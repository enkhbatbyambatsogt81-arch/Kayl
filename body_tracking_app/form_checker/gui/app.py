"""Үндсэн цонх: зүүн талын цэс + хуудсууд, тохиргоо хадгалах, товчлуурын удирдлага."""

from __future__ import annotations

import sys
import tkinter as tk
from datetime import datetime

import customtkinter as ctk
from PIL import Image, ImageDraw, ImageTk

from .. import __version__
from ..history import load_history
from ..session import LOG_DIR
from ..settings import load_settings, save_settings
from . import ctk_fixes
from .overlays import Onboarding
from .pages import EX_TITLES, HelpPage, HistoryPage, HomePage, SummaryPage, WorkoutPage
from .theme import (ACCENT, ACCENT_SOFT, BG, BORDER, INSET, MUTED, SEG, SIDEBAR, TEXT, TEXT2, apply_ctk_theme, font,
                    pick)
from .widgets import stick_figure

NAV = [("home", "Дасгал"), ("history", "Түүх"), ("help", "Заавар")]
APPEARANCE = {"light": "Цайвар", "dark": "Харанхуй", "system": "Систем"}
# Цонхны элементүүдийн хэмжээ. Linux-д дэлгэцийн томруулалтыг (HiDPI) CustomTkinter өөрөө мэддэггүй,
# жижиг дэлгэцтэй зөөврийн компьютерт эсрэгээрээ багасгах хэрэгтэй болдог.
SCALES = [0.8, 0.9, 1.0, 1.1, 1.25, 1.5, 1.75, 2.0]
IS_MAC = sys.platform == "darwin"


def scale_label(v):
    return f"{round(v * 100)}%"


