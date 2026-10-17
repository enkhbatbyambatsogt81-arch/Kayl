"""Суулт (squat)-ын шинжилгээ.

Гол өнцөг: өвдөг (хонго-өвдөг-шагай).
Шалгах алдаа:
  * гүехэн суусан (өвдөгний хамгийн бага өнцөг > depth_angle)
  * их бие хэт урагш хазайсан
  * өвдөг дотогш орсон (зөвхөн урдаас харахад)
  * урдаас харахад гүнийг сегментүүдийн богинолтоор (foreshortening) тооцно
  * өсгий газраас салсан (зөвхөн хажуугаас харахад)
  * давталтын хооронд бүрэн босоогүй
Сануулга (2.0, давталтыг буруу болгохгүй, зөвхөн оноог бууруулна):
  * хөлийн байрлал хэт нарийн / өргөн (урдаас; Exercise-Correction төслийн санаа)
  * хэт хурдан давталт
"""

from __future__ import annotations

import math
from collections import deque

import numpy as np

from ..config import CommonConfig, SquatConfig
from ..geometry import EMA, angle_3pt, angle_from_vertical
from ..pose import (L_ANKLE, L_FOOT, L_HIP, L_KNEE, L_SHOULDER, R_ANKLE, R_FOOT, R_HIP, R_KNEE,
                    R_SHOULDER)
from .base import ExerciseAnalyzer


