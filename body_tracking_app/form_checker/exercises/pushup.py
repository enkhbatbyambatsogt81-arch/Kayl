"""Гар дээр суниалт (push-up)-ын шинжилгээ.

Камер хажуу талаас харсан байх шаардлагатай.
Гол өнцөг: тохой (мөр-тохой-бугуй).
Шалгах алдаа:
  * хангалттай доошоо бууж чадаагүй (тохойн хамгийн бага өнцөг > depth_angle)
  * бэлхүүс унжсан (мөр-хонго-шагайн шугамаас хонго доор)
  * бөгс өргөгдсөн (хонго шугамаас дээр)
  * дээд байрлалд гараа бүрэн тэнийлгээгүй
Сануулга (2.0): хэт хурдан давталт (оноог бууруулна, давталтыг буруу болгохгүй).
"""

from __future__ import annotations

from ..config import CommonConfig, PushupConfig
from ..geometry import angle_3pt, angle_from_horizontal, signed_side_of_line
from .base import ExerciseAnalyzer


class PushupAnalyzer(ExerciseAnalyzer):
    name = "pushup"
    key_joints = ("shoulder", "elbow", "wrist", "hip", "ankle")
    shallow_issue = "pushup_shallow"
    not_up_issue = "pushup_not_up"
    fast_warning = "pushup_fast"
    idle_message = "pushup_arms"

    def __init__(self, cfg: PushupConfig | None = None, common: CommonConfig | None = None):
        super().__init__(cfg or PushupConfig(), common)

    def measure(self, pose, side, view, in_rep):
        cfg = self.cfg
        if view == "front":
            return None, {}, {}, "turn_side"

        p = pose.img[:, :2]
        sh, el, wr = p[side["shoulder"]], p[side["elbow"]], p[side["wrist"]]
        hip, ank = p[side["hip"]], p[side["ankle"]]

        tilt = self.smooth("body_tilt", angle_from_horizontal(sh, ank), degrees=True)
        metrics = {"body_tilt": tilt}
        # Бие хэвтээ, гар мөрнөөс доош газар тулсан байх ёстой
        if tilt > cfg.max_body_tilt or wr[1] < sh[1]:
            return None, metrics, {}, "get_in_plank"

        elbow = angle_3pt(sh, el, wr)
        line = self.smooth("body_line", angle_3pt(sh, hip, ank), degrees=True)
        side_of_line = self.smooth("hip_side", signed_side_of_line(hip, sh, ank))
        metrics["elbow"] = elbow
        metrics["body_line"] = line

        issues = {}
        if line < cfg.min_body_line:
            below = side_of_line > 0
            issues["pushup_sag" if below else "pushup_pike"] = [side["hip"]]
        return elbow, metrics, issues, None
