"""Дахин ашиглагдах жижиг элементүүд: карт, тоон хавтан, давталтын цэгүүд, график, дүрс."""

from __future__ import annotations

import tkinter as tk
from collections import deque

import customtkinter as ctk
import numpy as np
from PIL import Image, ImageDraw

from .theme import ACCENT, BAD, BORDER, CARD, GOOD, MUTED, TEXT, TEXT2, ZONE, canvas_font, font, pick


class Card(ctk.CTkFrame):
    def __init__(self, master, **kw):
        kw.setdefault("fg_color", CARD)
        kw.setdefault("corner_radius", 14)
        kw.setdefault("border_width", 1)
        kw.setdefault("border_color", BORDER)
        super().__init__(master, **kw)


class StatTile(Card):
    """Нэг тоог томоор харуулах хавтан (жишээ нь «Нарийвчлал 80%»)."""

    def __init__(self, master, label, value="–", sub=""):
        super().__init__(master)
        self.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(self, text=label, font=font(13), text_color=TEXT2, anchor="w").grid(
            row=0, column=0, sticky="ew", padx=16, pady=(12, 0))
        self.value = ctk.CTkLabel(self, text=value, font=font(30, "bold"), text_color=TEXT, anchor="w")
        self.value.grid(row=1, column=0, sticky="ew", padx=16)
        self.sub = ctk.CTkLabel(self, text=sub, font=font(12), text_color=MUTED, anchor="w")
        self.sub.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 12))

    def set(self, value, sub=None):
        self.value.configure(text=value)
        if sub is not None:
            self.sub.configure(text=sub)


class ThemedCanvas(tk.Canvas):
    """Өнгөний горим эсвэл хэмжээ солигдоход дахин зурагддаг tk.Canvas.

    tk.Canvas-ийг CustomTkinter өөрөө томруулдаггүй тул өндөр, зай, фонтыг 100%-ийн пикселээр бичээд
    self.s-ээр үржүүлнэ (Windows-ийн томруулалт, «Хэмжээ» тохиргоо). Ингэснээр бусад элементтэй ижил хэмжээтэй.
    """

    def __init__(self, master, height=120, bg_pair=CARD, **kw):
        super().__init__(master, height=height, highlightthickness=0, bd=0, **kw)
        self.bg_pair = bg_pair
        self.base_height = height
        self.s = 1.0
        # Энгийн tk.Tk цонхонд (тест) CustomTkinter-ийн томруулалт байхгүй
        self._tracked = isinstance(self.winfo_toplevel(), (ctk.CTk, ctk.CTkToplevel))
        if self._tracked:
            self.s = ctk.ScalingTracker.get_widget_scaling(self)
            ctk.ScalingTracker.add_widget(self._set_scaling, self)
            self.configure(height=round(height * self.s))
        self.bind("<Configure>", lambda e: self.redraw())

    def _set_scaling(self, widget_scaling, _window_scaling):
        self.s = widget_scaling
        self.configure(height=round(self.base_height * self.s))
        self.redraw()

    def set_base_height(self, height):
        self.base_height = height
        self.configure(height=round(height * self.s))

    def f(self, px, weight="normal"):
        """Канвасын фонт: px нь 100%-ийн хэмжээ."""
        return canvas_font(px * self.s, weight)

    def destroy(self):
        if self._tracked:
            ctk.ScalingTracker.remove_widget(self._set_scaling, self)
        super().destroy()

    def redraw(self):
        self.configure(bg=pick(self.bg_pair))
        self.delete("all")
        self.draw(max(self.winfo_width(), 10), max(self.winfo_height(), 10))

    def draw(self, w, h):
        pass


class RepDots(ThemedCanvas):
    """Сетийн давталт бүр: ногоон = зөв, улаан = алдаатай, хоосон дугуй = үлдсэн."""

    def __init__(self, master, **kw):
        super().__init__(master, height=34, **kw)
        self.reps, self.target = [], 0

    def set(self, reps, target):
        key = ([r.correct for r in reps], target)
        if key != getattr(self, "_key", None):
            self._key = key
            self.reps, self.target = list(reps), target
            self.redraw()

    def draw(self, w, h):
        n = max(self.target, len(self.reps))
        reps = self.reps if self.target > 0 else self.reps[-14:]
        if self.target <= 0:
            n = len(reps)
        if n == 0:
            return
        s = self.s
        step = min(26 * s, (w - 4 * s) / n)
        r = max(4 * s, min(9 * s, step / 2 - 2 * s))
        for i in range(n):
            cx, cy = 4 * s + r + i * step, h / 2
            if i < len(reps):
                color = GOOD if reps[i].correct else BAD
                self.create_oval(cx - r, cy - r, cx + r, cy + r, fill=color, outline="")
            else:
                self.create_oval(cx - r, cy - r, cx + r, cy + r, outline=pick(MUTED), width=1.5 * s)


