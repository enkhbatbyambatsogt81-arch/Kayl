"""Утасны (Android) хувилбарын хөдөлгүүр (3.2).

Утсан дээр камер, биеийн цэг илрүүлэлт (MediaPipe Tasks, JavaScript) ба зураглалыг WebView хариуцна. Харин давталт
тоолох, техник шалгах, сет / амралтын явц нь компьютерын хувилбартай ЯГ ИЖИЛ Python код (exercises/, workout.py,
recognition.py) бөгөөд утсан дээр Pyodide (WebAssembly дээрх Python)-оор ажиллана. Энэ модуль тэр хоёрын гүүр:
кадр бүрт 33 цэгийг аваад дэлгэцэнд хэрэгтэй бүхнийг JSON болгож болох dict-ээр буцаана.

OpenCV, MediaPipe (Python) шаардахгүй: зөвхөн numpy. Компьютер дээр ч ажиллана (tests/test_mobile.py).
"""

from __future__ import annotations

import json
import math

import numpy as np

from . import __version__
from .config import LEVELS, WorkoutConfig
from .demo import DEMO_FLOOR, DEMO_LIFT, demo_frames
from .exercises import create_analyzer
from .messages import EXERCISE_NAMES, MESSAGES, TIPS, WARNING_TITLES
from .messages import t as text
from .pose import SIDES, SKELETON, Pose
from .recognition import ExerciseRecognizer
from .workout import ACTIVE, COUNTDOWN, REST, SETUP, Workout

EXERCISES = ("squat", "pushup")
DEMO_FPS = 30.0
MAIN_JOINT = {"squat": "knee", "pushup": "elbow"}   # гол өнцгийг аль үен дээр бичих вэ


def _num(value, digits=1):
    """JSON-д NaN бичиж болохгүй (JavaScript JSON.parse унадаг) тул None болгоно."""
    if value is None:
        return None
    value = float(value)
    return None if math.isnan(value) or math.isinf(value) else round(value, digits)


def _focus(frames):
    """Демо хүний бүх кадрын туршид эзлэх талбай (жижиг дэлгэцэнд түүнийг томруулж харуулахад): [x0, y0, x1, y1]."""
    pts = np.concatenate([pose.img[pose.vis > 0.5, :2] for _, pose in frames])
    (x0, y0), (x1, y1) = pts.min(axis=0), pts.max(axis=0)
    mx, my = 0.12 * (x1 - x0) + 16, 0.08 * (y1 - y0) + 12
    return [round(float(v), 1) for v in (x0 - mx, y0 - my, x1 + mx, y1 + my)]


