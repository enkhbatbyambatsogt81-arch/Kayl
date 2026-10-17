"""Аппын "хөдөлгүүр": кадрын эх үүсвэр -> MediaPipe -> дасгалын логик -> зурах -> дуу.

main.py (командын мөр) болон gui.py (цонхтой интерфейс) хоёулаа энэ классыг ашиглана.
Эх үүсвэр гурван төрөл:
  * камер ("0", "1", ...)  - бодит цагаар;
  * видео файл             - кадрын дугаараар цаг тооцно;
  * "demo"                 - камергүй үзүүлэн: синтетик хүн дасгал хийж буйг зурна.
"""

from __future__ import annotations

import queue
import sys
import time
from dataclasses import dataclass

import cv2
import numpy as np

from .audio import SoundPlayer
from .config import WorkoutConfig
from .exercises import create_analyzer
from .pose import Pose
from .recognition import ExerciseRecognizer
from .session import LOG_DIR, PerfMeter, save_csv
from .ui import Renderer
from .workout import ACTIVE, COUNTDOWN, REST, SETUP, Workout, WorkoutView

EXERCISES = ("squat", "pushup")


@dataclass
class EngineFrame:
    image: np.ndarray        # зурсан BGR кадр
    pose: Pose | None
    wv: WorkoutView
    exercise: str
    perf: dict               # {"fps": ..., "pose_ms": ...}
    t: float
    switched: str | None = None  # энэ кадрт дасгалыг автоматаар сольсон бол шинэ дасгалын нэр


class DemoSource:
    """Камергүй үзүүлэн: синтетик хүний squat / push-up (зөв ба алдаатай давталт холилдсон).

    Камер байхгүй үед эсвэл хичээл дээр аппын ажиллагааг үзүүлэхэд зориулсан.
    """

    # (хамгийн бага өнцөг, алдаа[, дээд өнцөг[, хугацаа с]])
    SCRIPTS = {
        "squat": [(85, []), (82, []), (120, ["squat_shallow"]), (85, []), (82, ["squat_lean"]), (85, [], 175, 1.0),
                  (84, ["squat_heels"]), (85, []), (85, ["squat_not_up"], 138), (84, [])],
        "pushup": [(80, []), (80, ["pushup_sag"]), (82, []), (115, ["pushup_shallow"]), (80, []),
                   (80, ["pushup_pike"]), (82, []), (80, [])],
    }

    LIFT = 0.12  # кадрын өндрийн хувь

    def __init__(self, exercise, width=1280, height=720, fps=30, seed=0):
        from tools.synthetic import RepSpec, make_sequence  # зөвхөн демод хэрэгтэй

        reps = []
        for _ in range(4):
            for item in self.SCRIPTS[exercise]:
                top = item[2] if len(item) > 2 else 175.0
                duration = item[3] if len(item) > 3 else 2.2   # 1.0 с = хэт хурдан (2.0-ийн сануулга)
                reps.append(RepSpec(item[0], list(item[1]), duration=duration, pause=0.9, top_angle=top))
        self.frames, _ = make_sequence(exercise, reps, view="side", noise_px=1.5, outlier_rate=0.0,
                                       dropout_rate=0.0, seed=seed, start_pause=5.0)
        # Синтетик газар кадрын 92%-д байдаг; доод мессежийн мөрөнд дарагдахгүйн тулд дээш зөөнө.
        for _, pose in self.frames:
            pose.img[:, 1] -= self.LIFT * pose.height
        self.width, self.height, self.fps = width, height, fps
        self.i = 0
        self.background = self._background(width, height)

    @staticmethod
    def _background(w, h):
        y = np.linspace(0, 1, h, dtype=np.float32)[:, None, None]
        top, bottom = np.array([70, 62, 52], np.float32), np.array([40, 36, 32], np.float32)
        bg = (top * (1 - y) + bottom * y).repeat(w, axis=1).astype(np.uint8)
        floor = int(h * (0.92 - DemoSource.LIFT))
        cv2.line(bg, (0, floor), (w, floor), (110, 110, 110), 2)
        return bg

    def read(self):
        t, pose = self.frames[self.i % len(self.frames)]
        self.i += 1
        return True, self.background.copy(), pose