class SquatAnalyzer(ExerciseAnalyzer):
    name = "squat"
    key_joints = ("shoulder", "hip", "knee", "ankle")
    shallow_issue = "squat_shallow"
    not_up_issue = "squat_not_up"
    fast_warning = "squat_fast"
    warning_keys = frozenset({"squat_stance_narrow", "squat_stance_wide"})
    idle_message = "squat_stand"

    def __init__(self, cfg: SquatConfig | None = None, common: CommonConfig | None = None):
        super().__init__(cfg or SquatConfig(), common)
        self.heel_baseline = EMA(0.1)
        self.refs = {}  # урдаас харах үеийн босоо байрлалын сегментийн уртын түүх

    def on_view_change(self, view):
        c, cfg = self.counter, self.cfg
        if view == "front":
            c.top, c.start, c.attempt = cfg.front_top_angle, cfg.front_start_angle, cfg.front_attempt_angle
        else:
            c.top, c.start, c.attempt = cfg.top_angle, cfg.start_angle, cfg.attempt_angle

    def _reset_filters(self):
        super()._reset_filters()
        self.refs = {}

    def _foreshortened_angle(self, name, vertical_len, body_width, in_rep):
        """Урдаас харахад сегмент камер руу хазайх тусам зурган дээр богиносно.
        Босоо байх үеийн уртыг (L0) тогтоогоод хазайлтын өнцгийг acos(L / L0)-оор тооцно.

        Хүн камераас холдож/ойртоход бүх урт өөрчлөгдөх тул мөрний өргөнд хуваасан
        харьцааг ашиглана (мөрний өргөн суух үед өөрчлөгддөггүй)."""
        value = vertical_len / max(body_width, 1e-6)
        # acos нь шуугианыг өсгөдөг тул уртыг эхлээд шүүнэ.
        smooth_value = self.smooth("len_" + name, value)
        # Лавлах утга = давталтын гадуурх (босоо зогсож буй) сүүлийн ~5 секундын 80-р перцентиль.
        # Максимум авбал шуугианы оргилыг барьж, лавлах утга хэт томордог.
        buf = self.refs.setdefault(name, deque(maxlen=150))
        if not in_rep or not buf:
            buf.append(smooth_value)
        ref = float(np.percentile(buf, 80))
        # acos нь 1-ийн орчимд маш мэдрэмтгий тул 98%-иас урт бол "босоо" гэж үзнэ
        r = float(np.clip(smooth_value / max(ref * 0.98, 1e-6), 0.0, 1.0))
        return math.degrees(math.acos(r))

    def measure(self, pose, side, view, in_rep):
        cfg = self.cfg
        p = pose.img[:, :2]
        metrics, issues = {}, {}

        if view == "front":
            # Урдаас харахад өвдөг камер руу нугардаг тул хонго-өвдөг-шагайн 2D өнцөг
            # бараг өөрчлөгдөхгүй. Иймд гуя, шилбэ, их бие зурган дээр хэр
            # богиноссоноос (foreshortening) хазайлтын өнцгийг нь тооцоолно:
            #   өвдөгний өнцөг ≈ 180° - гуяны хазайлт - шилбэний хазайлт
            hip_y = (p[L_HIP, 1] + p[R_HIP, 1]) / 2
            knee_y = (p[L_KNEE, 1] + p[R_KNEE, 1]) / 2
            ankle_y = (p[L_ANKLE, 1] + p[R_ANKLE, 1]) / 2
            sh_y = (p[L_SHOULDER, 1] + p[R_SHOULDER, 1]) / 2
            width = self.smooth("shoulder_w", abs(p[L_SHOULDER, 0] - p[R_SHOULDER, 0]))
            thigh = self._foreshortened_angle("thigh", knee_y - hip_y, width, in_rep)
            shank = self._foreshortened_angle("shank", ankle_y - knee_y, width, in_rep)
            knee = 180.0 - thigh - shank
            # Өвдөг зургийн хавтгайд (хажуу тийш) нугарсан бол 2D өнцөг нь илүү бага гарна
            knee_2d = min(angle_3pt(p[L_HIP], p[L_KNEE], p[L_ANKLE]), angle_3pt(p[R_HIP], p[R_KNEE], p[R_ANKLE]))
            knee = min(knee, knee_2d)
            lean = self._foreshortened_angle("torso", hip_y - sh_y, width, in_rep)
            lean_joints = [L_SHOULDER, R_SHOULDER, L_HIP, R_HIP]
            metrics["thigh_tilt"] = thigh
        else:
            knee = angle_3pt(p[side["hip"]], p[side["knee"]], p[side["ankle"]])
            lean = angle_from_vertical(p[side["hip"]], p[side["shoulder"]])
            lean_joints = [side["shoulder"], side["hip"]]
        lean = self.smooth("torso_lean", lean, degrees=True)
        metrics["knee"] = knee
        metrics["torso_lean"] = lean

        if lean > cfg.max_torso_lean:
            issues["squat_lean"] = lean_joints

        if view == "front":
            knee_w = abs(p[L_KNEE, 0] - p[R_KNEE, 0])
            ankle_w = abs(p[L_ANKLE, 0] - p[R_ANKLE, 0])
            ratio = self.smooth("knee_ankle_ratio", knee_w / max(ankle_w, 1e-6))
            metrics["knee_ankle_ratio"] = ratio
            # Зөвхөн мэдэгдэхүйц сууж байх үед шалгана
            if in_rep and knee < self.counter.start - 20 and ratio < cfg.min_knee_ankle_ratio:
                issues["squat_knees_in"] = [L_KNEE, R_KNEE]
            # Хөлийн байрлал: хөлийн хурууны зай / мөрний өргөн (NgoQuocBao1010/Exercise-Correction, MIT).
            # Давталтын хооронд (босоо үед) л хэмжинэ: сууж байхад хөл хөдөлдөггүй, харин мөр урагш бөхийнө.
            vis_ok = min(pose.vis[L_FOOT], pose.vis[R_FOOT]) >= self.common.min_visibility
            if not in_rep and vis_ok:
                stance = self.smooth("stance", abs(p[L_FOOT, 0] - p[R_FOOT, 0]) / max(width, 1e-6))
                metrics["stance_ratio"] = stance
                if stance < cfg.min_stance_ratio:
                    issues["squat_stance_narrow"] = [L_FOOT, R_FOOT]
                elif stance > cfg.max_stance_ratio:
                    issues["squat_stance_wide"] = [L_FOOT, R_FOOT]
        else:
            heel, foot = side["heel"], side["foot"]
            if min(pose.vis[heel], pose.vis[foot]) >= self.common.min_visibility:
                shank = np.linalg.norm(p[side["knee"]] - p[side["ankle"]])
                # Өсгий өргөгдөхөд өсгий дээшилж (y багасна), хөлийн хуруу газарт үлдэнэ
                d = self.smooth("heel", (p[foot, 1] - p[heel, 1]) / max(shank, 1e-6))
                if not in_rep:
                    self.heel_baseline.update(d)
                elif self.heel_baseline.value is not None:
                    lift = d - self.heel_baseline.value
                    metrics["heel_lift"] = lift
                    if lift > cfg.max_heel_lift_ratio:
                        issues["squat_heels"] = [heel]

        return knee, metrics, issues, None