class MobileSession:
    """Нэг дасгалын сешн. Кадр бүрт frame() (камер) эсвэл demo_frame() (демо) дуудна."""

    def __init__(self, exercise="squat", level="normal", reps=10, sets=3, rest=60.0, free_mode=False,
                 auto_detect=False, demo=False, lang="mn"):
        self.exercise = exercise if exercise in EXERCISES else "squat"
        self.level = level if level in LEVELS else "normal"
        self.lang = lang
        self.auto_detect = bool(auto_detect)
        self.demo = bool(demo)
        self.cfg = WorkoutConfig(target_reps=0 if free_mode else max(0, int(reps)), sets=max(1, int(sets)),
                                 rest_seconds=float(rest))
        self.workouts = {name: Workout(create_analyzer(name, self.level), self.cfg) for name in EXERCISES}
        self.recognizer = ExerciseRecognizer()
        self._dismissed = None  # хэрэглэгч гараар өөр дасгал сонгосон үеийн танигдсан байрлал
        self._notice, self._notice_until = None, -1.0
        self._t = 0.0
        self._demo, self._demo_t0, self._demo_focus = None, 0.0, None
        if self.demo:
            self._set_demo(self.exercise, 0.0)

    def _set_demo(self, name, t):
        self._demo, self._demo_t0 = demo_frames(name), t
        self._demo_focus = _focus(self._demo)

    @property
    def workout(self) -> Workout:
        return self.workouts[self.exercise]

    # ---- Удирдлага -----------------------------------------------------------
    def skip(self):
        """3-2-1 тоолол эсвэл амралтыг алгасна."""
        self.workout.skip()

    def finish(self):
        """Дасгалыг дуусгаж дүн рүү шилжинэ."""
        self.workout.finish(self._t)

    def set_exercise(self, name):
        if name not in EXERCISES or name == self.exercise:
            return
        self._switch(name)
        # Гараар сонгосныг хүндэтгэнэ: одоогийн байрлалаар буцааж автоматаар солихгүй
        guess = self.recognizer.current
        self._dismissed = guess if guess != name else None

    def _switch(self, name):
        self.workout.pause()
        self.exercise = name
        if self.demo:
            self._set_demo(name, self._t)

    def _can_auto_switch(self):
        """Сетийн дундуур дасгалыг солихгүй: зөвхөн бэлтгэл, амралтын үед эсвэл энэ сетэд давталт тоологдоогүй үед."""
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

    # ---- Кадр ----------------------------------------------------------------
    def frame(self, points, width, height, t):
        """points: 33 × (x, y, z, visibility) дараалсан 132 тоо (x, y, z пикселээр) эсвэл хүн олдоогүй бол None.

        t: дасгал эхэлснээс хойших секунд (түр зогссон хугацааг хассан)."""
        pose = None
        if points is not None:
            if hasattr(points, "to_py"):   # Pyodide: JavaScript-ийн Float64Array
                points = points.to_py()
            arr = np.array(points, dtype=float).reshape(33, 4)
            pose = Pose(img=arr[:, :3].copy(), world=None, vis=arr[:, 3].copy(), width=int(width), height=int(height))
        return self._step(pose, float(t))

    def demo_frame(self, t):
        """Демо: синтетик хүний t агшин дахь байрлал. Буцаах dict-д зурах цэгүүд ("pose") орно."""
        t = float(t)
        i = int(max(0.0, t - self._demo_t0) * DEMO_FPS + 1e-6) % len(self._demo)   # 1e-6: 0.1 * 30 = 2.9999...
        pose = self._demo[i][1]
        view = self._step(pose, t)
        view["pose"] = {
            "points": [[round(float(x), 1), round(float(y), 1), round(float(v), 2)]
                       for (x, y), v in zip(pose.img[:, :2], pose.vis)],
            "width": pose.width, "height": pose.height, "floor": round(pose.height * (DEMO_FLOOR - DEMO_LIFT), 1),
            "focus": self._demo_focus,
        }
        return view

    def _step(self, pose, t):
        self._t = t
        switched = self._auto_detect(pose, t) if self.auto_detect else None
        workout = self.workout
        wv = workout.update(pose, t)
        if self._notice is not None and t <= self._notice_until and wv.level != "warn":
            wv.message, wv.level = self._notice, "ok"
        fb, counter = wv.fb, workout.analyzer.counter
        last = fb.last_rep
        joint = SIDES[fb.side][MAIN_JOINT[self.exercise]] if fb.side else None
        return {
            "exercise": self.exercise,
            "phase": wv.phase,
            "message": text(wv.message, self.lang),
            "message_key": wv.message,
            "level": wv.level,
            "set_index": wv.set_index,
            "sets_total": wv.sets_total,
            "target": wv.target,
            "set_reps": [{"correct": bool(r.correct), "score": int(r.score)} for r in wv.set_reps],
            "total_reps": wv.total_reps,
            "total_correct": wv.total_correct,
            "countdown": wv.countdown,
            "ready_progress": _num(wv.ready_progress, 3),
            "rest_left": _num(wv.rest_left),
            "events": list(wv.events),
            "checks": [bool(c) for c in wv.setup_checks] if wv.setup_checks is not None else None,
            "state": fb.state,
            "angle": _num(fb.main_angle),
            "angle_joint": joint,
            "depth_angle": _num(fb.metrics.get("depth_angle")),
            "depth_target": _num(counter.depth),
            "top_angle": _num(counter.top),
            "side": fb.side,
            "view": fb.view,
            "bad_joints": sorted(int(j) for j in fb.bad_joints),
            "last_rep": None if last is None else {
                "index": last.index, "correct": bool(last.correct), "score": int(last.score),
                "issues": [text(k, self.lang) for k in last.issues],
            },
            "new_rep": fb.new_rep is not None,
            "switched": switched,
            "t": round(t, 3),
        }

    # ---- Дүн -----------------------------------------------------------------
    def summary(self):
        """Давталт хийсэн дасгал бүрийн дүн (дүнгийн хуудас ба түүхэнд хадгалахад)."""
        out = []
        for name, w in self.workouts.items():
            s = w.summary()
            if not s["reps"]:
                continue
            reps = w.reps
            out.append({
                "exercise": name,
                "name": text(name, self.lang, EXERCISE_NAMES),
                "level": self.level,
                "reps": s["reps"],
                "correct": s["correct"],
                "accuracy": round(s["accuracy"], 4),
                "avg_score": round(s["avg_score"], 1),
                "avg_duration": round(s["avg_duration"], 2),
                "avg_min_angle": round(s["avg_min_angle"], 1),
                "sets": [[n, c] for n, c in s["sets"]],
                "issues": [{"key": k, "title": text(k, self.lang), "count": n, "tip": TIPS.get(k, "")}
                           for k, n in s["issues"]],
                "warnings": [{"key": k, "title": WARNING_TITLES.get(k, text(k, self.lang)), "count": n,
                              "tip": TIPS.get(k, "")} for k, n in s["warnings"]],
                "rep_scores": [int(r.score) for r in reps],
                "rep_correct": [bool(r.correct) for r in reps],
            })
        return out


# ---- JavaScript-ээс дуудах функцууд (нэг идэвхтэй сешн, бүх оролт / гаралт JSON мөр) --------------------------------
_session: MobileSession | None = None


def info():
    """Апп ачаалагдсаны дараа нэг удаа: хувилбар, араг ясны холбоос, мессежийн хүснэгт."""
    return json.dumps({"version": __version__, "skeleton": SKELETON, "exercises": list(EXERCISES),
                       "levels": list(LEVELS), "messages": {k: v[0] for k, v in MESSAGES.items()}},
                      ensure_ascii=False)


def start(options_json="{}"):
    global _session
    _session = MobileSession(**json.loads(options_json))
    return json.dumps({"exercise": _session.exercise, "level": _session.level, "demo": _session.demo})


def frame(points, width, height, t):
    return json.dumps(_session.frame(points, width, height, t), ensure_ascii=False)


def demo_frame(t):
    return json.dumps(_session.demo_frame(t), ensure_ascii=False)


def command(name, arg=None):
    if _session is None:
        return
    if name == "skip":
        _session.skip()
    elif name == "finish":
        _session.finish()
    elif name == "exercise":
        _session.set_exercise(arg)


def summary():
    return json.dumps(_session.summary() if _session is not None else [], ensure_ascii=False)
