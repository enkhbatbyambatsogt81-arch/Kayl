"""Дасгалыг автоматаар таних (2.0): хүн зогсож байна уу (squat), суниалтын байрлалд байна уу (push-up).

Санааг Google ML Kit / MediaPipe-ийн "Pose classification" жишээнээс авсан
(https://developers.google.com/ml-kit/vision/pose-detection/classifying-poses, Apache-2.0):
  1) кадр бүрт анги бүрийн итгэлийн оноо гаргана;
  2) оноог сүүлийн 10 кадрын цонхон дээр EMA-гаар тэгшитгэнэ (ML Kit EMASmoothing: window 10, alpha 0.2);
  3) ангид "орох" ба "гарах" хоёр өөр босготой (ML Kit RepetitionCounter: 6/10 ба 4/10) тул
     хоёр ангийн хил дээр шийдвэр нааш цааш үсэрдэггүй (hysteresis).
ML Kit кадрын оноог k-NN ангилагчаар (сургалтын олон зурагтай) гаргадаг. Бидэнд ердөө хоёр анги
байгаа бөгөөд тэдгээр нь биеийн чиглэлээр (босоо / хэвтээ) тод ялгардаг тул сургалтын өгөгдөл шаардахгүй
энгийн геометр дүрмээр сольсон. Код нь бие даан бичсэн (ML Kit-ийн кодоос хуулаагүй).
"""

from __future__ import annotations

from collections import deque

import numpy as np

from .geometry import angle_from_horizontal
from .pose import L_ANKLE, L_HIP, L_SHOULDER, R_ANKLE, R_HIP, R_SHOULDER, Pose

CLASSES = ("squat", "pushup")


def posture_scores(pose: Pose) -> dict[str, float]:
    """Нэг кадрын итгэлийн оноо 0..1. Мөр -> шагайн шугам хэвтээ (<=30°) бол суниалт,
    босоо (>=60°) бол зогсож / сууж байна (squat). Хооронд нь шугаман шилжинэ."""
    p = pose.img[:, :2]
    sh = (p[L_SHOULDER] + p[R_SHOULDER]) / 2
    hip = (p[L_HIP] + p[R_HIP]) / 2
    ank = (p[L_ANKLE] + p[R_ANKLE]) / 2
    tilt = angle_from_horizontal(sh, ank)
    if np.isnan(tilt):
        return {"squat": 0.0, "pushup": 0.0}
    plank = float(np.clip((60.0 - tilt) / 30.0, 0.0, 1.0))
    # Хэвтээ байрлалд хонго мөр, шагайн дунд орчимд байх ёстой (хажуу тийш хэвтсэн, суусан бол үгүй)
    if plank > 0:
        span = np.linalg.norm(sh - ank) + 1e-6
        along = float(np.dot(hip - ank, sh - ank) / span ** 2)
        if not 0.2 <= along <= 0.85:
            plank *= 0.3
    return {"pushup": plank, "squat": 1.0 - plank}


class WindowEMA:
    """Сүүлийн window утгын жигнэсэн дундаж: шинэ утгын жин 1, түүний өмнөхийнх (1-alpha), ... ."""

    def __init__(self, window=10, alpha=0.2):
        self.alpha = alpha
        self.buf = deque(maxlen=window)

    def update(self, x):
        self.buf.appendleft(float(x))
        w = (1.0 - self.alpha) ** np.arange(len(self.buf))
        return float(np.dot(w, np.array(self.buf)) / w.sum())

    def reset(self):
        self.buf.clear()


class ExerciseRecognizer:
    """Кадр бүрт update(pose, t) дуудна. Тогтвортой танигдсан дасгалыг (эсвэл None) буцаана."""

    def __init__(self, enter=0.6, exit=0.4, window=10, alpha=0.2, hold_seconds=0.8, reset_seconds=0.5):
        self.enter, self.exit = enter, exit
        self.hold_seconds = hold_seconds      # шинэ ангид орсноос хойш хэдэн секунд тогтвортой байх вэ
        self.reset_seconds = reset_seconds    # хүн удаан алдагдвал санах ойг цэвэрлэнэ (ML Kit: 100 мс)
        self.smooth = {c: WindowEMA(window, alpha) for c in CLASSES}
        self.reset()

    def reset(self):
        for s in self.smooth.values():
            s.reset()
        self.current = None        # "орсон" анги (hysteresis)
        self.since = None
        self.confidence = {c: 0.0 for c in CLASSES}
        self.last_t = None

    def update(self, pose: Pose | None, t: float):
        if pose is None:
            if self.last_t is not None and t - self.last_t > self.reset_seconds:
                self.reset()
            return None
        if self.last_t is not None and t - self.last_t > self.reset_seconds:
            self.reset()
        self.last_t = t
        raw = posture_scores(pose)
        self.confidence = {c: self.smooth[c].update(raw[c]) for c in CLASSES}
        if self.current is not None and self.confidence[self.current] < self.exit:
            self.current = None
        if self.current is None:
            best = max(CLASSES, key=self.confidence.get)
            if self.confidence[best] > self.enter:
                self.current, self.since = best, t
        if self.current is not None and t - self.since >= self.hold_seconds:
            return self.current
        return None
