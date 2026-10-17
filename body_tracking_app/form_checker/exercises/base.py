"""Дасгалын шинжилгээний ерөнхий логик: давталт тоолох төлөвийн машин,
алдааг тогтворжуулах, мессеж сонгох."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field, replace

import numpy as np

from ..config import CommonConfig
from ..geometry import AngleFilter
from ..pose import L_HIP, L_SHOULDER, R_HIP, R_SHOULDER, SIDES, Pose, framing_hint


@dataclass
class RepResult:
    index: int
    correct: bool
    issues: list[str]
    min_angle: float
    start_time: float
    end_time: float
    # 2.0: 0-100 оноо (зөв/буруугаас гадна хэр сайн хийснийг харуулна) ба сануулга. Сануулга
    # (хэт хурдан, хөлийн байрлал) нь давталтыг "буруу" болгодоггүй, зөвхөн оноог бууруулна.
    score: int = 100
    warnings: list[str] = field(default_factory=list)

    @property
    def duration(self):
        return self.end_time - self.start_time


@dataclass
class Feedback:
    exercise: str
    state: str                       # idle / top / down / bottom / up
    reps: int = 0
    correct_reps: int = 0
    main_angle: float | None = None  # өвдөг (squat) эсвэл тохой (push-up)
    metrics: dict = field(default_factory=dict)
    live_issues: list[str] = field(default_factory=list)
    message: str = "no_person"       # messages.py дахь түлхүүр
    level: str = "info"              # info / ok / warn
    side: str | None = None
    view: str | None = None
    bad_joints: set = field(default_factory=set)  # улаанаар зурах цэгүүд
    last_rep: RepResult | None = None
    new_rep: RepResult | None = None  # энэ кадрт дуусгавар болсон давталт


class RepCounter:
    """Нэг өнцгийн дохиогоор (өвдөг/тохой) давталт тоолох төлөвийн машин.

    idle -> top -> down -> bottom -> up -> top (давталт дуусна)
    Өнцөг буурах = доошлох, өсөх = өндийх.
    """

    def __init__(self, top, start, depth, attempt, rebound_rise, rebound_drop):
        self.top, self.start, self.depth, self.attempt = top, start, depth, attempt
        self.rebound_rise, self.rebound_drop = rebound_rise, rebound_drop
        self.reset()

    def reset(self):
        self.state = "idle"
        self.rep_min = None
        self.rise_max = None
        self.started_at = None
        self.depth_min = None   # гүнийг үнэлэх (бага тэгшитгэсэн) дохионы хамгийн бага утга

    @property
    def in_rep(self):
        return self.state in ("down", "bottom", "up")

    def _begin(self, a, t, d=None):
        self.state = "down"
        self.rep_min = a
        self.rise_max = a
        self.started_at = t
        self.depth_min = d

    def update(self, a, t, depth_value=None):
        """Шинэ өнцөг өгнө. Давталт дууссан бол dict буцаана, үгүй бол None.

        a: төлөв тодорхойлох (сайн тэгшитгэсэн) өнцөг. depth_value: гүнийг үнэлэх өнцөг (2.0). Их тэгшитгэл
        доод цэгийг "тайрдаг" тул давталтын хамгийн бага өнцгийг бага тэгшитгэсэн дохиогоор хэмжинэ."""
        d = depth_value
        if d is not None and self.in_rep:
            self.depth_min = d if self.depth_min is None else min(self.depth_min, d)
        if self.state == "idle":
            if a >= self.top:
                self.state = "top"
            return None

        if self.state == "top":
            if a < self.start:
                self._begin(a, t, d)
            return None

        # Давталтын дотор
        if a < self.rep_min:
            self.rep_min = a
            self.rise_max = a
        else:
            self.rise_max = max(self.rise_max, a)

        if a >= self.top:
            done = self._finish(t, full_extension=True)
            self.state = "top"
            return done

        # Бүрэн өндийлгүй дахин буусан ("bounce")
        if (self.rise_max - self.rep_min >= self.rebound_rise
                and self.rise_max - a >= self.rebound_drop):
            done = self._finish(t, full_extension=False)
            self._begin(a, t, d)
            return done

        if a <= self.depth or (d is not None and d <= self.depth):
            self.state = "bottom"   # гүний дохио (beep) ба depth_ok нэг дохиогоор шийдэгдэнэ
        elif a > self.rep_min + 8:
            self.state = "up"
        else:
            self.state = "down"
        return None

    def _finish(self, t, full_extension):
        low = self.rep_min if self.depth_min is None else min(self.rep_min, self.depth_min)
        if low is None or low > self.attempt:
            return None  # жижиг нугалалт, давталт биш
        return dict(min_angle=low, depth_ok=low <= self.depth,
                    full_extension=full_extension, start=self.started_at, end=t)


class ExerciseAnalyzer:
    """Дасгал бүрийн анализаторын суурь класс."""

    name = "base"
    key_joints = ("shoulder", "hip", "knee", "ankle")
    shallow_issue = "shallow"
    not_up_issue = "not_up"
    fast_warning = "fast"
    warning_keys: frozenset = frozenset()   # measure()-ийн буцаадаг алдаанаас аль нь зөвхөн сануулга вэ
    idle_message = "ready"
    level = "normal"         # шалгуурын түвшин (create_analyzer тохируулна)

    # Онооны торгууль (2.0). LearnOpenCV-ийн AI Fitness Trainer шиг алдааг ноцтой (давталтыг буруу
    # болгоно) ба зөөлөн (зөвхөн сануулна) гэж ангилж, хоёуланг нь нэг 0-100 оноонд нэгтгэв.
    SCORE_ISSUE = 20         # хэлбэрийн алдаа бүр
    SCORE_NOT_UP = 15        # бүрэн босоогүй / гараа тэнийлгээгүй
    SCORE_WARNING = 10       # сануулга бүр (хэт хурдан г.м.)
    SCORE_SHALLOW_MIN, SCORE_SHALLOW_MAX = 15, 45   # гүехэн: 15 + (дутуу градус), дээд тал нь 45

    def __init__(self, cfg, common: CommonConfig | None = None):
        self.cfg = cfg
        self.common = common or CommonConfig()
        self.counter = RepCounter(cfg.top_angle, cfg.start_angle, cfg.depth_angle,
                                  cfg.attempt_angle, cfg.rebound_rise, cfg.rebound_drop)
        self.angle_ema = self._make_filter()
        # Гүнийг үнэлэх өнцөг: 1.x-ийн медиан + EMA(0.5) (доод цэгийг тайрдаггүй, хазайлт ~0°)
        self.depth_filter = AngleFilter(self.common.smoothing_alpha, self.common.median_window)
        self.filters: dict[str, AngleFilter] = {}
        self.ratio_ema = AngleFilter(0.3, self.common.median_window)
        self.reps: list[RepResult] = []
        self.issue_streak = defaultdict(int)
        self.rep_issues: set[str] = set()
        self.rep_warnings: set[str] = set()
        self.side = None
        self.view = "side"
        self.last_seen = None
        self.result_until = -1.0
        self.gate_streak = 0
        self.last_fb: Feedback | None = None
        self._prev_view = None
        self._t = None  # одоогийн кадрын хугацаа (1€ шүүлтүүрт хэрэгтэй)

    # ---- Дэд класс хэрэгжүүлнэ ---------------------------------------------
    def measure(self, pose: Pose, side: dict, view: str, in_rep: bool):
        """Буцаах: (гол өнцөг, metrics dict, идэвхтэй алдаанууд {key: [joint idx]},
        gate_message эсвэл None)."""
        raise NotImplementedError

    def on_view_change(self, view):
        """Харагдац солигдох үед дэд класс босгоо өөрчилж болно."""

    # ---- Туслах ------------------------------------------------------------
    def _make_filter(self, degrees=True):
        """1€ шүүлтүүрийн beta нь дохионы нэгжээс (°/с) хамаардаг тул зөвхөн градусаар хэмжсэн
        дохионд хэрэглэнэ. Харьцаа, пикселийн хэмжээ зэрэгт өмнөх шиг медиан + EMA."""
        c = self.common
        if not degrees:
            return AngleFilter(c.smoothing_alpha, c.median_window)
        return AngleFilter(c.smoothing_alpha, c.median_window, kind=c.filter_kind,
                           min_cutoff=c.one_euro_min_cutoff, beta=c.one_euro_beta, d_cutoff=c.one_euro_d_cutoff)

    def smooth(self, name, value, degrees=False):
        """Хэмжилтийг (өнцөг, харьцаа) шуугианаас цэвэрлэнэ. degrees=True: градусаар хэмжсэн өнцөг."""
        if name not in self.filters:
            self.filters[name] = self._make_filter(degrees)
        return self.filters[name].update(value, self._t)

    def _reset_filters(self):
        self.angle_ema.reset()
        self.depth_filter.reset()
        for f in self.filters.values():
            f.reset()

    @property
    def correct_reps(self):
        return sum(r.correct for r in self.reps)

    def _choose_side(self, pose: Pose):
        scores = {}
        for name, idx in SIDES.items():
            # Хамгийн муу харагдаж буй үеэр үнэлнэ: нэг ч гол үе далд байвал тухайн тал тохирохгүй
            scores[name] = float(min(pose.vis[idx[j]] for j in self.key_joints))
        best = max(scores, key=scores.get)
        # Hysteresis: тал байнга солигдохоос сэргийлнэ
        if self.side is None or scores[best] > scores[self.side] + 0.1:
            self.side = best
        return self.side, scores[self.side]

    def _detect_view(self, pose: Pose):
        p = pose.img
        shoulder_w = abs(p[L_SHOULDER, 0] - p[R_SHOULDER, 0])
        mid_sh = (p[L_SHOULDER, :2] + p[R_SHOULDER, :2]) / 2
        mid_hip = (p[L_HIP, :2] + p[R_HIP, :2]) / 2
        torso = np.linalg.norm(mid_sh - mid_hip) + 1e-6
        ratio = self.ratio_ema.update(shoulder_w / torso)
        thr = self.common.front_view_ratio
        if self.view == "side" and ratio > thr + 0.05:
            self.view = "front"
        elif self.view == "front" and ratio < thr - 0.05:
            self.view = "side"
        return self.view, ratio

    def _lost(self, t, message):
        # Богино хугацааны (нэг хоёр кадрын) алдагдлыг үл тоож, өмнөх дүнг харуулна
        if (self.last_fb is not None and self.last_seen is not None
                and t - self.last_seen < self.common.glitch_seconds):
            return replace(self.last_fb, new_rep=None)
        fb = Feedback(exercise=self.name, state=self.counter.state, reps=len(self.reps),
                      correct_reps=self.correct_reps, message=message, level="warn",
                      last_rep=self.reps[-1] if self.reps else None)
        if self.last_seen is not None and t - self.last_seen > self.common.lost_reset_seconds:
            if self.counter.in_rep:
                self.counter.reset()
                self.rep_issues.clear()
            self._reset_filters()
            fb.state = self.counter.state
        return fb

    def score_rep(self, min_angle, depth_ok, issues, warnings):
        """Давталтын 0-100 оноо: 100-аас алдаа, сануулга бүрийн торгуулийг хасна."""
        score = 100.0
        if not depth_ok:
            missing = max(0.0, min_angle - self.counter.depth)
            score -= min(self.SCORE_SHALLOW_MAX, self.SCORE_SHALLOW_MIN + missing)
        for key in issues:
            if key == self.not_up_issue:
                score -= self.SCORE_NOT_UP
            elif key != self.shallow_issue:
                score -= self.SCORE_ISSUE
        score -= self.SCORE_WARNING * len(warnings)
        return int(round(max(0.0, score)))

    # ---- Гол функц -----------------------------------------------------------
    def update(self, pose: Pose | None, t: float) -> Feedback:
        fb = self._update(pose, t)
        if fb.main_angle is not None:
            self.last_fb = fb
        return fb

    def _update(self, pose: Pose | None, t: float) -> Feedback:
        self._t = t
        if pose is None:
            return self._lost(t, "no_person")

        side_name, side_vis = self._choose_side(pose)
        if side_vis < self.common.min_visibility:
            # Биеийн аль хэсэг кадраас гарсныг тодорхой хэлнэ (жишээ нь "хөл харагдахгүй")
            return self._lost(t, framing_hint(pose, self.common.min_visibility) or "not_visible")

        view, ratio = self._detect_view(pose)
        if view != self._prev_view:
            # Харагдац солигдвол өнцгийн тооцоолол өөрчлөгдөх тул эхэлсэн давталтыг цуцална
            if self._prev_view is not None and self.counter.in_rep:
                self.counter.reset()
                self.rep_issues.clear()
            self._reset_filters()
            self._prev_view = view
            self.on_view_change(view)
        side = SIDES[side_name]
        raw_angle, metrics, issues, gate = self.measure(pose, side, view, self.counter.in_rep)
        metrics["view_ratio"] = ratio

        if gate is not None or raw_angle is None or np.isnan(raw_angle):
            # Зөв байрлалд ороогүй. Хэдхэн кадр бол шуугиан гэж үзээд алгасна,
            # удаан үргэлжилбэл тоолуурыг зогсооно.
            self.gate_streak += 1
            if self.gate_streak < self.common.gate_min_frames and self.last_fb is not None:
                return replace(self.last_fb, new_rep=None)
            if self.counter.in_rep or self.counter.state == "top":
                self.counter.reset()
                self.rep_issues.clear()
            self._reset_filters()
            self.last_fb = None
            return Feedback(exercise=self.name, state=self.counter.state, side=side_name, view=view,
                            metrics=metrics, reps=len(self.reps), correct_reps=self.correct_reps,
                            message=gate or "not_visible", level="warn",
                            last_rep=self.reps[-1] if self.reps else None)
        self.gate_streak = 0
        self.last_seen = t

        fb = Feedback(exercise=self.name, state=self.counter.state, side=side_name, view=view,
                      metrics=metrics)
        angle = self.angle_ema.update(raw_angle, t)
        depth_angle = self.depth_filter.update(raw_angle)
        metrics["depth_angle"] = depth_angle  # гүний самбар энэ утгаар (давталтын үнэлгээтэй ижил дохио)
        fb.main_angle = angle

        # Алдааг хэдэн кадр дараалан харагдсаны дараа л тооцно (шуугианаас хамгаална)
        live = []
        for key in list(self.issue_streak):
            if key not in issues:
                self.issue_streak[key] = 0
        for key, joints in issues.items():
            self.issue_streak[key] += 1
            if self.issue_streak[key] >= self.common.issue_min_frames:
                live.append(key)
                fb.bad_joints.update(joints)
                if self.counter.in_rep:
                    (self.rep_warnings if key in self.warning_keys else self.rep_issues).add(key)

        was_in_rep = self.counter.in_rep
        done = self.counter.update(angle, t, depth_angle)
        fb.state = self.counter.state
        if done is not None:
            rep_issues = sorted(self.rep_issues)
            if not done["depth_ok"]:
                rep_issues.insert(0, self.shallow_issue)
            if not done["full_extension"]:
                rep_issues.append(self.not_up_issue)
            warnings = sorted(self.rep_warnings)
            if t - done["start"] < getattr(self.cfg, "min_rep_seconds", 0.0):
                warnings.append(self.fast_warning)
            rep = RepResult(index=len(self.reps) + 1, correct=not rep_issues, issues=rep_issues,
                            min_angle=done["min_angle"], start_time=done["start"], end_time=t,
                            score=self.score_rep(done["min_angle"], done["depth_ok"], rep_issues, warnings),
                            warnings=warnings)
            self.reps.append(rep)
            fb.new_rep = rep
            self.result_until = t + self.common.result_message_seconds
        if done is not None or not self.counter.in_rep:
            self.rep_issues.clear()
            self.rep_warnings.clear()
        if not was_in_rep and self.counter.in_rep:
            # Давталт эхлэх агшны сануулгууд (жишээ нь хөлийн байрлал) энэ давталтад хамаарна
            self.rep_warnings = {k for k in live if k in self.warning_keys}

        fb.reps, fb.correct_reps = len(self.reps), self.correct_reps
        fb.last_rep = self.reps[-1] if self.reps else None
        fb.live_issues = live

        # Мессеж сонгох дараалал: давталтын үр дүн > идэвхтэй алдаа > төлөвийн зөвлөмж
        if fb.last_rep is not None and t <= self.result_until:
            if fb.last_rep.correct and self.fast_warning in fb.last_rep.warnings:
                fb.message, fb.level = self.fast_warning, "info"   # "Зөв! Гэхдээ арай удаан ..."
            elif fb.last_rep.correct:
                fb.message, fb.level = "good_rep", "ok"
            else:
                fb.message, fb.level = fb.last_rep.issues[0], "warn"
        elif live:
            fb.message, fb.level = live[0], ("info" if live[0] in self.warning_keys else "warn")
        else:
            fb.message = {"idle": self.idle_message, "top": "ready" if not self.reps else "keep_going",
                          "down": "go_down", "bottom": "depth_ok", "up": "go_up"}[fb.state]
            fb.level = "info"
        return fb
