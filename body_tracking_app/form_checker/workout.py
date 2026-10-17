"""Дасгалын явцыг удирдах: эхлэх заавар -> 3-2-1 тоолол -> дасгал -> амралт -> дүн.

Анализатор (squat/push-up) зөвхөн давталтыг тоолж үнэлдэг. Энэ модуль түүний дээр
хэрэглэгчийн туршлагын давхаргыг нэмнэ:
  * setup     : бие бүтэн харагдаж, эхлэх байрлалдаа (squat - босоо, push-up - гар тэнийсэн)
                ready_seconds хугацаанд тогтвортой байхыг хүлээнэ;
  * countdown : 3-2-1 тоолол, дараа нь "Эхэл!";
  * active    : давталтыг тоолж, сетийн зорилгод хүрэхийг хянана;
  * rest      : сетийн хоорондох амралтын таймер;
  * done      : бүх сет дууссан, дүнгийн дэлгэц.
Мөн кадр бүрт гарах дуут дохионы үйл явдлуудыг (events) буцаана.
2.0: сетийн дунд хүн удаан алга болбол түр зогсоож (setup руу буцаана), удаан хөдөлгөөнгүй байвал сануулна.
"""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass, field

from .config import WorkoutConfig
from .exercises.base import ExerciseAnalyzer, Feedback, RepResult
from .pose import Pose, framing_hint

SETUP, COUNTDOWN, ACTIVE, REST, DONE = "setup", "countdown", "active", "rest", "done"


@dataclass
class WorkoutView:
    """Дэлгэц зурахад хэрэгтэй бүх мэдээлэл."""
    phase: str
    fb: Feedback
    message: str
    level: str
    set_index: int                    # 1-ээс эхэлнэ
    sets_total: int
    target: int                       # 0 = чөлөөт горим
    set_reps: list[RepResult]
    total_reps: int
    total_correct: int
    countdown: int | None = None      # 3, 2, 1
    ready_progress: float = 0.0       # 0..1, эхлэх байрлалдаа хэр удаан тогтвортой байгаа
    rest_left: float | None = None    # амралтын үлдсэн секунд
    events: list[str] = field(default_factory=list)  # дуут дохио: tick, go, depth, good, bad, set_done, done
    # Бэлтгэлийн шалгах жагсаалт (зөвхөн setup шатанд): (хүн харагдаж байна, бүтэн бие кадрт багтсан,
    # эхлэх байрлалд байна). Хэрэглэгч тоолол яагаад эхлэхгүй байгааг харах боломжтой болно.
    setup_checks: tuple[bool, bool, bool] | None = None