class _Tooltip:
    """Канвас дээрх баганын хүрээнд хулгана очиход тайлбар харуулна."""

    def __init__(self, canvas):
        self.canvas = canvas
        self.targets = []  # (x0, y0, x1, y1, [мөрүүд])
        canvas.bind("<Motion>", self._move)
        canvas.bind("<Leave>", lambda e: canvas.delete("tip"))

    def _move(self, e):
        c, s = self.canvas, self.canvas.s
        c.delete("tip")
        for x0, y0, x1, y1, lines in self.targets:
            if x0 <= e.x <= x1 and y0 <= e.y <= y1:
                text = "\n".join(lines)
                tid = c.create_text(0, 0, text=text, anchor="nw", fill=pick(TEXT), font=c.f(13), tags="tip")
                bx0, by0, bx1, by1 = c.bbox(tid)
                tw, th = bx1 - bx0 + 16 * s, by1 - by0 + 12 * s
                x = min(max(e.x + 14 * s, 4 * s), c.winfo_width() - tw - 4 * s)
                y = max(e.y - th - 10 * s, 4 * s)
                rid = c.create_rectangle(x, y, x + tw, y + th, fill=pick(CARD), outline=pick(BORDER), tags="tip")
                c.coords(tid, x + 8 * s, y + 6 * s)
                c.tag_raise(tid, rid)
                return


def _legend(c, x, y, items):
    """items: [(өнгө, текст, "box"|"dot"|"dash")]. Баруун дээд буланд зурна, x нь баруун ирмэг."""
    s = c.s
    for color, label, kind in reversed(items):
        tid = c.create_text(x, y, text=label, anchor="e", fill=pick(TEXT2), font=c.f(13))
        x0 = c.bbox(tid)[0]
        if kind == "box":
            c.create_rectangle(x0 - 16 * s, y - 5 * s, x0 - 6 * s, y + 5 * s, fill=color, outline="")
        elif kind == "dot":
            c.create_oval(x0 - 16 * s, y - 5 * s, x0 - 6 * s, y + 5 * s, fill=color, outline="")
        else:
            c.create_line(x0 - 22 * s, y, x0 - 6 * s, y, fill=color, dash=(4, 3), width=2 * s)
        x = x0 - 32 * s