def app_icon(size=128):
    """Цонх, taskbar-ын дүрс: хар дөрвөлжин дээр squat хийж буй цагаан дүрс."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    ImageDraw.Draw(img).rounded_rectangle([0, 0, size - 1, size - 1], radius=size // 5, fill=(17, 17, 17, 255))
    pad = size // 8
    img.alpha_composite(stick_figure("squat", (size - 2 * pad, size - 2 * pad), color=(255, 255, 255)), (pad, pad))
    return img


class App(ctk.CTk):
    def __init__(self, log_dir=LOG_DIR):
        ctk_fixes.apply()
        self.settings = load_settings()
        ctk.set_appearance_mode(self.settings["appearance"])
        ctk.set_default_color_theme("blue")
        apply_ctk_theme()   # цагаан, минимал өнгө (theme.py)
        ctk.set_widget_scaling(self.settings["ui_scale"])
        super().__init__(fg_color=BG)
        self.log_dir = log_dir  # дасгалын CSV лог ба түүхийн хавтас
        self.title("Дасгалын хэлбэр шалгагч")
        self._set_icon()
        ui = self.settings["ui_scale"]
        self._fit_to_screen(round(1320 * ui), round(820 * ui))
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.current = None
        self.fullscreen = False

        # --- Зүүн цэс
        self.sidebar = ctk.CTkFrame(self, fg_color=SIDEBAR, corner_radius=0, width=220)
        self.sidebar.grid(row=0, column=0, sticky="nsw")
        self.sidebar.grid_propagate(False)
        self.sidebar.grid_columnconfigure(0, weight=1)
        self.sidebar.grid_rowconfigure(10, weight=1)
        # Цэс ба хуудсын хоорондох нимгэн зураас (CTkFrame 1 пикселийн өргөнийг 0 болгож зурдаггүй тул tk.Frame)
        self.divider = tk.Frame(self.sidebar, width=1, bd=0, highlightthickness=0, bg=pick(BORDER))
        self.divider.place(relx=1.0, y=0, relheight=1.0, anchor="ne")
        ctk.CTkLabel(self.sidebar, text="Хэлбэр шалгагч", font=font(20, "bold"), text_color=TEXT, anchor="w").grid(
            row=0, column=0, sticky="ew", padx=20, pady=(24, 0))
        ctk.CTkLabel(self.sidebar, text=f"Squat · Push-up · v{__version__}", font=font(13), text_color=MUTED,
                     anchor="w").grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 20))
        self.nav = {}
        self._nav_fonts = {False: font(15), True: font(15, "bold")}
        for i, (key, label) in enumerate(NAV):
            b = ctk.CTkButton(self.sidebar, text=label, anchor="w", height=42, font=font(15), corner_radius=10,
                              fg_color="transparent", text_color=TEXT2, hover_color=INSET,
                              command=lambda k=key: self.show(k))
            b.grid(row=2 + i, column=0, sticky="ew", padx=12, pady=3)
            self.nav[key] = b

        # Таны явц: түүхээс товч дүн (дарвал Түүх хуудас нээгдэнэ)
        self.progress = ctk.CTkFrame(self.sidebar, fg_color="transparent", corner_radius=0)
        self.progress.grid(row=6, column=0, sticky="ew", padx=12, pady=(22, 0))
        self.progress.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(self.progress, text="Таны явц", font=font(12), text_color=MUTED, anchor="w").grid(
            row=0, column=0, sticky="ew", padx=8, pady=(0, 4))
        self.progress_lbl = ctk.CTkLabel(self.progress, text="", font=font(13), text_color=TEXT2, anchor="w",
                                         justify="left", wraplength=170)
        self.progress_lbl.grid(row=1, column=0, sticky="ew", padx=8)
        for w in (self.progress, *self.progress.winfo_children()):
            w.bind("<Button-1>", lambda e: self.show("history"))
        ctk.CTkLabel(self.sidebar, text="Өнгөний горим", font=font(12), text_color=MUTED, anchor="w").grid(
            row=11, column=0, sticky="ew", padx=20)
        self.appearance = ctk.CTkSegmentedButton(self.sidebar, values=list(APPEARANCE.values()),
                                                 command=self._on_appearance, font=font(12), **SEG)
        self.appearance.set(APPEARANCE[self.settings["appearance"]])
        self.appearance.grid(row=12, column=0, sticky="ew", padx=14, pady=(4, 12))
        size_row = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        size_row.grid(row=13, column=0, sticky="ew", padx=(20, 14), pady=(0, 20))
        ctk.CTkLabel(size_row, text="Хэмжээ", font=font(12), text_color=MUTED).pack(side="left")
        current = scale_label(self.settings["ui_scale"])
        labels = [scale_label(v) for v in SCALES]
        self.scale_menu = ctk.CTkOptionMenu(size_row, values=labels if current in labels else [*labels, current],
                                            width=92, height=28, font=font(12), command=self._on_scale)
        self.scale_menu.set(current)
        self.scale_menu.pack(side="right")

        # --- Хуудсууд
        self.content = ctk.CTkFrame(self, fg_color="transparent")
        self.content.grid(row=0, column=1, sticky="nsew", padx=20, pady=16)
        self.content.grid_columnconfigure(0, weight=1)
        self.content.grid_rowconfigure(0, weight=1)
        self.pages = {
            "home": HomePage(self.content, self),
            "workout": WorkoutPage(self.content, self),
            "summary": SummaryPage(self.content, self),
            "history": HistoryPage(self.content, self),
            "help": HelpPage(self.content, self),
        }
        self.onboarding = Onboarding(self, on_close=self._onboarding_done,
                                     on_demo=lambda: self.start_workout(source="demo"))
        self.bind("<KeyPress>", self._on_key)
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        if IS_MAC:
            # Cmd+Q эсвэл цэсний Quit: цонхны × товчтой адил камерыг зогсоож, тохиргоог хадгална
            self.createcommand("tk::mac::Quit", self.on_close)
            # Terminal-аас эхлүүлэхэд цонх ард нь нээгдэх нь бий
            self.after(150, self._bring_to_front)
        self.show("home")
        if not self.settings.get("onboarded"):
            self.after(300, self.show_onboarding)  # анх нээхэд л гарна; «Заавар» хуудаснаас дахин нээж болно

    def _set_icon(self):
        try:
            self._icon = ImageTk.PhotoImage(app_icon(), master=self)
            self.iconphoto(True, self._icon)
            # Windows-д CustomTkinter 0.2 секундын дараа өөрийн дүрсийг тавьдаг. Хоосон iconbitmap()
            # дуудлага юуг ч өөрчлөхгүй, харин түүнийг дүрсээ солихгүй болгоно.
            if sys.platform.startswith("win"):
                self.iconbitmap()
        except (tk.TclError, OSError, ImportError):
            pass  # дүрсгүй байсан ч апп ажиллана

    def _bring_to_front(self):
        self.lift()
        self.attributes("-topmost", True)
        self.after(400, lambda: self.attributes("-topmost", False))
        self.focus_force()

    def _fit_to_screen(self, w, h):
        """Дэлгэц жижиг (эсвэл Windows-ийн томруулалт их) бол цонхыг дэлгэцэд багтаана."""
        try:
            scale = self._get_window_scaling()
        except AttributeError:
            scale = 1.0
        sw, sh = self.winfo_screenwidth() / scale, self.winfo_screenheight() / scale
        # 1366×768, 125% томруулалттай зөөврийн компьютерт 1000×640 хамгийн бага хэмжээ дэлгэцээс томордог
        self.minsize(int(min(1000, sw - 20)), int(min(640, sh - 90)))
        if sw < w + 40 or sh < h + 90:
            w, h = int(min(w, sw - 20)), int(min(h, sh - 90))
            self.geometry(f"{w}x{h}+0+0")
            if sys.platform.startswith("win"):
                self.after(50, lambda: self.state("zoomed"))  # бүтэн дэлгэцээр (taskbar-тай) нээнэ
        else:
            self.geometry(f"{w}x{h}+{int((sw - w) / 2)}+{int(max(0, (sh - h) / 2 - 30))}")

    # ---- хуудас солих
    def show(self, name):
        if self.current == "workout" and name != "workout":
            self.pages["workout"].stop()
        for key, page in self.pages.items():
            if key != name:
                page.grid_remove()
        page = self.pages[name]
        page.grid(row=0, column=0, sticky="nsew")
        self.current = name
        # Дасгалын үед зүүн цэсийг нууж видеог томруулна
        if name == "workout":
            self.sidebar.grid_remove()
        else:
            self.sidebar.grid()
        for key, b in self.nav.items():
            active = key == name or (key == "home" and name == "summary")
            b.configure(fg_color=ACCENT_SOFT if active else "transparent",
                        text_color=ACCENT if active else TEXT2, font=self._nav_fonts[active])
        if name == "history":
            page.refresh()
        if name != "workout":
            self.refresh_progress()
        self.focus_set()

    def refresh_progress(self):
        records = load_history(self.log_dir)
        if not records:
            self.progress_lbl.configure(text="Одоогоор дасгал алга.\nЭхний дасгалаа эхлүүлээрэй!")
            return
        last = records[0]
        now = datetime.now()
        week = [r for r in records if (now - r.when).days < 7]
        reps = sum(r.reps for r in week)
        name = EX_TITLES.get(last.exercise, last.exercise).split(" (")[0]
        lines = [f"Сүүлд {last.when:%m/%d}: {name}", f"{last.correct}/{last.reps} зөв давталт", "", "Сүүлийн 7 хоногт:"]
        if week:
            acc = sum(r.correct for r in week) / max(reps, 1)
            lines += [f"{len(week)} дасгал · {reps} давталт", f"Нарийвчлал {acc * 100:.0f}%"]
        else:
            lines.append("дасгал хийгээгүй")
        self.progress_lbl.configure(text="\n".join(lines))

    def show_onboarding(self):
        if self.current == "workout":
            return
        self.onboarding.open()

    def _onboarding_done(self):
        self.settings["onboarded"] = True
        save_settings(self.settings)

    def toggle_fullscreen(self, value=None):
        self.fullscreen = (not self.fullscreen) if value is None else bool(value)
        self.attributes("-fullscreen", self.fullscreen)
        self.pages["workout"].full_btn.configure(text="Цонх (F)" if self.fullscreen else "Бүтэн дэлгэц (F)")

    def start_workout(self, source=None):
        """source өгвөл (жишээ нь камер нээгдээгүй үед «демо») тохиргоог өөрчлөхгүйгээр тэр эх үүсвэрээр эхэлнэ."""
        s = self.settings
        if self.pages["home"].scanning:  # «Камер хайх» камеруудыг нээж байх үед зэрэг нээхгүй
            self.pages["home"].show_notice("Камер хайж дуустал түр хүлээнэ үү.")
            return
        if source is None and s["source"] == "video" and not s["video_path"]:
            self.show("home")
            self.pages["home"].show_notice("Эхлээд видео файлаа сонгоно уу.")
            return
        save_settings(s)
        if self.current == "workout":
            self.pages["workout"].stop()
        self.show("workout")
        self.pages["workout"].start(dict(s, source=source) if source else s)

    def stop_workout(self):
        self.show("home")

    def show_summary(self, ended=False):
        if self.current != "workout":
            return
        engine, csv_path, last = self.pages["workout"].stop()
        workouts = [w for w in engine.workouts.values() if w.reps] if engine else []
        if ended and not workouts:
            self.show("home")
            self.pages["home"].show_notice("Бичлэг дууслаа. Тоологдсон давталт алга.")
            return
        self.pages["summary"].show(workouts, last.t if last else 0.0, csv_path)
        self.show("summary")

    # ---- товчлуур
    def _on_key(self, e):
        k = e.keysym.lower()
        if self.onboarding.visible:
            self.onboarding.on_key(k)
            return "break"
        page = self.pages["workout"]
        if self.current == "workout" and page.confirm.visible:
            if k == "escape":
                page.confirm_continue()
            elif k == "return":
                page.confirm_summary()
            return "break"
        # F11 (Windows, Linux) эсвэл дасгалын үед F: macOS-д F11 ихэвчлэн системд эзлэгдсэн байдаг
        if k == "f11" or (k == "f" and self.current == "workout"):
            self.toggle_fullscreen()
            return "break"
        if k == "escape" and self.fullscreen:  # эхлээд бүтэн дэлгэцээс гарна
            self.toggle_fullscreen(False)
            return "break"
        if self.current == "workout":
            actions = {"space": page.skip, "p": page.toggle_pause, "s": page.toggle_sound, "e": page.finish,
                       "m": page.toggle_mirror, "escape": page.request_leave,
                       "1": lambda: page.set_exercise("squat"), "2": lambda: page.set_exercise("pushup")}
            if k in actions:
                actions[k]()
                return "break"
        elif self.current == "home" and k == "return":
            self.start_workout()

    def _on_appearance(self, label):
        mode = next(k for k, v in APPEARANCE.items() if v == label)
        self.settings["appearance"] = mode
        ctk.set_appearance_mode(mode)
        save_settings(self.settings)
        self.divider.configure(bg=pick(BORDER))
        # tk.Canvas дээрх графикууд өнгөө өөрөө солихгүй тул дахин зурна
        self.after(50, lambda: [p.refresh_theme() for p in self.pages.values() if hasattr(p, "refresh_theme")])

    def _on_scale(self, label):
        scale = int(label.rstrip("%")) / 100
        self.settings["ui_scale"] = scale
        ctk.set_widget_scaling(scale)
        save_settings(self.settings)

    def on_close(self):
        if self.current == "workout":
            self.pages["workout"].stop()
        save_settings(self.settings)
        self.destroy()


def run():
    app = App()
    app.mainloop()
