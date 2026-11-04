"""Цайвар / харанхуй горим солих товч (2.4): мөнгөлөг гулсуур, бөмбөлөг дээр нар эсвэл сар.

Хуудас бүрийн баруун дээд буланд байрлана. Дарахад бөмбөлөг нөгөө тал руу гулсаж, бүх апп горимоо солино.
Зургийг Pillow-оор 4 дахин том зурж багасгадаг тул ирмэг нь гөлгөр, ямар ч DPI-д тод харагдана.
"""

from __future__ import annotations

import math
import tkinter as tk

import customtkinter as ctk
from PIL import Image, ImageDraw, ImageFilter, ImageTk

from .theme import BG, pick

W, H = 64, 32          # гулсуурын хэмжээ (логик пиксел, 100%-д)
MARGIN = 8             # гэрэлтэлт, сүүдэрт үлдээх зай
SS = 4                 # supersampling


def _scale(widget) -> float:
    try:
        return float(ctk.ScalingTracker.get_widget_scaling(widget))
    except Exception:  # noqa: BLE001
        return 1.0


def _hex(c):
    c = c.lstrip("#")
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))


def _vgradient(size, top, bottom):
    w, h = size
    col = Image.new("RGBA", (1, h))
    for y in range(h):
        t = y / max(1, h - 1)
        col.putpixel((0, y), tuple(round(a + (b - a) * t) for a, b in zip(top, bottom)) + (255,))
    return col.resize((w, h))


def _mask_rounded(size, box, radius):
    m = Image.new("L", size, 0)
    ImageDraw.Draw(m).rounded_rectangle(box, radius=radius, fill=255)
    return m


def _mask_circle(size, box):
    m = Image.new("L", size, 0)
    ImageDraw.Draw(m).ellipse(box, fill=255)
    return m


def render(pos: float, dark: bool, bg: str, scale: float = 1.0, hover: bool = False) -> Image.Image:
    """pos: бөмбөлгийн байрлал 0 (зүүн, цайвар) ... 1 (баруун, харанхуй)."""
    k = scale * SS
    fw, fh = round((W + 2 * MARGIN) * k), round((H + 2 * MARGIN) * k)
    img = Image.new("RGBA", (fw, fh), _hex(bg) + (255,))
    x0, y0 = MARGIN * k, MARGIN * k
    x1, y1 = x0 + W * k, y0 + H * k
    r = H * k / 2
    track = (x0, y0, x1, y1)

    # гадна талын гэрэлтэлт (харанхуйд цагаан туяа) эсвэл зөөлөн сүүдэр (цайварт)
    halo = Image.new("L", (fw, fh), 0)
    off = 0 if dark else 2 * k
    ImageDraw.Draw(halo).rounded_rectangle((x0, y0 + off, x1, y1 + off), radius=r, fill=255)
    halo = halo.filter(ImageFilter.GaussianBlur(radius=(4.5 if dark else 3.5) * k))
    glow_rgb, glow_a = ((255, 255, 255), 0.55 if hover else 0.38) if dark else ((0, 0, 0), 0.20 if hover else 0.14)
    img.paste(Image.new("RGBA", (fw, fh), glow_rgb + (255,)), (0, 0), halo.point(lambda v: round(v * glow_a)))

    # гулсуур: мөнгөлөг босоо градиент, дээд талдаа гялбаа
    body = _vgradient((fw, fh), (250, 250, 250), (196, 197, 200)) if not dark else \
        _vgradient((fw, fh), (236, 237, 240), (168, 170, 175))
    img.paste(body, (0, 0), _mask_rounded((fw, fh), track, r))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle(track, radius=r, outline=(150, 152, 156, 255) if dark else (205, 206, 209, 255),
                        width=max(1, round(k * 0.8)))
    gloss = Image.new("L", (fw, fh), 0)
    ImageDraw.Draw(gloss).rounded_rectangle((x0 + 3 * k, y0 + 1.5 * k, x1 - 3 * k, y0 + H * k * 0.45),
                                            radius=r * 0.6, fill=255)
    gloss = gloss.filter(ImageFilter.GaussianBlur(radius=1.2 * k))
    img.paste(Image.new("RGBA", (fw, fh), (255, 255, 255, 255)), (0, 0), gloss.point(lambda v: round(v * 0.55)))

    # бөмбөлөг
    pad = 3 * k
    kr = r - pad
    cx = x0 + pad + kr + pos * (W * k - 2 * pad - 2 * kr)
    cy = y0 + r
    knob = (cx - kr, cy - kr, cx + kr, cy + kr)
    shadow = _mask_circle((fw, fh), (knob[0], knob[1] + 1.5 * k, knob[2], knob[3] + 1.5 * k))
    shadow = shadow.filter(ImageFilter.GaussianBlur(radius=1.6 * k))
    img.paste(Image.new("RGBA", (fw, fh), (0, 0, 0, 255)), (0, 0), shadow.point(lambda v: round(v * 0.35)))
    t = pos  # цайвар (цагаан) -> харанхуй (бараан) бөмбөлөг
    top = tuple(round(a + (b - a) * t) for a, b in zip((255, 255, 255), (70, 72, 78)))
    bottom = tuple(round(a + (b - a) * t) for a, b in zip((226, 227, 230), (24, 25, 28)))
    img.paste(_vgradient((fw, fh), top, bottom), (0, 0), _mask_circle((fw, fh), knob))
    d = ImageDraw.Draw(img)
    rim = tuple(round(a + (b - a) * t) for a, b in zip((200, 201, 205), (12, 12, 14)))
    d.ellipse(knob, outline=rim + (255,), width=max(1, round(k * 0.7)))

    # дүрс: нар (цайвар) эсвэл сар (харанхуй), шилжих үед бүдгэрч солигдоно
    ir = kr * 0.52
    if t < 0.5:
        a = round(255 * (1 - 2 * t))
        col = (60, 62, 66, a)
        d.ellipse((cx - ir * 0.5, cy - ir * 0.5, cx + ir * 0.5, cy + ir * 0.5), fill=col)
        for i in range(8):
            ang = i * math.pi / 4
            d.line((cx + math.cos(ang) * ir * 0.72, cy + math.sin(ang) * ir * 0.72,
                    cx + math.cos(ang) * ir, cy + math.sin(ang) * ir), fill=col, width=max(1, round(k * 1.4)))
    else:
        a = round(255 * (2 * t - 1))
        moon = Image.new("L", (fw, fh), 0)
        md = ImageDraw.Draw(moon)
        md.ellipse((cx - ir, cy - ir, cx + ir, cy + ir), fill=255)
        md.ellipse((cx - ir * 0.25, cy - ir * 1.15, cx + ir * 1.55, cy + ir * 0.6), fill=0)
        img.paste(Image.new("RGBA", (fw, fh), (245, 245, 247, 255)), (0, 0), moon.point(lambda v: round(v * a / 255)))

    return img.resize((round((W + 2 * MARGIN) * scale), round((H + 2 * MARGIN) * scale)), Image.LANCZOS)