class AngleTrace(ThemedCanvas):
    """Бодит цагийн хөдөлгөөний график: гол үеийн өнцөг сүүлийн WINDOW секундэд.

    Ногоон бүс = зорилтот гүнд хүрсэн; давталт бүрийн хамгийн гүн цэгийг ногоон/улаан цэгээр тэмдэглэнэ.
    Тогтмол хэсгийг (тор, бүс, шошго) зөвхөн хэмжээ/өнгө солигдоход, шугамыг кадр бүрт зурна.
    """

    WINDOW = 10.0
    Y0, Y1 = 50.0, 185.0

    def __init__(self, master, **kw):
        super().__init__(master, height=140, **kw)
        self.points = deque()   # (t, өнцөг эсвэл None)
        self.marks = deque()    # (t, өнцөг, зөв эсэх, дугаар)
        self.depth = 100.0
        self.now = 0.0
        self._last_rep_t = -1e9
        self._box = (0, 0, 1, 1)

    def reset(self, depth):
        self.points.clear()
        self.marks.clear()
        self.depth, self.now = float(depth), 0.0
        self._last_rep_t = -1e9
        self.redraw()

    def push(self, t, angle, rep=None, rep_no=0):
        """Шинэ кадр нэмнэ. rep = энэ кадрт бүртгэгдсэн давталт (RepResult) эсвэл None."""
        if self.points and t < self.points[-1][0]:  # видео дахин эхэлсэн гэх мэт
            self.points.clear()
            self.marks.clear()
            self._last_rep_t = -1e9
        self.now = t
        self.points.append((t, angle))
        if rep is not None:
            # Өмнөх давталт бүртгэгдсэнээс хойших хамгийн бага өнцөгтэй цэг = энэ давталтын хамгийн гүн цэг
            cand = [(a, tt) for tt, a in self.points if a is not None and tt > self._last_rep_t]
            if cand:
                a, tt = min(cand)
                self.marks.append((tt, a, rep.correct, rep_no))
            self._last_rep_t = t
        while self.points and self.points[0][0] < t - self.WINDOW - 0.5:
            self.points.popleft()
        while self.marks and self.marks[0][0] < t - self.WINDOW:
            self.marks.popleft()
        self._draw_dynamic()

    def _xy(self, t, a):
        x0, y0, x1, y1 = self._box
        x = x1 - (self.now - t) / self.WINDOW * (x1 - x0)
        a = min(max(a, self.Y0), self.Y1)
        return x, y1 - (a - self.Y0) / (self.Y1 - self.Y0) * (y1 - y0)

    def draw(self, w, h):
        s = self.s
        self._box = (42 * s, 26 * s, w - 12 * s, h - 22 * s)  # дээд хэсэгт тайлбар (legend), шугамтай давхцахгүй
        x0, y0, x1, y1 = self._box
        _, yd = self._xy(self.now, self.depth)
        self.create_rectangle(x0, yd, x1, y1, fill=pick(ZONE), outline="")
        for v in ((60, 90, 120, 150, 180) if y1 - y0 > 70 * s else (60, 120, 180)):
            _, y = self._xy(self.now, v)
            self.create_line(x0, y, x1, y, fill=pick(BORDER))
            self.create_text(x0 - 6 * s, y, text=f"{v}°", anchor="e", fill=pick(MUTED), font=self.f(12))
        self.create_line(x0, yd, x1, yd, fill=pick(TEXT2), dash=(5, 4), width=2 * s)
        for k in range(0, int(self.WINDOW) + 1, 2):
            x = x1 - k / self.WINDOW * (x1 - x0)
            self.create_text(x, y1 + 11 * s, text="одоо" if k == 0 else f"−{k} с", fill=pick(MUTED),
                             font=self.f(12), anchor="e" if k == 0 else "center")
        _legend(self, x1, 10 * s, [(GOOD, "Зөв", "dot"), (BAD, "Алдаатай", "dot"),
                                   (pick(TEXT2), f"Зорилт ≤ {self.depth:.0f}°", "dash")])
        self._draw_dynamic()

    def _draw_dynamic(self):
        self.delete("dyn")
        if not self.points:
            return
        s = self.s
        # None (хүн харагдахгүй) үед шугамыг таслана
        seg = []
        for t, a in self.points:
            if a is None:
                if len(seg) >= 4:
                    self.create_line(*seg, fill=pick(ACCENT), width=2 * s, tags="dyn")
                seg = []
            else:
                seg.extend(self._xy(t, a))
        if len(seg) >= 4:
            self.create_line(*seg, fill=pick(ACCENT), width=2 * s, tags="dyn")
        r = 6 * s
        for t, a, ok, n in self.marks:
            x, y = self._xy(t, a)
            self.create_oval(x - r - 2 * s, y - r - 2 * s, x + r + 2 * s, y + r + 2 * s, fill=pick(CARD), outline="",
                             tags="dyn")
            self.create_oval(x - r, y - r, x + r, y + r, fill=GOOD if ok else BAD, outline="", tags="dyn")
            self.create_text(x, y + r + 9 * s, text=str(n), fill=pick(TEXT2), font=self.f(12), tags="dyn")