class WorkoutEngine:
    def __init__(self, exercise="squat", source="0", model="lite", workout_cfg: WorkoutConfig | None = None,
                 lang="mn", mirror=None, sound=True, width=1280, height=720, hud=True, show_help=True,
                 realtime=False, estimator=None, log_dir=None, level="normal", auto_detect=False):
        self.exercise = exercise
        self.level = level              # шалгуурын түвшин: easy / normal / strict
        self.auto_detect = auto_detect  # дасгалыг биеийн байрлалаар автоматаар таних (2.0)
        self.recognizer = ExerciseRecognizer()
        self._dismissed = None  # хэрэглэгч гараар өөр дасгал сонгосон үеийн танигдсан байрлал
        self._notice, self._notice_until = None, -1.0
        self.source = str(source)
        self.model = model
        self.lang = lang
        self.width, self.height = width, height
        self.hud, self.show_help = hud, show_help
        self.realtime = realtime
        self.log_dir = log_dir or LOG_DIR
        self.kind = "demo" if self.source == "demo" else ("camera" if self.source.isdigit() else "video")
        self.mirror = (self.kind == "camera") if mirror is None else mirror
        self.cfg = workout_cfg or self.default_config(self.kind)
        self.renderer = Renderer(lang)
        self.sound = SoundPlayer(enabled=sound)
        self.perf = PerfMeter()
        self.workouts = {name: self._new_workout(name) for name in EXERCISES}
        self.estimator = estimator
        self._own_estimator = estimator is None
        self.cap = None
        self.demo = None
        self.fps = 30.0
        self.frame_idx = 0
        self.t_start = None
        self.paused = False
        self._paused_at = None
        self._paused_total = 0.0
        self._last_wall = None
        self._commands = queue.SimpleQueue()

    # ---- Тохиргоо -------------------------------------------------------------
    @staticmethod
    def default_config(kind, reps=None, sets=3, rest=60.0):
        if kind == "video":
            # Бичлэг дээр бүх давталтыг тоолохын тулд 3-2-1 тоололгүй, анхдагчаар чөлөөт горимоор
            return WorkoutConfig(target_reps=reps or 0, sets=sets, rest_seconds=rest,
                                 ready_seconds=0, countdown_seconds=0)
        return WorkoutConfig(target_reps=10 if reps is None else reps, sets=sets, rest_seconds=rest)

    def _new_workout(self, name):
        return Workout(create_analyzer(name, self.level), self.cfg)

    @property
    def workout(self) -> Workout:
        return self.workouts[self.exercise]

    # ---- Нээх / хаах ------------------------------------------------------------
    def open(self):
        """Эх үүсвэр ба загварыг нээнэ. Амжилттай бол None, үгүй бол алдааны мессеж буцаана."""
        if self.kind == "demo":
            self.demo = DemoSource(self.exercise, self.width, self.height)
        else:
            if self.kind == "camera":
                index = int(self.source)
                win = sys.platform.startswith("win")
                # Windows дээр DirectShow камерыг хурдан нээдэг
                self.cap = cv2.VideoCapture(index, cv2.CAP_DSHOW) if win else cv2.VideoCapture(index)
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
            else:
                self.cap = cv2.VideoCapture(self.source)
            if not self.cap.isOpened():
                return (f"Камер {self.source}-ийг нээж чадсангүй. Өөр програм (Zoom, Teams) камер ашиглаж байгаа "
                        "эсэхийг шалгана уу." if self.kind == "camera"
                        else f"Видео файлыг нээж чадсангүй: {self.source}")
            self.fps = self.cap.get(cv2.CAP_PROP_FPS) or 30.0
            if self.estimator is None:
                from .pose import PoseEstimator
                self.estimator = PoseEstimator(self.model)
        self.t_start = time.perf_counter()
        return None

    def close(self):
        """Эх үүсвэрийг хаагаад, давталт байвал CSV лог хадгалж замыг нь буцаана."""
        if self.cap is not None:
            self.cap.release()
            self.cap = None
        if self.estimator is not None and self._own_estimator:
            self.estimator.close()
            self.estimator = None
        return save_csv(self.workouts.values(), self.log_dir)

    # ---- Удирдлага (өөр урсгалаас дуудаж болно) ---------------------------------
    def skip(self):
        self._commands.put(("skip",))

    def finish(self):
        self._commands.put(("finish",))

    def reset(self):
        self._commands.put(("reset",))

    def set_exercise(self, name):
        self._commands.put(("exercise", name))

    def toggle_mirror(self):
        self._commands.put(("mirror",))

    def toggle_sound(self):
        return self.sound.toggle()

    def set_paused(self, paused):
        if paused and not self.paused:
            self._paused_at = time.perf_counter()
        elif not paused and self.paused and self._paused_at is not None:
            self._paused_total += time.perf_counter() - self._paused_at
        self.paused = paused

    def _apply_commands(self, t):
        while True:
            try:
                cmd = self._commands.get_nowait()
            except queue.Empty:
                return
            if cmd[0] == "skip":
                self.workout.skip()
            elif cmd[0] == "finish":
                self.workout.finish(t)
            elif cmd[0] == "reset":
                self.workouts[self.exercise] = self._new_workout(self.exercise)
            elif cmd[0] == "exercise" and cmd[1] in EXERCISES and cmd[1] != self.exercise:
                self._switch(cmd[1])
                # Гараар сонгосныг хүндэтгэнэ: одоогийн байрлалаар буцааж автоматаар солихгүй
                guess = self.recognizer.current
                self._dismissed = guess if guess != cmd[1] else None
            elif cmd[0] == "mirror":
                self.mirror = not self.mirror

    def _switch(self, name):
        self.workout.pause()
        self.exercise = name
        if self.kind == "demo":
            self.demo = DemoSource(self.exercise, self.width, self.height)

    def _can_auto_switch(self):
        """Сетийн дундуур (давталт хийж байхад) дасгалыг солихгүй: зөвхөн бэлтгэл, амралтын үед
        эсвэл энэ сетэд нэг ч давталт тоологдоогүй үед."""
        w = self.workout
        if w.phase in (SETUP, REST):
            return True
        return w.phase in (COUNTDOWN, ACTIVE) and not w.sets[-1] and not w.analyzer.counter.in_rep

    def _auto_detect(self, pose, t):
        guess = self.recognizer.update(pose, t)
        if guess is None:
            return None
        if guess == self.exercise:
            self._dismissed = None
            return None
        if guess != self._dismissed and self._can_auto_switch():
            self._switch(guess)
            self._notice, self._notice_until = f"switched_{guess}", t + 2.5
            return guess
        return None

    # ---- Нэг кадр -------------------------------------------------------------
    def _now(self, wall):
        if self.kind == "camera":
            return wall - self.t_start - self._paused_total
        return self.frame_idx / self.fps

    def step(self) -> EngineFrame | None:
        """Нэг кадр уншиж боловсруулна. Видео дууссан бол None."""
        if self.realtime and self.kind != "camera" and self._last_wall is not None:
            # Бичлэг/демог бодит хурдаар тоглуулна
            wait = 1.0 / self.fps - (time.perf_counter() - self._last_wall)
            if wait > 0:
                time.sleep(wait)
        self._last_wall = time.perf_counter()

        if self.kind == "demo":
            ok, frame, pose_given = self.demo.read()
        else:
            ok, frame = self.cap.read()
            pose_given = None
        if not ok:
            return None
        t0 = time.perf_counter()
        if self.mirror and self.kind == "camera":
            frame = cv2.flip(frame, 1)
        t = self._now(t0)
        self.frame_idx += 1
        self._apply_commands(t)

        if self.kind == "demo":
            pose, pose_ms = pose_given, 0.0
        else:
            pose = self.estimator.process(frame, int(t * 1000))
            pose_ms = self.estimator.last_latency_ms
        switched = self._auto_detect(pose, t) if self.auto_detect else None
        workout = self.workout
        wv = workout.update(pose, t)
        if self._notice is not None and t <= self._notice_until and wv.level != "warn":
            wv.message, wv.level = self._notice, "ok"
        self.sound.play_events(wv.events)

        summary = workout.summary() if (self.hud and wv.phase == "done") else None
        frame = self.renderer.render(
            frame, pose, wv, workout.analyzer.counter, self.perf.current(), show_help=self.show_help,
            sound_on=self.sound.enabled if self.sound.available else None,
            summary=summary, sets=[s for s in workout.sets if s], hud=self.hud)
        self.perf.tick(pose_ms, (time.perf_counter() - t0) * 1000)
        return EngineFrame(image=frame, pose=pose, wv=wv, exercise=self.exercise, perf=self.perf.current(), t=t,
                           switched=switched)