class ThemeToggle(tk.Label):
    """Горим солих товч. app.set_dark(bool)-ыг дуудаж, app.theme_toggles-д бүртгэгдэнэ."""

    def __init__(self, master, app):
        super().__init__(master, bd=0, highlightthickness=0, cursor="hand2", takefocus=1)
        self.app = app
        self.pos = 1.0 if self.is_dark() else 0.0
        self.hover = False
        self._anim = None
        self._photo = None
        self.bind("<Button-1>", lambda e: self.toggle())
        self.bind("<Enter>", lambda e: self._set_hover(True))
        self.bind("<Leave>", lambda e: self._set_hover(False))
        self.bind("<Map>", lambda e: self.sync())
        self.bind("<Destroy>", self._forget, add="+")
        app.theme_toggles.append(self)
        self.redraw()

    def _forget(self, _e=None):
        if self in self.app.theme_toggles:
            self.app.theme_toggles.remove(self)

    @staticmethod
    def is_dark():
        return ctk.get_appearance_mode() == "Dark"

    def _set_hover(self, value):
        self.hover = value
        self.redraw()

    def toggle(self):
        self.app.set_dark(not self.is_dark())
        return "break"

    def sync(self, animate=False):
        """Одоогийн горимд тааруулна (өөр хуудсанд солигдсон байж болно)."""
        target = 1.0 if self.is_dark() else 0.0
        if self._anim is not None:
            self.after_cancel(self._anim)
            self._anim = None
        if animate and self.winfo_ismapped():
            self._animate(self.pos, target, 0)
        else:
            self.pos = target
            self.redraw()

    def _animate(self, start, end, i, steps=8):
        t = (i + 1) / steps
        t = 1 - (1 - t) ** 3   # ease-out
        self.pos = start + (end - start) * t
        self.redraw()
        if i + 1 < steps:
            self._anim = self.after(16, self._animate, start, end, i + 1, steps)
        else:
            self._anim = None

    def redraw(self):
        bg = pick(BG)
        try:
            self._photo = ImageTk.PhotoImage(render(self.pos, self.is_dark(), bg, _scale(self), self.hover),
                                             master=self)
        except tk.TclError:
            return
        self.configure(image=self._photo, bg=bg, activebackground=bg)