class RepChart(ThemedCanvas):
    """Давталт бүрийн гүн (180° − хамгийн бага өнцөг), сетээр бүлэглэсэн, зорилтот гүний шугамтай."""

    def __init__(self, master, **kw):
        super().__init__(master, height=230, **kw)
        self.tip = _Tooltip(self)
        self.sets, self.target_bend, self.issue_name, self.joint = [], 80, (lambda k: k), "өвдөг"

    def set_data(self, sets, depth_angle, issue_name, joint):
        self.sets = [s for s in sets if s]
        self.target_bend = 180 - depth_angle
        self.issue_name, self.joint = issue_name, joint
        self.redraw()

    def draw(self, w, h):
        self.tip.targets = []
        s = self.s
        left, right, top, bottom = 44 * s, 12 * s, 28 * s, 40 * s
        reps = [r for st in self.sets for r in st]
        if not reps:
            self.create_text(w / 2, h / 2, text="Давталт алга", fill=pick(MUTED), font=self.f(16))
            return
        ymax = max(120, max(180 - r.min_angle for r in reps) + 10)
        ph = h - top - bottom
        y_of = lambda v: top + ph * (1 - v / ymax)  # noqa: E731
        for v in range(0, int(ymax) + 1, 30):
            self.create_line(left, y_of(v), w - right, y_of(v), fill=pick(BORDER))
            self.create_text(left - 8 * s, y_of(v), text=f"{v}°", anchor="e", fill=pick(MUTED), font=self.f(12))
        gap_set = 18 * s
        n, ns = len(reps), len(self.sets)
        slot = (w - left - right - gap_set * (ns - 1)) / n
        bw = max(4 * s, min(34 * s, slot - 2 * s))  # баганын хооронд зай үлдээнэ
        x = left
        for si, st in enumerate(self.sets):
            x_start = x
            for r in st:
                bend = 180 - r.min_angle
                cx = x + slot / 2
                y0 = y_of(bend)
                self.create_rectangle(cx - bw / 2, y0, cx + bw / 2, y_of(0), fill=GOOD if r.correct else BAD,
                                      outline="")
                status = "Зөв" if r.correct else "Алдаатай: " + ", ".join(self.issue_name(i) for i in r.issues)
                lines = [f"Давталт #{r.index}  ·  оноо {getattr(r, 'score', 100)}",
                         f"{self.joint.capitalize()}: {r.min_angle:.0f}°  (гүн {bend:.0f}°)",
                         f"Хугацаа: {r.duration:.1f} с", status]
                if getattr(r, "warnings", None):
                    lines.append("Сануулга: " + ", ".join(self.issue_name(i) for i in r.warnings))
                self.tip.targets.append((x, top, x + slot, y_of(0), lines))
                x += slot
            if ns > 1:
                self.create_text((x_start + x) / 2, h - bottom + 22 * s, text=f"Сет {si + 1}", fill=pick(TEXT2),
                                 font=self.f(13))
            x += gap_set
        if n <= 30:
            x = left
            for st in self.sets:
                for k, r in enumerate(st, 1):
                    self.create_text(x + slot / 2, h - bottom + 8 * s, text=str(k), fill=pick(MUTED),
                                     font=self.f(12))
                    x += slot
                x += gap_set
        yt = y_of(self.target_bend)
        self.create_line(left, yt, w - right, yt, fill=pick(TEXT2), dash=(5, 4), width=2 * s)
        _legend(self, w - right, 12 * s, [(GOOD, "Зөв", "box"), (BAD, "Алдаатай", "box"),
                                          (pick(TEXT2), f"Зорилт: {self.joint} ≤ {180 - self.target_bend:.0f}°",
                                           "dash")])


SHORT_NAMES = {"squat": "Squat", "pushup": "Push-up"}


class HistoryChart(ThemedCanvas):
    """Сүүлийн дасгалууд: зөв (ногоон) ба алдаатай (улаан) давталтын тоо, давхарласан багана."""

    def __init__(self, master, **kw):
        super().__init__(master, height=240, **kw)
        self.tip = _Tooltip(self)
        self.records, self.ex_name = [], (lambda k: k)

    def set_data(self, records, ex_name):
        self.records, self.ex_name = list(reversed(records[:14])), ex_name  # хуучнаас шинэ рүү
        self.redraw()

    def draw(self, w, h):
        self.tip.targets = []
        s = self.s
        left, right, top, bottom = 40 * s, 12 * s, 30 * s, 44 * s
        if not self.records:
            return
        ymax = max(10, max(r.reps for r in self.records) * 1.1)  # дээд талд бага зэрэг зай
        step = 5 if ymax <= 40 else 10
        ymax = int(np.ceil(ymax / step) * step)
        ph = h - top - bottom
        y_of = lambda v: top + ph * (1 - v / ymax)  # noqa: E731
        for v in range(0, ymax + 1, step):
            self.create_line(left, y_of(v), w - right, y_of(v), fill=pick(BORDER))
            self.create_text(left - 8 * s, y_of(v), text=str(v), anchor="e", fill=pick(MUTED), font=self.f(12))
        slot = (w - left - right) / len(self.records)
        bw = max(6 * s, min(40 * s, slot * 0.6))
        for i, r in enumerate(self.records):
            cx = left + slot * (i + 0.5)
            yb, yc = y_of(0), y_of(r.correct)
            if r.correct:
                self.create_rectangle(cx - bw / 2, yc, cx + bw / 2, yb, fill=GOOD, outline="")
            if r.reps > r.correct:
                # Бага зэрэг зай: давхарласан хэсгүүдийг ялгана
                self.create_rectangle(cx - bw / 2, y_of(r.reps), cx + bw / 2, yc - (2 * s if r.correct else 0),
                                      fill=BAD, outline="")
            self.create_text(cx, h - bottom + 10 * s, text=SHORT_NAMES.get(r.exercise, r.exercise),
                             fill=pick(TEXT2), font=self.f(12))
            self.create_text(cx, h - bottom + 24 * s, text=r.when.strftime("%m/%d %H:%M"), fill=pick(MUTED),
                             font=self.f(11))
            self.tip.targets.append((cx - slot / 2, top, cx + slot / 2, yb, [
                r.when.strftime("%Y-%m-%d %H:%M"), self.ex_name(r.exercise),
                f"Давталт: {r.reps}, зөв: {r.correct} ({r.accuracy * 100:.0f}%)"]))
        _legend(self, w - right, 12 * s, [(GOOD, "Зөв давталт", "box"), (BAD, "Алдаатай давталт", "box")])


