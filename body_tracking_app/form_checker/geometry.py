"""Өнцөг, вектор, тэгшитгэлийн туслах функцууд."""

import math

import numpy as np


def angle_3pt(a, b, c):
    """b цэг дээрх a-b-c өнцөг (градус). 2D болон 3D цэг хоёуланд ажиллана."""
    a, b, c = np.asarray(a, float), np.asarray(b, float), np.asarray(c, float)
    ba, bc = a - b, c - b
    denom = np.linalg.norm(ba) * np.linalg.norm(bc)
    if denom < 1e-9:
        return float("nan")
    cos = float(np.dot(ba, bc) / denom)
    return math.degrees(math.acos(max(-1.0, min(1.0, cos))))


def angle_from_vertical(p_low, p_high):
    """p_low -> p_high векторын босоо тэнхлэгээс хазайх өнцөг (градус).

    Зургийн болон MediaPipe world координатад y тэнхлэг доошоо чиглэдэг,
    тиймээс "дээш" чиглэл нь (0, -1[, 0]).
    """
    v = np.asarray(p_high, float) - np.asarray(p_low, float)
    up = np.zeros_like(v)
    up[1] = -1.0
    n = np.linalg.norm(v)
    if n < 1e-9:
        return float("nan")
    cos = float(np.dot(v, up) / n)
    return math.degrees(math.acos(max(-1.0, min(1.0, cos))))


def angle_from_horizontal(p1, p2):
    """p1 -> p2 шугам хэвтээ хавтгайгаас хэдэн градус хазайж байгаа вэ (0 = хэвтээ)."""
    return 90.0 - min(angle_from_vertical(p1, p2), angle_from_vertical(p2, p1))


def signed_side_of_line(p, a, b):
    """2D: p цэг a->b шугамын аль талд байгаа (зургийн y доошоо).

    Эерэг утга = шугамаас доор (зурган дээр), сөрөг = дээр.
    Утгыг шугамын уртад хувааж нормчилсон.
    """
    p, a, b = (np.asarray(x, float)[:2] for x in (p, a, b))
    ab = b - a
    n = np.linalg.norm(ab)
    if n < 1e-9:
        return 0.0
    # a->b-д перпендикуляр, "доош" (y+) тийш чиглэсэн нэгж вектор
    normal = np.array([-ab[1], ab[0]]) / n
    if normal[1] < 0:
        normal = -normal
    return float(np.dot(p - a, normal) / n)


class OneEuroFilter:
    """1€ шүүлтүүр (One Euro Filter) - хурдаас хамаарч тасалгааны давтамжаа өөрчилдөг low-pass шүүлтүүр.

    Casiez, Roussel, Vogel. "1€ Filter: A Simple Speed-Based Low-Pass Filter for Noisy Input in
    Interactive Systems", CHI 2012, https://doi.org/10.1145/2207676.2208639
    Лавлах хэрэгжүүлэлт: https://github.com/casiez/OneEuroFilter (BSD-3-Clause, Inria).
    Энэ код нь өгүүллийн томьёогоор бие даан бичсэн хувилбар (лавлах кодоос хуулаагүй).

    Санаа: хөдөлгөөн удаан үед тасалгааны давтамж бага (min_cutoff) -> чичиргээг сайн дарна;
    хурдан үед давтамж өснө (cutoff = min_cutoff + beta * |хурд|) -> хоцрогдол бага.
    Тогтмол alpha-тай EMA нэг л тохиргоогоор энэ хоёрын аль нэгийг нь золиослодог.
    """

    def __init__(self, min_cutoff=1.0, beta=0.0, d_cutoff=1.0, freq=30.0):
        self.min_cutoff, self.beta, self.d_cutoff = float(min_cutoff), float(beta), float(d_cutoff)
        self.freq = float(freq)  # хугацааны тэмдэг өгөөгүй үед ашиглах давтамж (Гц)
        self.reset()

    @staticmethod
    def _alpha(cutoff, dt):
        tau = 1.0 / (2.0 * math.pi * cutoff)
        return 1.0 / (1.0 + tau / dt)

    @property
    def value(self):
        return self.x_hat

    def update(self, x, t=None):
        if x is None or (isinstance(x, float) and math.isnan(x)):
            return self.x_hat
        x = float(x)
        if self.x_hat is None:
            self.x_prev = self.x_hat = x
            self.dx_hat = 0.0
            self.t_prev = t
            return x
        dt = 1.0 / self.freq
        if t is not None and self.t_prev is not None and t > self.t_prev:
            dt = t - self.t_prev
        self.t_prev = t
        # 1) хурдыг (уламжлал) тооцоод түүнийг тогтмол d_cutoff-оор шүүнэ
        dx = (x - self.x_prev) / dt
        a_d = self._alpha(self.d_cutoff, dt)
        self.dx_hat = a_d * dx + (1 - a_d) * self.dx_hat
        # 2) хурдаас хамаарах тасалгааны давтамжаар утгыг шүүнэ
        cutoff = self.min_cutoff + self.beta * abs(self.dx_hat)
        a = self._alpha(cutoff, dt)
        self.x_hat = a * x + (1 - a) * self.x_hat
        self.x_prev = x
        return self.x_hat

    def reset(self):
        self.x_hat = None
        self.x_prev = None
        self.dx_hat = 0.0
        self.t_prev = None


class AngleFilter:
    """Медиан (сүүлийн n утга) + тэгшитгэл: гэнэтийн үсрэлтийг (outlier) арилгаад жигд болгоно.

    kind="one_euro" (2.0 хувилбараас анхдагч): медиан -> 1€ шүүлтүүр.
    kind="ema" (1.x хувилбар): медиан -> тогтмол alpha-тай EMA.
    """

    def __init__(self, alpha=0.5, median_window=5, kind="ema", min_cutoff=1.0, beta=0.0, d_cutoff=1.0):
        self.window = median_window
        self.buf = []
        if kind == "one_euro":
            self.ema = OneEuroFilter(min_cutoff, beta, d_cutoff)
        else:
            self.ema = EMA(alpha)

    @property
    def value(self):
        return self.ema.value

    def update(self, x, t=None):
        if x is None or (isinstance(x, float) and math.isnan(x)):
            return self.ema.value
        self.buf.append(float(x))
        if len(self.buf) > self.window:
            self.buf.pop(0)
        m = float(np.median(self.buf)) if self.window > 1 else float(x)
        return self.ema.update(m, t) if isinstance(self.ema, OneEuroFilter) else self.ema.update(m)

    def reset(self):
        self.buf = []
        self.ema.reset()


class EMA:
    """Экспоненциал хөдөлгөөнт дундаж: шуугиантай өнцгийг жигд болгоно."""

    def __init__(self, alpha):
        self.alpha = alpha
        self.value = None

    def update(self, x):
        if x is None or (isinstance(x, float) and math.isnan(x)):
            return self.value
        if self.value is None:
            self.value = float(x)
        else:
            self.value = self.alpha * float(x) + (1 - self.alpha) * self.value
        return self.value

    def reset(self):
        self.value = None