class Workout:
    def __init__(self, analyzer: ExerciseAnalyzer, cfg: WorkoutConfig | None = None):
        self.analyzer = analyzer
        self.cfg = cfg or WorkoutConfig()
        self.phase = SETUP
        self.set_index = 1
        self.sets: list[list[RepResult]] = [[]]
        self.ready_since = None
        self.lost_since = None
        self.phase_start = 0.0
        self.rest_until = None
        self._last_count = None
        self._skip = False
        self._depth_rep = None  # «гүнд хүрлээ» дохио өгсөн давталтын эхэлсэн хугацаа
        self._away_since = None     # сетийн дунд хүн алга болсон хугацаа
        self._paused_away = False   # хүн алга болсны улмаас түр зогссон эсэх
        self._last_activity = 0.0   # сүүлд хөдөлгөөн (давталт) хийсэн хугацаа

    # ---- Гаднаас дуудах ------------------------------------------------------
    @property
    def name(self):
        return self.analyzer.name

    @property
    def free_mode(self):
        return self.cfg.target_reps <= 0

    @property
    def reps(self) -> list[RepResult]:
        return [r for s in self.sets for r in s]

    def skip(self):
        """Space товч: 3-2-1 тоолол эсвэл амралтыг алгасна."""
        self._skip = True

    def finish(self, t):
        """E товч: дасгалыг дуусгаж дүнгийн дэлгэц рүү шилжинэ."""
        self.phase = DONE
        self.phase_start = t

    def pause(self):
        """Өөр дасгал руу шилжих эсвэл хүн удаан алга болох үед: сетийн явцыг хадгалаад эхлэх шат руу буцна."""
        if self.phase in (COUNTDOWN, ACTIVE):
            self.phase = SETUP
            self.ready_since = None
            self._away_since = None

    # ---- Кадр бүрт ----------------------------------------------------------
    def update(self, pose: Pose | None, t: float) -> WorkoutView:
        fb = self.analyzer.update(pose, t)
        events: list[str] = []
        message, level = fb.message, fb.level
        countdown, ready_progress, rest_left, checks = None, 0.0, None, None
        skip, self._skip = self._skip, False

        if self.phase == SETUP:
            hint = None
            if pose is not None and fb.main_angle is not None:
                hint = framing_hint(pose, self.analyzer.common.min_visibility,
                                    min_size=self.cfg.min_body_size)
            framed = hint is None and fb.main_angle is not None
            ready = framed and self.analyzer.counter.state == "top"
            checks = (pose is not None, framed, ready)
            if ready:
                if self.ready_since is None:
                    self.ready_since = t
                ready_progress = (1.0 if self.cfg.ready_seconds <= 0
                                  else min(1.0, (t - self.ready_since) / self.cfg.ready_seconds))
                message, level = "hold_position", "ok"
                if ready_progress >= 1.0 or skip:
                    self._enter(COUNTDOWN, t)
                    skip = False  # нэг Space нэг л шатыг алгасна
            else:
                self.ready_since = None
                if hint is not None:
                    message, level = hint, "warn"
                elif fb.main_angle is not None:
                    message, level = self.analyzer.idle_message, "info"
                if skip and fb.main_angle is not None:
                    self._enter(COUNTDOWN, t)  # Space: хүлээлгүйгээр тоолол эхлүүлнэ
                    skip = False
            if self._paused_away:
                if pose is None:
                    message, level = "paused_away", "warn"
                else:
                    self._paused_away = False

        if self.phase == COUNTDOWN:
            # Хүн удаан алдагдвал дахин эхлэх шат руу
            if fb.main_angle is None:
                self.lost_since = self.lost_since if self.lost_since is not None else t
                if t - self.lost_since > self.cfg.lost_seconds:
                    self._enter(SETUP, t)
            else:
                self.lost_since = None
            if self.phase == COUNTDOWN:
                left = self.cfg.countdown_seconds - (t - self.phase_start)
                if left <= 0 or skip:
                    self._enter(ACTIVE, t)
                    events.append("go")
                else:
                    countdown = int(math.ceil(left))
                    if countdown != self._last_count:
                        events.append("tick")
                        self._last_count = countdown
                    message, level = "get_ready", "info"

        if self.phase == ACTIVE:
            counter = self.analyzer.counter
            if pose is None:
                self._away_since = self._away_since if self._away_since is not None else t
            else:
                self._away_since = None
            if counter.in_rep or fb.new_rep is not None:
                self._last_activity = t
            if counter.state == "bottom" and counter.started_at != self._depth_rep:
                # Зорилтот гүнд хүрлээ: дэлгэц рүү харж чадахгүй үед (push-up) дуугаар мэдэгдэнэ
                self._depth_rep = counter.started_at
                events.append("depth")
            if fb.new_rep is not None:
                self.sets[-1].append(fb.new_rep)
                events.append("good" if fb.new_rep.correct else "bad")
                if not self.free_mode and len(self.sets[-1]) >= self.cfg.target_reps:
                    if self.set_index >= self.cfg.sets:
                        self._enter(DONE, t)
                        events.append("done")
                    else:
                        self._enter(REST, t)
                        self.rest_until = t + self.cfg.rest_seconds
                        events.append("set_done")
            if self.phase == ACTIVE and t - self.phase_start < 1.0 and fb.level == "info":
                message, level = "ready", "ok"  # "Бэлэн. Эхэл!" эхний секундэд
            elif (self.phase == ACTIVE and fb.level == "info" and self.cfg.idle_seconds > 0
                  and t - self._last_activity > self.cfg.idle_seconds):
                message, level = "idle_hint", "info"
            if (self.phase == ACTIVE and self._away_since is not None and self.cfg.away_seconds > 0
                    and t - self._away_since > self.cfg.away_seconds):
                # Хүн удаан алга: сетийн явцыг хадгалаад эхлэх шат руу (буцаж ирэхэд 3-2-1 дахин)
                self.pause()
                self._paused_away = True
                message, level = "paused_away", "warn"

        if self.phase == REST:
            rest_left = max(0.0, self.rest_until - t)
            message, level = ("set_done", "ok") if t - self.phase_start < 2.0 else ("rest", "info")
            if rest_left <= 0 or skip:
                self.set_index += 1
                self.sets.append([])
                self._enter(SETUP, t)
                events.append("tick")

        if self.phase == DONE:
            message, level = "workout_done", "ok"

        cur = self.sets[-1]
        return WorkoutView(phase=self.phase, fb=fb, message=message, level=level,
                           set_index=self.set_index, sets_total=self.cfg.sets, target=self.cfg.target_reps,
                           set_reps=cur, total_reps=len(self.reps), total_correct=sum(r.correct for r in self.reps),
                           countdown=countdown, ready_progress=ready_progress, rest_left=rest_left, events=events,
                           setup_checks=checks if self.phase == SETUP else None)

    def _enter(self, phase, t):
        if phase == ACTIVE:
            # Тоолол эхлэхээс өмнө дууссан (бүртгэгдээгүй) давталтын "Зөв!" мессежийг харуулахгүй
            self.analyzer.result_until = -1.0
            self._last_activity = t
            self._away_since = None
        self.phase = phase
        self.phase_start = t
        self.ready_since = None
        self.lost_since = None
        self._last_count = None

    # ---- Дүн ----------------------------------------------------------------
    def summary(self):
        reps = self.reps
        issues = Counter(i for r in reps for i in r.issues)
        warnings = Counter(w for r in reps for w in r.warnings)
        n = len(reps)
        correct = sum(r.correct for r in reps)
        return {
            "exercise": self.name,
            "reps": n,
            "correct": correct,
            "accuracy": correct / n if n else 0.0,
            "sets": [(len(s), sum(r.correct for r in s)) for s in self.sets if s],
            "issues": issues.most_common(),
            "avg_duration": sum(r.duration for r in reps) / n if n else 0.0,
            "avg_min_angle": sum(r.min_angle for r in reps) / n if n else 0.0,
            "avg_score": sum(r.score for r in reps) / n if n else 0.0,
            "warnings": warnings.most_common(),
        }