def stick_figure(exercise, size=(200, 120), color=(42, 120, 214), bg=None, start=False):
    """Дасгалын энгийн араг ясны дүрс (синтетик загвараас). start=True бол эхлэх байрлал."""
    from tools.synthetic import project, pushup_skeleton, squat_skeleton

    from ..pose import SKELETON

    if exercise == "squat":
        P = squat_skeleton(175, [], 0.0) if start else squat_skeleton(92, [], 0.95)
    else:
        P = pushup_skeleton(172, [], 0.0) if start else pushup_skeleton(95, [], 0.9)
    pose = project(P, "side", noise_px=0, rng=np.random.default_rng(0))
    pts = pose.img[:, :2]
    used = sorted({i for a, b in SKELETON for i in (a, b)} | {0})
    lo, hi = pts[used].min(axis=0), pts[used].max(axis=0)
    W, H = size[0] * 3, size[1] * 3  # 3 дахин том зураад жижгэрүүлнэ (гөлгөр ирмэг)
    scale = min((W - 60) / (hi[0] - lo[0]), (H - 60) / (hi[1] - lo[1]))
    off = np.array([W, H]) / 2 - (lo + hi) / 2 * scale
    q = pts * scale + off
    img = Image.new("RGBA", (W, H), bg or (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    lw = 14
    for a, b in SKELETON:
        d.line([tuple(q[a]), tuple(q[b])], fill=color, width=lw, joint="curve")
    for i in used:
        if i >= 11:
            d.ellipse([q[i][0] - lw / 2, q[i][1] - lw / 2, q[i][0] + lw / 2, q[i][1] + lw / 2], fill=color)
    hx, hy = q[0]
    d.ellipse([hx - 22, hy - 22, hx + 22, hy + 22], fill=color)
    floor_y = max(q[i][1] for i in (29, 30, 31, 32)) + lw
    d.line([(10, floor_y), (W - 10, floor_y)], fill=color + (90,) if len(color) == 3 else color, width=4)
    return img.resize(size, Image.LANCZOS)


def camera_figure(exercise, size=(300, 160), color=(42, 120, 214)):
    """Камерыг хаана тавихыг харуулах дүрс: зүүн талд камер (tripod дээр), баруун талд хажуугаас харагдах хүн,
    дунд нь зайн сум. Push-up-д камер шалнаас намхан байна."""
    W, H = size[0] * 3, size[1] * 3
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    fig_w = int(W * (0.30 if exercise == "squat" else 0.48))
    d = ImageDraw.Draw(img)
    floor = H - 30
    cam_y = int(H * 0.40) if exercise == "squat" else int(H * 0.70)   # линзний өндөр
    cx = 80
    for dx in (-44, 0, 44):  # tripod
        d.line([(cx, cam_y + 30), (cx + dx, floor)], fill=color, width=9)
    d.rounded_rectangle([cx - 50, cam_y - 34, cx + 36, cam_y + 34], radius=12, fill=color)
    d.rectangle([cx + 32, cam_y - 20, cx + 62, cam_y + 20], fill=color)
    d.ellipse([cx - 24, cam_y - 20, cx + 16, cam_y + 20], fill=(255, 255, 255, 230))
    x0, x1, y = cx + 90, W - fig_w - 24, floor - 10   # зайн сум (тасархай)
    x = x0 + 26
    while x < x1 - 30:
        d.line([(x, y), (min(x + 26, x1 - 30), y)], fill=color, width=6)
        x += 44
    d.polygon([(x0, y), (x0 + 28, y - 16), (x0 + 28, y + 16)], fill=color)
    d.polygon([(x1, y), (x1 - 28, y - 16), (x1 - 28, y + 16)], fill=color)
    img = img.resize(size, Image.LANCZOS)
    fw = fig_w // 3
    fh = size[1] - 4 if exercise == "squat" else int(fw * 0.42)
    fig = stick_figure(exercise, (fw, fh), color=color, start=True)
    img.alpha_composite(fig, (size[0] - fw - 2, size[1] - fh - 3))  # шал нь камерын шалтай нэг түвшинд
    return img
