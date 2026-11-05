"""Хуудас хооронд зөөлөн шилжих (3.1).

Tk-д элементийг хагас тунгалаг болгох боломжгүй тул «бүдгэрэх» хөдөлгөөний оронд:

1. Шинэ хуудсыг одоогийнхоо ДООР байрлуулж, бүрэн зурагдтал хүлээнэ. Ингэснээр хуудас хэсэг хэсгээрээ
   зурагдаж, анивчих нь харагдахгүй.
2. Бэлэн болмогц нэг дор дээш нь гаргаж, хуучныг нууна.
3. Шинэ хуудас хэдэн пикселийн зайнаас зөөлөн (ease-out) гулсаж байрандаа сууна.

Хөдөлгөөн цаг хугацаанд тулгуурладаг: удаан компьютерт кадр алгассан ч хугацаандаа дуусна.
"""

from __future__ import annotations

import time
import tkinter as tk

PREPARE_MS = 30      # шинэ хуудас доор нь зурагдах хугацаа
SLIDE_MS = 220       # гулсах хугацаа
FRAME_MS = 15        # ~60 кадр/сек
PAGE_SHIFT = 16      # хуудас доороос дээш (логик пиксел, томруулалтаар өснө)
STEP_SHIFT = 32      # эхлэх урсгалын алхам хажуунаас

FILL = dict(relx=0, rely=0, relwidth=1, relheight=1)


def ease_out(t: float) -> float:
    return 1 - (1 - t) ** 3


def frame_of(page):
    """CTkScrollableFrame-ийн хувьд байрлал, давхарлалтыг гадна талын хүрээ нь эзэмшинэ."""
    return getattr(page, "_parent_frame", page)


def place_fill(page, x=0, y=0):
    page.place(**FILL, x=x, y=y)


class Transition:
    """Нэг шилжилт. finish() дуудвал (дараагийн шилжилт эхлэх үед) шууд эцсийн байрлалд орно."""

    def __init__(self, owner, page, reveal, dx=0, dy=0, prepare_ms=PREPARE_MS, slide_ms=SLIDE_MS):
        self.owner, self.page, self._reveal = owner, page, reveal
        self.dx, self.dy, self.slide_ms = dx, dy, max(1, slide_ms)
        self.revealed = self.done = False
        self._t0 = 0.0
        self._job = owner.after(prepare_ms, self._start)

    def _start(self):
        self._job = None
        try:
            self.owner.update_idletasks()   # үлдсэн байрлал, зурагдалтыг хуудас харагдахаас өмнө дуусгана
        except tk.TclError:
            return
        self._show()
        self._t0 = time.perf_counter()
        self._step()

    def _show(self):
        if not self.revealed:
            self.revealed = True
            self._reveal()

    def _step(self):
        t = min(1.0, (time.perf_counter() - self._t0) * 1000 / self.slide_ms)
        k = 1 - ease_out(t)
        try:
            place_fill(self.page, x=round(self.dx * k), y=round(self.dy * k))
        except tk.TclError:   # цонх хаагдсан
            self.done = True
            return
        if t < 1.0:
            self._job = self.owner.after(FRAME_MS, self._step)
        else:
            self._job = None
            self.done = True

    def finish(self):
        if self.done:
            return
        if self._job is not None:
            try:
                self.owner.after_cancel(self._job)
            except tk.TclError:
                pass
            self._job = None
        try:
            self._show()
            place_fill(self.page)
        except tk.TclError:
            pass
        self.done = True
