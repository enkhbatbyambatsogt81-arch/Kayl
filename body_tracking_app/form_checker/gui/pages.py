"""Цонхны хуудсууд: Нүүр (дасгал сонгох), Дасгал (камер), Дүн, Түүх, Заавар."""

from __future__ import annotations

import os
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import filedialog

import customtkinter as ctk
from PIL import Image, ImageTk

from ..camera import camera_help, find_cameras
from ..config import PushupConfig, SquatConfig
from ..engine import WorkoutEngine
from ..history import compare_with_history, load_history
from ..messages import TIPS, WARNING_TITLES, t
from .theme import (ACCENT, ACCENT_SOFT, BAD, BORDER, CARD, GOOD, INFO, INSET, LEVEL_COLORS, MUTED, PHASES, PRIMARY,
                    SECONDARY, SEG, TEXT, TEXT2, WARN, font)
from .overlays import ConfirmCard, SetupChecklist
from .widgets import AngleTrace, Card, HistoryChart, RepChart, RepDots, StatTile, stick_figure
from .worker import EngineWorker

EX_TITLES = {"squat": "Суулт (Squat)", "pushup": "Гар дээр суниалт (Push-up)"}
EX_INFO = {
    "squat": ("Шалгах зүйлс: суултын гүн, их биеийн хазайлт, өвдөг дотогш орох, өсгий өргөгдөх",
              "Камер: хажуугаас (эсвэл урдаас), 2–3 м зайд, бүтэн бие харагдахаар"),
    "pushup": ("Шалгах зүйлс: тохойн гүн, бэлхүүс унжих, бөгс өргөх, гараа бүрэн тэнийлгэх",
               "Камер: зөвхөн хажуугаас, шалнаас 30–60 см өндөрт"),
}
JOINT = {"squat": "өвдөг", "pushup": "тохой"}
DEPTH = {"squat": SquatConfig().depth_angle, "pushup": PushupConfig().depth_angle}
PHASE_HINTS = {
    "setup": "Камерын өмнө бүтэн биеэ харуулж, эхлэх байрлалдаа 1 секунд хөдөлгөөнгүй зогс. Шууд эхлэх бол Space.",
    "countdown": "Тоолол дуусмагц дасгалаа эхэл.",
    "rest": "Ус ууж, амьсгалаа тайвшруул. Space дарвал амралтыг алгасна.",
    "done": "Дүнгийн хуудас нээгдэж байна...",
}
SOURCES = {"camera": "Вэбкамер", "video": "Видео файл", "demo": "Демо (камергүй)"}
KEY_HINT = "Enter = эхлэх.  Дасгалын үед: Space алгасах · P түр зогсоох · E дуусгах · F бүтэн дэлгэц · Esc буцах"
CAMERA_NOTE = "0 нь ихэвчлэн компьютерийн өөрийн камер. Олон камертай бол «Камер хайх» дарж ажиллаж буйг нь олно."
DEMO_NOTE = ("Камергүйгээр зохиомол хүн зөв ба алдаатай давталт хийнэ. Апп яг камертай үеийнх шиг тоолж, "
             "үнэлнэ. Хичээл дээр үзүүлэх эсвэл камер ажиллахгүй үед туршихад тохиромжтой.")
HISTORY_FILTERS = {"Бүгд": None, "Squat": "squat", "Push-up": "pushup"}
MODELS = {"lite": "Хурдан (lite)", "full": "Нарийн (full)"}
# Бэлэн зорилго: (нэг сетийн давталт, сет, амралт секунд). Анх удаа ашиглагч гурван гулсуурыг тааруулахгүйгээр
# нэг товчоор сонгоно. Гулсуураар өөр утга сонговол «Өөрөө» гэж харагдана.
PRESETS = {"Эхлэгч": (8, 2, 60), "Дунд": (10, 3, 60), "Ахисан": (15, 4, 90)}
CUSTOM = "Өөрөө"
# Шалгуурын түвшин (2.0): босго утгууд config.LEVEL_OVERRIDES-д
LEVEL_LABELS = {"easy": "Зөөлөн", "normal": "Энгийн", "strict": "Хатуу"}
LEVEL_HINTS = {
    "easy": "Зөөлөн: өвдөг 110°, тохой 100° хүртэл бууход хангалттай. Эхлэгч, өвдөлттэй үед.",
    "normal": "Энгийн: өвдөг 100°, тохой 90° хүртэл бууна (анхдагч).",
    "strict": "Хатуу: өвдөг 90°, тохой 80°, их бие илүү босоо, хэмнэл удаан байх ёстой.",
}


def issue_title(key):
    return WARNING_TITLES.get(key) or t(key, "mn")


def score_color(score):
    """Давталтын оноог өнгөөр: 80+ ногоон, 60-79 шар, түүнээс бага улаан."""
    return GOOD if score >= 80 else WARN if score >= 60 else BAD


def open_path(path):
    """Файл/хавтсыг үйлдлийн системийн програмаар нээнэ."""
    try:
        if sys.platform.startswith("win"):
            os.startfile(path)  # noqa: S606
        elif sys.platform == "darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])
    except OSError:
        pass


def header(master, title, subtitle=None):
    f = ctk.CTkFrame(master, fg_color="transparent")
    ctk.CTkLabel(f, text=title, font=font(28, "bold"), text_color=TEXT, anchor="w").pack(anchor="w")
    if subtitle:
        ctk.CTkLabel(f, text=subtitle, font=font(14), text_color=TEXT2, anchor="w", justify="left").pack(anchor="w")
    return f


def section_title(master, text):
    return ctk.CTkLabel(master, text=text, font=font(17, "bold"), text_color=TEXT, anchor="w")


def step_title(master, number, text):
    """Нүүр хуудасны алхмын гарчиг: дугуйлсан дугаар + нэр (1 Дасгал, 2 Зорилго, 3 Эх үүсвэр)."""
    f = ctk.CTkFrame(master, fg_color="transparent")
    ctk.CTkLabel(f, text=str(number), font=font(13, "bold"), text_color="#ffffff", fg_color=ACCENT,
                 corner_radius=12, width=24, height=24).pack(side="left")
    ctk.CTkLabel(f, text=text, font=font(17, "bold"), text_color=TEXT, anchor="w").pack(side="left", padx=(10, 0))
    return f


def auto_wrap(label, container, pad):
    """Урт тайлбарыг савныхаа өргөнд тааруулж мөр ороох (цонхны өргөн, «Хэмжээ» өөрчлөгдөхөд)."""
    def on_resize(e):
        scale = ctk.ScalingTracker.get_widget_scaling(label)
        width = max(120, int(e.width / scale) - pad)
        if label.cget("wraplength") != width:
            label.configure(wraplength=width)
    container.bind("<Configure>", on_resize, add="+")


# =============================================================================
# Нүүр хуудас
# =============================================================================
class ExerciseCard(Card):
    def __init__(self, master, name, on_select):
        super().__init__(master)
        self.name = name
        self.grid_columnconfigure(1, weight=1)
        icon = ctk.CTkImage(light_image=stick_figure(name, (150, 96), color=(42, 120, 214)),
                            dark_image=stick_figure(name, (150, 96), color=(120, 170, 235)), size=(150, 96))
        self.pic = ctk.CTkLabel(self, text="", image=icon)
        self.pic.grid(row=0, column=0, rowspan=3, padx=(16, 8), pady=16)
        title = ctk.CTkLabel(self, text=EX_TITLES[name], font=font(19, "bold"), text_color=TEXT, anchor="w",
                             justify="left", wraplength=230)
        title.grid(row=0, column=1, sticky="sw", padx=(8, 96), pady=(18, 2))
        checks, camera = EX_INFO[name]
        checks_lbl = ctk.CTkLabel(self, text=checks, font=font(13), text_color=TEXT2, anchor="w", justify="left",
                                  wraplength=270)
        checks_lbl.grid(row=1, column=1, sticky="w", padx=(8, 16))
        camera_lbl = ctk.CTkLabel(self, text=camera, font=font(13), text_color=MUTED, anchor="w", justify="left",
                                  wraplength=270)
        camera_lbl.grid(row=2, column=1, sticky="nw", padx=(8, 16), pady=(4, 16))
        self._texts = ((title, 96), (checks_lbl, 16), (camera_lbl, 16))   # (бичиг, баруун талын зай)
        self._narrow = None
        self.bind("<Configure>", self._on_resize, add="+")
        self.check = ctk.CTkLabel(self, text="", font=font(13, "bold"), text_color="#ffffff", fg_color=ACCENT,
                                  corner_radius=10, width=86, height=24)
        self._bind_all(self, lambda e: on_select(name))

    def _on_resize(self, e):
        """Нарийн цонхонд (жишээ нь 1366×768, 125%) зургийг нууж, бичгийг картын өргөнд ороно."""
        width = e.width / ctk.ScalingTracker.get_widget_scaling(self)
        narrow = width < 430
        if narrow != self._narrow:
            self._narrow = narrow
            self.pic.grid_remove() if narrow else self.pic.grid()
            for lbl, right in self._texts:
                lbl.grid(padx=(18 if narrow else 8, right))
        left = 18 if narrow else 16 + 150 + 8 + 8   # зураг харагдвал түүний өргөн ба зай
        for lbl, right in self._texts:
            wrap = max(100, int(width - left - right - 8))
            if lbl.cget("wraplength") != wrap:
                lbl.configure(wraplength=wrap)

    def _bind_all(self, w, fn):
        w.bind("<Button-1>", fn)
        try:
            w.configure(cursor="hand2")
        except (ValueError, tk.TclError):
            pass
        for child in w.winfo_children():
            self._bind_all(child, fn)

    def set_selected(self, selected):
        self.configure(border_color=ACCENT if selected else BORDER, border_width=2 if selected else 1,
                       fg_color=ACCENT_SOFT if selected else CARD)
        if selected:
            self.check.configure(text="Сонгосон", fg_color=ACCENT)
            self.check.place(relx=1.0, x=-14, y=14, anchor="ne")
        else:
            self.check.place_forget()


class HomePage(ctk.CTkFrame):
    """Дээд хэсэг нь гүйлгэгдэнэ; доод «Эхлэх» самбар цонх намхан (эсвэл томруулсан) үед ч үргэлж харагдана."""

    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.scanning = False      # «Камер хайх» ажиллаж байгаа эсэх (энэ үед дасгал эхлүүлэхгүй)
        self._src_kind = None
        s = app.settings
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        body = ctk.CTkScrollableFrame(self, fg_color="transparent")
        body.grid(row=0, column=0, sticky="nsew")
        body.grid_columnconfigure((0, 1), weight=1, uniform="col")
        header(body, "Шинэ дасгал", "Дасгал, зорилго, эх үүсвэрээ сонгоод «Эхлэх» дарна.").grid(
            row=0, column=0, columnspan=2, sticky="w", padx=8, pady=(8, 10))

        # --- 1. Дасгал
        step_title(body, 1, "Дасгал").grid(row=1, column=0, columnspan=2, sticky="w", padx=10, pady=(4, 0))
        self.cards = {}
        for col, name in enumerate(("squat", "pushup")):
            card = ExerciseCard(body, name, self.select)
            card.grid(row=2, column=col, sticky="nsew", padx=8, pady=8)
            self.cards[name] = card

        # --- 2. Зорилго
        goal = Card(body)
        goal.grid(row=3, column=0, sticky="nsew", padx=8, pady=8)
        goal.grid_columnconfigure(0, weight=1)
        step_title(goal, 2, "Зорилго").grid(row=0, column=0, sticky="w", padx=18, pady=(16, 8))
        self.preset = ctk.CTkSegmentedButton(goal, values=[*PRESETS, CUSTOM], command=self._on_preset,
                                             font=font(14), **SEG)
        self.preset.grid(row=1, column=0, sticky="ew", padx=18, pady=(2, 6))
        self.free = ctk.CTkSwitch(goal, text="Чөлөөт горим (зорилго, амралтгүй)", font=font(14),
                                  command=self._on_free)
        self.free.grid(row=2, column=0, sticky="w", padx=18, pady=6)
        self.goal_note = ctk.CTkLabel(goal, text="", font=font(12), text_color=MUTED, anchor="w", justify="left")
        self.reps_lbl = ctk.CTkLabel(goal, text="", font=font(14), text_color=TEXT2, anchor="w")
        self.reps_lbl.grid(row=4, column=0, sticky="w", padx=18, pady=(8, 0))
        self.reps = ctk.CTkSlider(goal, from_=3, to=30, number_of_steps=27, command=self._on_reps)
        self.reps.grid(row=5, column=0, sticky="ew", padx=18, pady=4)
        self.sets_lbl = ctk.CTkLabel(goal, text="Сетийн тоо", font=font(14), text_color=TEXT2, anchor="w")
        self.sets_lbl.grid(row=6, column=0, sticky="w", padx=18, pady=(8, 0))
        self.sets = ctk.CTkSegmentedButton(goal, values=["1", "2", "3", "4", "5"], command=self._on_sets,
                                           font=font(14), **SEG)
        self.sets.grid(row=7, column=0, sticky="ew", padx=18, pady=4)
        self.rest_lbl = ctk.CTkLabel(goal, text="", font=font(14), text_color=TEXT2, anchor="w")
        self.rest_lbl.grid(row=8, column=0, sticky="w", padx=18, pady=(8, 0))
        self.rest = ctk.CTkSlider(goal, from_=15, to=180, number_of_steps=11, command=self._on_rest)
        self.rest.grid(row=9, column=0, sticky="ew", padx=18, pady=(4, 18))

        # --- 3. Эх үүсвэр ба тохиргоо
        opt = Card(body)
        opt.grid(row=3, column=1, sticky="nsew", padx=8, pady=8)
        opt.grid_columnconfigure(1, weight=1)
        step_title(opt, 3, "Эх үүсвэр ба тохиргоо").grid(row=0, column=0, columnspan=2, sticky="w", padx=18,
                                                         pady=(16, 8))
        self.source = ctk.CTkSegmentedButton(opt, values=list(SOURCES.values()), command=self._on_source,
                                             font=font(14), **SEG)
        self.source.grid(row=1, column=0, columnspan=2, sticky="ew", padx=18, pady=(2, 6))
        # Сонгосон эх үүсвэрт хамаатай тохиргоо л харагдана (_show_source)
        self.src_box = ctk.CTkFrame(opt, fg_color=INSET, corner_radius=10)
        self.src_box.grid(row=2, column=0, columnspan=2, sticky="ew", padx=18, pady=(4, 8))
        self.src_box.grid_columnconfigure(2, weight=1)
        inner = dict(SECONDARY, hover_color=BORDER)
        self.cam_lbl = ctk.CTkLabel(self.src_box, text="Камер", font=font(14), text_color=TEXT2)
        self.cam = ctk.CTkOptionMenu(self.src_box, values=["0", "1", "2", "3"], width=80, command=self._on_cam)
        self.scan_btn = ctk.CTkButton(self.src_box, text="Камер хайх", width=120, command=self.scan_cameras,
                                      **inner)
        self.cam_status = ctk.CTkLabel(self.src_box, text=CAMERA_NOTE, font=font(12), text_color=MUTED,
                                       anchor="w", justify="left")
        self.mirror = ctk.CTkSwitch(self.src_box, text="Толин дүрс (толинд харж байгаа мэт)", font=font(14),
                                    command=self._on_switches)
        self.video_btn = ctk.CTkButton(self.src_box, text="Файл сонгох...", width=130, command=self._pick_video,
                                       **inner)
        self.video_lbl = ctk.CTkLabel(self.src_box, text="", font=font(13), text_color=TEXT2, anchor="w")
        self.demo_lbl = ctk.CTkLabel(self.src_box, text=DEMO_NOTE, font=font(13), text_color=TEXT2, anchor="w",
                                     justify="left")
        for lbl in (self.cam_status, self.demo_lbl):
            auto_wrap(lbl, self.src_box, 30)
        ctk.CTkLabel(opt, text="Загвар", font=font(14), text_color=TEXT2).grid(row=3, column=0, sticky="w",
                                                                              padx=18, pady=6)
        self.model = ctk.CTkSegmentedButton(opt, values=list(MODELS.values()), command=self._on_model,
                                            font=font(13), **SEG)
        self.model.grid(row=3, column=1, sticky="ew", padx=(0, 18), pady=6)
        ctk.CTkLabel(opt, text="Шалгуур", font=font(14), text_color=TEXT2).grid(row=4, column=0, sticky="w",
                                                                               padx=18, pady=6)
        self.level = ctk.CTkSegmentedButton(opt, values=list(LEVEL_LABELS.values()), command=self._on_level,
                                            font=font(13), **SEG)
        self.level.grid(row=4, column=1, sticky="ew", padx=(0, 18), pady=6)
        self.level_lbl = ctk.CTkLabel(opt, text="", font=font(12), text_color=MUTED, anchor="w", justify="left")
        self.level_lbl.grid(row=5, column=0, columnspan=2, sticky="w", padx=18, pady=(0, 4))
        auto_wrap(self.level_lbl, opt, 40)
        self.auto = ctk.CTkSwitch(opt, text="Дасгалыг автоматаар таних", font=font(14), command=self._on_switches)
        self.auto.grid(row=6, column=0, columnspan=2, sticky="w", padx=18, pady=6)
        self.sound = ctk.CTkSwitch(opt, text="Дуут дохио", font=font(14), command=self._on_switches)
        self.sound.grid(row=7, column=0, columnspan=2, sticky="w", padx=18, pady=(6, 18))

        # --- Доод самбар: юу сонгосныг товч харуулаад эхлүүлнэ
        bar = Card(self)
        bar.grid(row=1, column=0, sticky="ew", padx=8, pady=(10, 0))
        bar.grid_columnconfigure(0, weight=1)
        self.summary_lbl = ctk.CTkLabel(bar, text="", font=font(15, "bold"), text_color=TEXT, anchor="w",
                                        justify="left")
        self.summary_lbl.grid(row=0, column=0, sticky="sw", padx=18, pady=(14, 0))
        self.notice = ctk.CTkLabel(bar, text="", font=font(13), text_color=TEXT2, anchor="w", justify="left")
        self.notice.grid(row=1, column=0, sticky="nw", padx=18, pady=(2, 14))
        for lbl in (self.summary_lbl, self.notice):
            auto_wrap(lbl, bar, 300)
        self.start_btn = ctk.CTkButton(bar, text="Эхлэх  ▶", font=font(20, "bold"), height=52, width=230,
                                       corner_radius=12, command=app.start_workout, **PRIMARY)
        self.start_btn.grid(row=0, column=1, rowspan=2, padx=(12, 14), pady=12)

        self._load(s)

    # ---- тохиргоог харуулах / хадгалах
    def _load(self, s):
        self.select(s["exercise"])
        self.free.select() if s["free_mode"] else self.free.deselect()
        self.reps.set(s["reps"])
        self.sets.set(str(s["sets"]))
        self.rest.set(s["rest"])
        self.source.set(SOURCES[s["source"]])
        self.cam.set(str(s["camera_index"]))
        self.model.set(MODELS.get(s["model"], MODELS["lite"]))
        self.sound.select() if s["sound"] else self.sound.deselect()
        self.mirror.select() if s["mirror"] else self.mirror.deselect()
        self.auto.select() if s["auto_detect"] else self.auto.deselect()
        self.level.set(LEVEL_LABELS[s["level"]])
        self._refresh_labels()

    def _refresh_labels(self):
        s = self.app.settings
        self.reps_lbl.configure(text=f"Нэг сетэд: {s['reps']} давталт")
        self.rest_lbl.configure(text=f"Сет хоорондын амралт: {s['rest']} секунд")
        video = s["source"] == "video"  # бичлэг дээр зорилго, амралтгүйгээр бүх давталтыг тоолно
        off = s["free_mode"] or video
        for w in (self.reps, self.sets, self.rest, self.preset):
            w.configure(state="disabled" if off else "normal")
        for lbl in (self.reps_lbl, self.sets_lbl, self.rest_lbl):
            lbl.configure(text_color=MUTED if off else TEXT2)
        current = (s["reps"], s["sets"], s["rest"])
        self.preset.set(next((k for k, v in PRESETS.items() if v == current), CUSTOM))
        self.free.configure(state="disabled" if video else "normal")
        if off:  # идэвхгүй болсон шалтгааныг хэлнэ
            self.goal_note.configure(text="Видео файл дээр бүх давталтыг зорилго, амралтгүйгээр тоолно." if video
                                     else "Чөлөөт горимд зорилго, сет, амралт хэрэглэгдэхгүй.")
            self.goal_note.grid(row=3, column=0, sticky="w", padx=18, pady=(0, 2))
        else:
            self.goal_note.grid_remove()
        self._show_source(s["source"])
        self.video_lbl.configure(text=os.path.basename(s["video_path"]) if s["video_path"] else "Файл сонгоогүй")
        self.level_lbl.configure(text=LEVEL_HINTS[s["level"]])
        self._refresh_summary()
        self.notice.configure(text=KEY_HINT, text_color=TEXT2)

    def _show_source(self, kind):
        if kind == self._src_kind:
            return
        self._src_kind = kind
        for w in self.src_box.winfo_children():
            w.grid_remove()
        if kind == "camera":
            self.cam_lbl.grid(row=0, column=0, sticky="w", padx=(14, 8), pady=(12, 4))
            self.cam.grid(row=0, column=1, sticky="w", pady=(12, 4))
            self.scan_btn.grid(row=0, column=2, sticky="e", padx=14, pady=(12, 4))
            self.cam_status.grid(row=1, column=0, columnspan=3, sticky="ew", padx=14, pady=(2, 2))
            self.mirror.grid(row=2, column=0, columnspan=3, sticky="w", padx=14, pady=(6, 12))
        elif kind == "video":
            self.video_btn.grid(row=0, column=0, sticky="w", padx=14, pady=12)
            self.video_lbl.grid(row=0, column=1, columnspan=2, sticky="ew", padx=(10, 14), pady=12)
        else:
            self.demo_lbl.grid(row=0, column=0, columnspan=3, sticky="ew", padx=14, pady=12)

    def _refresh_summary(self):
        s = self.app.settings
        if s["source"] == "video":
            goal = "бичлэг дээрх бүх давталт"
        elif s["free_mode"]:
            goal = "чөлөөт горим"
        else:
            goal = f"{s['sets']} сет × {s['reps']} давталт, амралт {s['rest']} с"
        src = {"camera": f"вэбкамер {s['camera_index']}",
               "video": os.path.basename(s["video_path"]) or "видео файл сонгоогүй",
               "demo": "демо (камергүй)"}[s["source"]]
        self.summary_lbl.configure(text=f"{EX_TITLES[s['exercise']]}  ·  {goal}  ·  {src}")

    def select(self, name):
        self.app.settings["exercise"] = name
        for n, card in self.cards.items():
            card.set_selected(n == name)
        self._refresh_summary()

    def _on_preset(self, label):
        if label not in PRESETS:
            return  # «Өөрөө»: одоогийн утгуудыг хэвээр үлдээж, гулсуураар өөрчилнө
        s = self.app.settings
        s["reps"], s["sets"], s["rest"] = PRESETS[label]
        self.reps.set(s["reps"])
        self.sets.set(str(s["sets"]))
        self.rest.set(s["rest"])
        self._refresh_labels()

    def _on_free(self):
        self.app.settings["free_mode"] = bool(self.free.get())
        self._refresh_labels()

    def _on_reps(self, v):
        self.app.settings["reps"] = int(round(v))
        self._refresh_labels()

    def _on_sets(self, v):
        self.app.settings["sets"] = int(v)
        self._refresh_labels()

    def _on_rest(self, v):
        self.app.settings["rest"] = int(round(v / 15) * 15)
        self._refresh_labels()

    def _on_source(self, label):
        self.app.settings["source"] = next(k for k, v in SOURCES.items() if v == label)
        self._refresh_labels()
        if self.app.settings["source"] == "video" and not self.app.settings["video_path"]:
            self._pick_video()

    def _on_cam(self, v):
        self.app.settings["camera_index"] = int(v)
        self._refresh_summary()

    def _on_model(self, label):
        self.app.settings["model"] = next(k for k, v in MODELS.items() if v == label)

    def _on_switches(self):
        self.app.settings["sound"] = bool(self.sound.get())
        self.app.settings["mirror"] = bool(self.mirror.get())
        self.app.settings["auto_detect"] = bool(self.auto.get())

    def _on_level(self, label):
        self.app.settings["level"] = next(k for k, v in LEVEL_LABELS.items() if v == label)
        self._refresh_labels()

    def _pick_video(self):
        path = filedialog.askopenfilename(title="Видео файл сонгох",
                                          filetypes=[("Видео", "*.mp4 *.avi *.mov *.mkv *.webm"), ("Бүх файл", "*.*")])
        if path:
            self.app.settings["video_path"] = path
        self._refresh_labels()

    # ---- камер хайх (тусдаа урсгалд: цонх гацахгүй)
    def scan_cameras(self):
        if self.scanning:
            return
        self.scanning = True
        self.scan_btn.configure(state="disabled", text="Хайж байна...")
        self.start_btn.configure(state="disabled")
        self.cam_status.configure(text="Камеруудыг шалгаж байна. Хэдэн секунд болно...", text_color=TEXT2)
        result = {}

        def work():
            try:
                result["found"] = find_cameras()
            except Exception as e:  # noqa: BLE001 - OpenCV-ийн алдааг хэрэглэгчид харуулна
                result["error"] = str(e)

        thread = threading.Thread(target=work, daemon=True)
        thread.start()
        self.after(100, self._scan_done, thread, result)

    def _scan_done(self, thread, result):
        if thread.is_alive():
            self.after(100, self._scan_done, thread, result)
            return
        self.scanning = False
        self.scan_btn.configure(state="normal", text="Камер хайх")
        self.start_btn.configure(state="normal")
        self.notice.configure(text=KEY_HINT, text_color=TEXT2)   # «хүлээнэ үү» сануулгыг арилгана
        found = result.get("found") or []
        if not found:
            error = f" ({result['error']})" if result.get("error") else ""
            self.cam_status.configure(text=f"Камер олдсонгүй{error}. {camera_help()}", text_color=WARN)
            return
        values = [str(i) for i in found]
        self.cam.configure(values=values)
        if self.cam.get() not in values:
            self.cam.set(values[0])
            self._on_cam(values[0])
        names = ", ".join(values)
        self.cam_status.configure(text=f"Ажиллаж буй камер: {names}. Одоо {self.cam.get()}-р камерыг сонгосон.",
                                  text_color=GOOD)

    def show_notice(self, text, color=WARN):
        self.notice.configure(text=text, text_color=color)


# =============================================================================
# Дасгалын хуудас
# =============================================================================
class WorkoutPage(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.worker = None
        self.engine = None
        self._seq = 0
        self._photo = None
        self._cache = {}
        self._done_at = None
        self._last_ef = None
        self._trace_ex, self._trace_reps = None, 0
        self._setup_icons = {}
        self._pending_ex = None
        self._flash_job = None
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # --- Видео ба хөдөлгөөний график
        left = ctk.CTkFrame(self, fg_color="transparent")
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        left.grid_columnconfigure(0, weight=1)
        left.grid_rowconfigure(0, weight=1)
        self.video_box = ctk.CTkFrame(left, fg_color="#000000", corner_radius=14)
        self.video_box.grid(row=0, column=0, sticky="nsew")
        trace_card = Card(left)
        trace_card.grid(row=1, column=0, sticky="ew", pady=(10, 0))
        trace_card.grid_columnconfigure(0, weight=1)
        self.trace_title = ctk.CTkLabel(trace_card, text="", font=font(14, "bold"), text_color=TEXT, anchor="w")
        self.trace_title.grid(row=0, column=0, sticky="w", padx=16, pady=(10, 0))
        self.trace = AngleTrace(trace_card)
        self.trace.grid(row=1, column=0, sticky="ew", padx=8, pady=(0, 8))
        self.video = tk.Label(self.video_box, bg="#000000", bd=0)
        self.video.place(relx=0.5, rely=0.5, anchor="center")
        self.overlay = ctk.CTkLabel(self.video_box, text="", font=font(22, "bold"), text_color="#ffffff",
                                    fg_color="#202020", corner_radius=12, wraplength=520)
        self.checklist = SetupChecklist(self.video_box)
        # Камер нээгдэхгүй үед мухардалд орохгүйн тулд дараагийн алхмыг санал болгоно
        self.err_actions = ctk.CTkFrame(self.video_box, fg_color="transparent")
        ctk.CTkButton(self.err_actions, text="Демо горимоор туршиж үзэх", height=40, font=font(15), **PRIMARY,
                      command=lambda: self.app.start_workout(source="demo")).pack(side="left", padx=5)
        ctk.CTkButton(self.err_actions, text="Нүүр хуудас", height=40, font=font(15), fg_color="#2c2c2c",
                      hover_color="#383838", text_color="#f2f2f0",
                      command=self.app.stop_workout).pack(side="left", padx=5)
        self.video_box.bind("<Configure>", self._on_resize)

        # --- Хажуугийн самбар
        side = ctk.CTkFrame(self, fg_color="transparent", width=360)
        side.grid(row=0, column=1, sticky="ns")
        side.grid_columnconfigure((0, 1), weight=1)
        self.ex_switch = ctk.CTkSegmentedButton(side, values=["Squat", "Push-up"], command=self._on_exercise,
                                                font=font(14), **SEG)
        self.ex_switch.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10))

        self.rep_card = rep_card = Card(side)
        rep_card.grid(row=1, column=0, columnspan=2, sticky="ew")
        rep_card.grid_columnconfigure(0, weight=1)
        top = ctk.CTkFrame(rep_card, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", padx=18, pady=(14, 0))
        self.ex_lbl = ctk.CTkLabel(top, text="", font=font(15, "bold"), text_color=TEXT, anchor="w")
        self.ex_lbl.pack(side="left")
        self.phase = ctk.CTkLabel(top, text="", font=font(12, "bold"), corner_radius=8, height=24, width=90)
        self.phase.pack(side="right")
        num = ctk.CTkFrame(rep_card, fg_color="transparent")
        num.grid(row=1, column=0, sticky="w", padx=18)
        self.rep_num = ctk.CTkLabel(num, text="0", font=font(84, "bold"), text_color=TEXT, height=96)
        self.rep_num.pack(side="left")
        self.rep_of = ctk.CTkLabel(num, text="/ 10", font=font(32), text_color=TEXT2)
        self.rep_of.pack(side="left", anchor="s", pady=(0, 16), padx=(8, 0))
        meta = ctk.CTkFrame(rep_card, fg_color="transparent")
        meta.grid(row=2, column=0, sticky="ew", padx=18)
        self.set_lbl = ctk.CTkLabel(meta, text="", font=font(14), text_color=TEXT2, anchor="w")
        self.set_lbl.pack(side="left")
        self.time_lbl = ctk.CTkLabel(meta, text="", font=font(14), text_color=TEXT2, anchor="e")
        self.time_lbl.pack(side="right")
        self.set_bar = ctk.CTkProgressBar(rep_card, height=10, progress_color=ACCENT)
        self.set_bar.grid(row=3, column=0, sticky="ew", padx=18, pady=(6, 8))
        self.dots = RepDots(rep_card)
        self.dots.grid(row=4, column=0, sticky="ew", padx=18)
        counts = ctk.CTkFrame(rep_card, fg_color="transparent")
        counts.grid(row=5, column=0, sticky="ew", padx=18, pady=(4, 14))
        self.good_lbl = ctk.CTkLabel(counts, text="", font=font(14), text_color=TEXT2)
        self.good_lbl.pack(side="left")
        self.bad_lbl = ctk.CTkLabel(counts, text="", font=font(14), text_color=TEXT2)
        self.bad_lbl.pack(side="left", padx=(18, 0))
        self.score_lbl = ctk.CTkLabel(counts, text="", font=font(14, "bold"), text_color=TEXT2)
        self.score_lbl.pack(side="right")

        depth = Card(side)
        depth.grid(row=2, column=0, columnspan=2, sticky="ew", pady=10)
        depth.grid_columnconfigure(0, weight=1)
        self.depth_lbl = ctk.CTkLabel(depth, text="Гүн", font=font(14), text_color=TEXT2, anchor="w")
        self.depth_lbl.grid(row=0, column=0, sticky="ew", padx=18, pady=(12, 2))
        self.depth_bar = ctk.CTkProgressBar(depth, height=16, progress_color=WARN)
        self.depth_bar.grid(row=1, column=0, sticky="ew", padx=18, pady=(2, 14))

        tip = Card(side)
        tip.grid(row=3, column=0, columnspan=2, sticky="ew")
        tip.grid_columnconfigure(1, weight=1)
        self.tip_bar = ctk.CTkFrame(tip, width=6, height=10, corner_radius=3, fg_color=INFO)
        self.tip_bar.grid(row=0, column=0, rowspan=2, sticky="ns", padx=(12, 0), pady=12)
        self.tip_lbl = ctk.CTkLabel(tip, text="", font=font(17, "bold"), text_color=TEXT, anchor="w",
                                    justify="left", wraplength=300)
        self.tip_lbl.grid(row=0, column=1, sticky="ew", padx=12, pady=(12, 0))
        self.tip_detail = ctk.CTkLabel(tip, text="", font=font(13), text_color=TEXT2, anchor="w",
                                       justify="left", wraplength=300)
        self.tip_detail.grid(row=1, column=1, sticky="ew", padx=12, pady=(2, 12))
        self.tip_img = ctk.CTkLabel(tip, text="")  # бэлтгэлийн үед эхлэх байрлалын зураг

        b = dict(height=38, font=font(14), corner_radius=10)
        sec = SECONDARY
        self.pause_btn = ctk.CTkButton(side, text="Түр зогсоох (P)", command=self.toggle_pause, **b, **sec)
        self.pause_btn.grid(row=4, column=0, sticky="ew", padx=(0, 5), pady=(12, 5))
        self.skip_btn = ctk.CTkButton(side, text="Алгасах (Space)", command=self.skip, **b, **sec)
        self.skip_btn.grid(row=4, column=1, sticky="ew", padx=(5, 0), pady=(12, 5))
        self.sound_btn = ctk.CTkButton(side, text="", command=self.toggle_sound, **b, **sec)
        self.sound_btn.grid(row=5, column=0, sticky="ew", padx=(0, 5), pady=5)
        self.mirror_btn = ctk.CTkButton(side, text="Толин дүрс (M)", command=self.toggle_mirror, **b, **sec)
        self.mirror_btn.grid(row=5, column=1, sticky="ew", padx=(5, 0), pady=5)
        self.finish_btn = ctk.CTkButton(side, text="Дуусгаж дүн харах (E)", command=self.finish, **PRIMARY, **b)
        self.finish_btn.grid(row=6, column=0, columnspan=2, sticky="ew", pady=5)
        self.back_btn = ctk.CTkButton(side, text="← Нүүр (Esc)", command=self.request_leave, **b, **sec)
        self.back_btn.grid(row=7, column=0, sticky="ew", padx=(0, 5), pady=5)
        self.full_btn = ctk.CTkButton(side, text="Бүтэн дэлгэц (F)", command=self.app.toggle_fullscreen,
                                      **b, **sec)
        self.full_btn.grid(row=7, column=1, sticky="ew", padx=(5, 0), pady=5)
        self.perf_lbl = ctk.CTkLabel(side, text="", font=font(12), text_color=MUTED)
        self.perf_lbl.grid(row=8, column=0, columnspan=2, pady=(6, 0))
        self._compact = None
        self.bind("<Configure>", self._on_page_resize)
        # Давталт хийсний дараа Esc дарахад дүнг харахгүй гарахаас сэргийлнэ
        self.confirm = ConfirmCard(self, "Дасгалаа дуусгах уу?", "", [
            ("Үргэлжлүүлэх (Esc)", self.confirm_continue, "secondary"),
            ("Нүүр хуудас руу", self.confirm_home, "secondary"),
            ("Дүнгээ харах (Enter)", self.confirm_summary, "primary"),
        ])
        self._was_paused = False

    def _on_page_resize(self, e):
        """Намхан дэлгэц (жишээ нь 1280×800, 200% томруулалт) дээр самбарыг багтаахын тулд жижигрүүлнэ."""
        compact = e.height / ctk.ScalingTracker.get_widget_scaling(self) < 780
        if compact == self._compact:
            return
        self._compact = compact
        self.rep_num.configure(font=font(56 if compact else 84, "bold"), height=66 if compact else 96)
        self.rep_of.configure(font=font(24 if compact else 32))
        self.tip_detail.grid_remove() if compact else self.tip_detail.grid()
        self.trace.set_base_height(104 if compact else 140)
        self.perf_lbl.grid_remove() if compact else self.perf_lbl.grid()

    # ---- эхлүүлэх / зогсоох
    def start(self, s):
        kind = s["source"]
        source = {"camera": str(s["camera_index"]), "video": s["video_path"], "demo": "demo"}[kind]
        reps = 0 if s["free_mode"] or kind == "video" else s["reps"]
        cfg = WorkoutEngine.default_config(kind, reps, s["sets"], float(s["rest"]))
        self.engine = WorkoutEngine(exercise=s["exercise"], source=source, model=s["model"], workout_cfg=cfg,
                                    mirror=s["mirror"] if kind == "camera" else False, sound=s["sound"],
                                    hud=False, realtime=kind != "camera", log_dir=self.app.log_dir,
                                    level=s["level"], auto_detect=s["auto_detect"] and kind != "demo")
        self.worker = EngineWorker(self.engine)
        self._seq, self._cache, self._done_at, self._last_ef = 0, {}, None, None
        self._pending_ex = None
        self.ex_switch.set("Squat" if s["exercise"] == "squat" else "Push-up")
        self.pause_btn.configure(text="Түр зогсоох (P)")
        self._update_sound_btn()
        self._reset_panel(s, kind)
        self.video.configure(image="")
        self._photo = None
        self.checklist.hide()
        self.confirm.close()
        self.err_actions.place_forget()
        self._show_overlay("Камер нээж байна..." if kind == "camera" else "Ачаалж байна...")
        self._on_resize()
        self.worker.start()
        self.after(15, self._poll)

    def _reset_panel(self, s, kind):
        """Шинэ дасгал эхлэхэд самбарыг хоосон төлөвт оруулна (эхний кадр ирэхээс өмнө)."""
        reps = 0 if s["free_mode"] or kind == "video" else s["reps"]
        self.ex_lbl.configure(text=EX_TITLES[s["exercise"]])
        self.phase.configure(text="", fg_color="transparent")
        self.rep_num.configure(text="0")
        self.rep_of.configure(text=f"/ {reps}" if reps else "давталт")
        self.set_lbl.configure(text="")
        self.set_bar.set(0)
        self.dots.set([], reps)
        self.good_lbl.configure(text="")
        self.bad_lbl.configure(text="")
        self.depth_lbl.configure(text="Гүн")
        self.depth_bar.set(0)
        self.tip_bar.configure(fg_color=INFO)
        self.tip_lbl.configure(text="")
        self.tip_detail.configure(text="")
        self.skip_btn.configure(state="disabled")
        self.mirror_btn.configure(state="normal" if kind == "camera" else "disabled")
        self.time_lbl.configure(text="")
        self.perf_lbl.configure(text="")
        self._unflash()
        self._reset_trace(s["exercise"])
        self._show_setup_icon(None)

    def stop(self):
        """Ажлыг зогсоогоод (engine, csv_path, сүүлийн кадр) буцаана."""
        self.confirm.close()
        if self.worker is None:
            return None, None, None
        self.worker.stop()
        result = (self.engine, self.worker.csv_path, self._last_ef)
        self.worker = None
        return result

    # ---- гарах үеийн асуулт
    def total_reps(self):
        return sum(len(w.reps) for w in self.engine.workouts.values()) if self.engine else 0

    def request_leave(self):
        """Esc / «Нүүр»: давталт хийсэн бол шууд гаргахгүй, юу хийхийг асууна."""
        if self.confirm.visible:
            return
        done = self._last_ef is not None and self._last_ef.wv.phase == "done"
        if self.worker is None or self.worker.error or done or self.total_reps() == 0:
            self.app.stop_workout()
            return
        self._was_paused = self.engine.paused
        self.engine.set_paused(True)
        n = self.total_reps()
        self.confirm.open(f"Та {n} давталт хийсэн. Үр дүн хадгалагдана. Дүнгээ харах уу, эсвэл үргэлжлүүлэх үү?")

    def confirm_continue(self):
        self.confirm.close()
        if self.engine and not self._was_paused:
            self.engine.set_paused(False)

    def confirm_summary(self):
        self.confirm.close()
        self.app.show_summary()

    def confirm_home(self):
        self.confirm.close()
        self.app.stop_workout()

    # ---- товчлуурууд
    def skip(self):
        if self.engine:
            self.engine.skip()

    def finish(self):
        if self.engine:
            if self.engine.paused:
                self.toggle_pause()
            self.engine.finish()

    def toggle_pause(self):
        if not self.engine:
            return
        paused = not self.engine.paused
        self.engine.set_paused(paused)
        self.pause_btn.configure(text="Үргэлжлүүлэх (P)" if paused else "Түр зогсоох (P)")
        if paused:
            self._show_overlay("Түр зогссон. Үргэлжлүүлэх бол P дарна уу.")
        else:
            self.overlay.place_forget()

    def toggle_sound(self):
        if self.engine:
            self.engine.toggle_sound()
            self.app.settings["sound"] = self.engine.sound.enabled
            self._update_sound_btn()

    def _update_sound_btn(self):
        snd = self.engine.sound if self.engine else None
        if snd is None or not snd.available:
            self.sound_btn.configure(text="Дуу байхгүй", state="disabled")
        else:
            self.sound_btn.configure(text="Дуу: асаалттай (S)" if snd.enabled else "Дуу: унтраалттай (S)",
                                     state="normal")

    def toggle_mirror(self):
        if self.engine and self.engine.kind == "camera":
            self.engine.toggle_mirror()

    def set_exercise(self, name):
        self.ex_switch.set("Squat" if name == "squat" else "Push-up")
        self._on_exercise(self.ex_switch.get())

    def _on_exercise(self, label):
        name = "squat" if label == "Squat" else "pushup"
        self.app.settings["exercise"] = name
        if self.engine:
            self._pending_ex = name  # хөдөлгүүр дараагийн кадрт солино
            self.engine.set_exercise(name)

    def _sync_exercise(self, ex):
        """Хөдөлгүүр дасгалыг автоматаар сольсон бол сонгогчийг дагуулж шинэчилнэ."""
        if self._pending_ex is not None:
            if ex != self._pending_ex:
                return
            self._pending_ex = None
        want = "Squat" if ex == "squat" else "Push-up"
        if self.ex_switch.get() != want:
            self.ex_switch.set(want)
            self.app.settings["exercise"] = ex

    # ---- зурах
    def _show_overlay(self, text):
        self.overlay.configure(text=text)
        self.overlay.place(relx=0.5, rely=0.5, anchor="center")
        self.overlay.lift()

    def _on_resize(self, _e=None):
        if self.worker:
            w, h = self.video_box.winfo_width(), self.video_box.winfo_height()
            if w > 20 and h > 20:
                self.worker.target_size = (w - 8, h - 8)

    def _set(self, key, widget, **kw):
        """Утга өөрчлөгдсөн үед л элементийг шинэчилнэ (Tk-ийн configure харьцангуй удаан)."""
        if self._cache.get(key) != kw:
            self._cache[key] = kw
            widget.configure(**kw)

    def _poll(self):
        w = self.worker
        if w is None:
            return
        if w.error:
            self.checklist.hide()
            self._show_overlay(w.error if self.engine.kind == "camera"
                               else w.error + "\n\n«Нүүр хуудас» товчоор буцна уу.")
            if self.engine.kind == "camera":
                self.err_actions.place(relx=0.5, rely=0.5, y=90, anchor="n")
                self.err_actions.lift()
            return
        data, self._seq = w.get(self._seq)
        if data is not None:
            rgb, ef = data
            self._last_ef = ef
            if not self.engine.paused and self.overlay.winfo_ismapped():
                self.overlay.place_forget()
            self._show_frame(rgb)
            self._update_panel(ef)
            if ef.wv.phase == "done" and self._done_at is None:
                self._done_at = ef.t
                self.after(1200, self.app.show_summary)  # төгсгөлийн дууг сонсгоод дүн рүү
        if w.ended and data is None:
            self.app.show_summary(ended=True)
            return
        self.after(15, self._poll)

    def _reset_trace(self, ex):
        self._trace_ex, self._trace_reps = ex, 0
        self.trace_title.configure(text=f"Хөдөлгөөн: {JOINT[ex]}ний өнцөг, сүүлийн 10 секунд"
                                   if ex == "squat" else "Хөдөлгөөн: тохойн өнцөг, сүүлийн 10 секунд")
        self.trace.reset(DEPTH[ex])

    def _update_trace(self, ef):
        """Графикт кадр нэмнэ. Энэ кадрт шинэ давталт тоологдсон бол түүнийг буцаана."""
        if ef.exercise != self._trace_ex:
            self._reset_trace(ef.exercise)
            self._trace_reps = ef.wv.total_reps
        rep, n = None, ef.wv.total_reps
        if n > self._trace_reps:
            reps = self.engine.workouts[ef.exercise].reps
            rep = reps[n - 1] if len(reps) >= n else None
        self._trace_reps = n
        self.trace.push(ef.t, ef.wv.fb.main_angle, rep, rep_no=n)
        return rep

    def _flash(self, color):
        """Давталт тоологдоход тоолуурын карт 0.7 секунд ногоон/улаан болно: холоос ч, нүдний булангаар ч харагдана."""
        if self._flash_job is not None:
            self.after_cancel(self._flash_job)
        self.rep_card.configure(border_color=color, border_width=3)
        self.rep_num.configure(text_color=color)
        self._flash_job = self.after(700, self._unflash)

    def _unflash(self):
        if self._flash_job is not None:
            self.after_cancel(self._flash_job)
            self._flash_job = None
        self.rep_card.configure(border_color=BORDER, border_width=1)
        self.rep_num.configure(text_color=TEXT)

    def _show_setup_icon(self, ex):
        """Бэлтгэлийн үед зөвлөмжийн карт дээр эхлэх байрлалыг зургаар харуулна."""
        if self._cache.get("setup_icon") == ex:
            return
        self._cache["setup_icon"] = ex
        if ex is None:
            self.tip_img.grid_remove()
            for lbl in (self.tip_lbl, self.tip_detail):
                lbl.configure(wraplength=300)
            return
        if ex not in self._setup_icons:
            size = (64, 92) if ex == "squat" else (120, 60)
            self._setup_icons[ex] = ctk.CTkImage(
                light_image=stick_figure(ex, size, color=(42, 120, 214), start=True),
                dark_image=stick_figure(ex, size, color=(120, 170, 235), start=True), size=size)
        self.tip_img.configure(image=self._setup_icons[ex])
        self.tip_img.grid(row=0, column=2, rowspan=2, padx=(0, 12), pady=10)
        for lbl in (self.tip_lbl, self.tip_detail):
            lbl.configure(wraplength=190)

    def _show_frame(self, rgb):
        img = Image.fromarray(rgb)
        if self._photo is not None and (self._photo.width(), self._photo.height()) == img.size:
            # Хэмжээ өөрчлөгдөөгүй бол хуучин зураг руу хуулна: шинэ PhotoImage үүсгэхээс ~6 дахин хурдан
            self._photo.paste(img)
        else:
            self._photo = ImageTk.PhotoImage(img)
            self.video.configure(image=self._photo)

    def _update_panel(self, ef):
        wv, fb = ef.wv, ef.wv.fb
        ex = ef.exercise
        self._sync_exercise(ex)
        self._set("ex", self.ex_lbl, text=EX_TITLES[ex])
        label, color = PHASES.get(wv.phase, ("", INFO))
        self._set("phase", self.phase, text=label, fg_color=color,
                  text_color="#141414" if color == WARN else "#ffffff")
        free = wv.target <= 0
        n = wv.total_reps if free else len(wv.set_reps)
        self._set("num", self.rep_num, text=str(n))
        self._set("of", self.rep_of, text="давталт" if free else f"/ {wv.target}")
        self._set("set", self.set_lbl, text="Чөлөөт горим" if free else f"Сет {wv.set_index} / {wv.sets_total}")
        mins, secs = divmod(int(ef.t), 60)
        self._set("time", self.time_lbl, text=f"Хугацаа {mins}:{secs:02d}")
        new_rep = self._update_trace(ef)
        if new_rep is not None:
            self._flash(GOOD if new_rep.correct else BAD)
        prog = 0.0 if free else min(1.0, len(wv.set_reps) / max(wv.target, 1))
        if self._cache.get("prog") != prog:
            self._cache["prog"] = prog
            self.set_bar.set(prog)
        self.dots.set(wv.set_reps if not free else self.engine.workout.reps, wv.target)
        reps = self.engine.workout.reps if free else wv.set_reps
        good = sum(r.correct for r in reps)
        self._set("good", self.good_lbl, text=f"●  Зөв: {good}", text_color=GOOD)
        self._set("bad", self.bad_lbl, text=f"●  Алдаатай: {len(reps) - good}", text_color=BAD)
        last = reps[-1] if reps else None
        self._set("score", self.score_lbl, text=f"Оноо: {last.score}" if last else "",
                  text_color=score_color(last.score) if last else TEXT2)

        counter = self.engine.workout.analyzer.counter
        if fb.main_angle is not None:
            # Давталтыг үнэлдэг (бага тэгшитгэсэн) өнцгөөр: «гүнд хүрлээ» гэх дохиотой зөрөхгүй
            angle = min(fb.main_angle, fb.metrics.get("depth_angle") or fb.main_angle)
            frac = (counter.top - angle) / max(counter.top - counter.depth, 1)
            frac = max(0.0, min(1.0, frac))
            txt = f"Гүн: {JOINT[ex]} {angle:.0f}°  (зорилт ≤ {counter.depth:.0f}°)"
        else:
            frac, txt = 0.0, "Гүн: хүн харагдахгүй байна"
        self._set("dlbl", self.depth_lbl, text=txt)
        reached = frac >= 1.0
        self._set("dcol", self.depth_bar, progress_color=GOOD if reached else WARN)
        if abs(self._cache.get("dval", -1) - frac) > 0.01:
            self._cache["dval"] = frac
            self.depth_bar.set(frac)

        color = LEVEL_COLORS.get(wv.level, INFO)
        self._set("tipc", self.tip_bar, fg_color=color)
        self._set("tip", self.tip_lbl, text=t(wv.message, "mn"))
        detail = TIPS.get(wv.message) or PHASE_HINTS.get(wv.phase, "")
        self._set("tipd", self.tip_detail, text=detail)
        self._show_setup_icon(ex if wv.phase == "setup" else None)
        if wv.phase == "setup" and wv.setup_checks is not None and self.engine.kind != "video":
            self.checklist.set(ex, wv.setup_checks, wv.ready_progress)
            self.checklist.show()
        else:
            self.checklist.hide()
        can_skip = wv.phase in ("setup", "countdown", "rest")
        self._set("skip", self.skip_btn, state="normal" if can_skip else "disabled")
        self._set("mirror", self.mirror_btn, state="normal" if self.engine.kind == "camera" else "disabled")
        p = ef.perf
        self._set("perf", self.perf_lbl, text=f"{p.get('fps', 0):.0f} FPS · pose {p.get('pose_ms', 0):.0f} ms")


# =============================================================================
# Дүнгийн хуудас
# =============================================================================
class SummaryPage(ctk.CTkScrollableFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.grid_columnconfigure(0, weight=1)
        self.charts = []

    def show(self, workouts, duration, csv_path):
        for w in self.winfo_children():
            w.destroy()
        self.charts = []
        row = 0
        mins, secs = divmod(int(duration), 60)
        header(self, "Дасгал дууслаа!",
               f"Нийт хугацаа {mins}:{secs:02d}" + ("  ·  Дүн logs/ хавтсанд хадгалагдсан" if csv_path else "")
               ).grid(row=row, column=0, sticky="w", padx=8, pady=(8, 12))
        row += 1
        if not workouts:
            ctk.CTkLabel(self, text="Тоологдсон давталт алга. Камерын өмнө бүтэн харагдаж, эхлэх байрлалдаа "
                         "1 секунд зогсоход тоолол эхэлнэ.", font=font(15), text_color=TEXT2, wraplength=700,
                         justify="left").grid(row=row, column=0, sticky="w", padx=8)
            row += 1
        records = load_history(self.app.log_dir) if workouts else []
        for w in workouts:
            row = self._section(w, row, records, csv_path)
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.grid(row=row, column=0, sticky="w", padx=8, pady=(8, 16))
        ctk.CTkButton(bar, text="Дахин хийх", height=44, width=160, font=font(15, "bold"), **PRIMARY,
                      command=self.app.start_workout).pack(side="left")
        sec = SECONDARY
        ctk.CTkButton(bar, text="Нүүр хуудас", height=44, width=150, font=font(15),
                      command=lambda: self.app.show("home"), **sec).pack(side="left", padx=10)
        ctk.CTkButton(bar, text="Түүх харах", height=44, width=150, font=font(15),
                      command=lambda: self.app.show("history"), **sec).pack(side="left")

    def _section(self, w, row, records=(), csv_path=None):
        s = w.summary()
        section_title(self, EX_TITLES[w.name]).grid(row=row, column=0, sticky="w", padx=8, pady=(8, 6))
        row += 1
        tiles = ctk.CTkFrame(self, fg_color="transparent")
        tiles.grid(row=row, column=0, sticky="ew")
        tiles.grid_columnconfigure((0, 1, 2, 3), weight=1, uniform="t")
        acc = s["accuracy"] * 100
        items = [("Нийт давталт", str(s["reps"]), f"{len(s['sets'])} сет"),
                 ("Зөв давталт", str(s["correct"]), f"алдаатай {s['reps'] - s['correct']}"),
                 ("Нарийвчлал", f"{acc:.0f}%", "сайн байна" if acc >= 80 else "сайжруулах боломжтой"),
                 ("Дундаж оноо", f"{s['avg_score']:.0f}", f"100-аас · {s['avg_duration']:.1f} с / давталт")]
        for i, (lab, val, sub) in enumerate(items):
            StatTile(tiles, lab, val, sub).grid(row=0, column=i, sticky="ew", padx=8, pady=4)
        row += 1
        self._compare(w.name, s, records, csv_path).grid(row=row, column=0, sticky="ew", padx=8, pady=(8, 0))
        row += 1

        card = Card(self)
        card.grid(row=row, column=0, sticky="ew", padx=8, pady=8)
        card.grid_columnconfigure(0, weight=1)
        section_title(card, "Давталт бүрийн гүн").grid(row=0, column=0, sticky="w", padx=18, pady=(14, 0))
        joint_gen = {"squat": "өвдөгний", "pushup": "тохойны"}[w.name]
        caption = (f"Баганын өндөр = 180° − {joint_gen} хамгийн бага өнцөг: өндөр байх тусам гүн. "
                   "Тасархай шугамаас дээш бол хангалттай гүн. Багана дээр хулганаа аваачвал дэлгэрэнгүй.")
        ctk.CTkLabel(card, text=caption, font=font(12), text_color=MUTED, anchor="w").grid(
            row=1, column=0, sticky="w", padx=18)
        chart = RepChart(card)
        chart.grid(row=2, column=0, sticky="ew", padx=12, pady=(4, 12))
        chart.set_data(w.sets, DEPTH[w.name], issue_title, JOINT[w.name])
        self.charts.append(chart)
        row += 1

        card = Card(self)
        card.grid(row=row, column=0, sticky="ew", padx=8, pady=8)
        card.grid_columnconfigure(1, weight=1)
        section_title(card, "Юуг сайжруулах вэ").grid(row=0, column=0, columnspan=2, sticky="w", padx=18,
                                                      pady=(14, 6))
        if not s["issues"] and not s["warnings"]:
            ctk.CTkLabel(card, text="✓  Алдаа гараагүй. Маш сайн байна!", font=font(15, "bold"),
                         text_color=GOOD).grid(row=1, column=0, columnspan=2, sticky="w", padx=18, pady=(0, 16))
        # Алдаа (давталтыг буруу болгосон) улаанаар, сануулга (зөвхөн оноо бууруулсан) шараар
        items = [(k, n, BAD) for k, n in s["issues"]] + [(k, n, WARN) for k, n in s["warnings"]]
        for i, (key, n, color) in enumerate(items, 1):
            ctk.CTkLabel(card, text=f"{n}×", font=font(18, "bold"), text_color=color, width=50).grid(
                row=2 * i - 1, column=0, rowspan=2, sticky="n", padx=(14, 4), pady=(4, 10))
            ctk.CTkLabel(card, text=issue_title(key), font=font(15, "bold"), text_color=TEXT, anchor="w").grid(
                row=2 * i - 1, column=1, sticky="w", padx=(4, 18), pady=(4, 0))
            ctk.CTkLabel(card, text=TIPS.get(key, ""), font=font(13), text_color=TEXT2, anchor="w", justify="left",
                         wraplength=820).grid(row=2 * i, column=1, sticky="w", padx=(4, 18), pady=(0, 10))
        return row + 1

    def _compare(self, exercise, s, records, csv_path):
        """Өмнөх ижил дасгалтай харьцуулсан мөр: ахиц харагдвал урам өгнө."""
        card = Card(self)
        card.grid_columnconfigure(1, weight=1)
        cmp = compare_with_history(records, exercise, s["reps"], s["correct"], exclude_path=csv_path)
        prev = cmp["previous"]
        short = EX_TITLES[exercise].split(" (")[0]
        if prev is None:
            ctk.CTkLabel(card, text=f"Энэ таны анхны {short.lower()} дасгал. Дараагийн удаа үр дүнгээ энд "
                         "харьцуулж харна.", font=font(14), text_color=TEXT2, anchor="w").grid(
                row=0, column=0, columnspan=2, sticky="w", padx=18, pady=14)
            return card
        acc, pacc = round(s["accuracy"] * 100), round(prev.accuracy * 100)
        diff = acc - pacc
        arrow, color = ("▲", GOOD) if diff > 0 else ("▼", BAD) if diff < 0 else ("=", MUTED)
        ctk.CTkLabel(card, text=arrow, font=font(22, "bold"), text_color=color, width=36).grid(
            row=0, column=0, rowspan=2, padx=(14, 4), pady=12)
        change = f"{diff:+d} пункт".replace("-", "−") if diff else "өөрчлөлтгүй"
        ctk.CTkLabel(card, text=f"Нарийвчлал: өмнөх удаа {pacc}%, одоо {acc}% ({change})", font=font(15, "bold"),
                     text_color=TEXT, anchor="w").grid(row=0, column=1, sticky="w", pady=(12, 0))
        note = ("Ахиц гарч байна, үргэлжлүүлээрэй!" if diff > 0 else
                "Доорх зөвлөмжийг анхаарвал дараагийн удаа сайжирна." if diff < 0 else "Тогтвортой байна.")
        ctk.CTkLabel(card, text=f"Өмнөх {short.lower()} дасгал ({prev.when:%m/%d %H:%M}): {prev.reps} давталт, "
                     f"{prev.correct} зөв. {note}", font=font(13), text_color=TEXT2, anchor="w").grid(
            row=1, column=1, sticky="w", pady=(0, 12))
        if cmp["new_best"]:
            ctk.CTkLabel(card, text="★  Шинэ дээд амжилт", font=font(13, "bold"), text_color="#ffffff",
                         fg_color=GOOD, corner_radius=8, height=28).grid(row=0, column=2, rowspan=2, padx=16)
        return card

    def refresh_theme(self):
        for c in self.charts:
            c.redraw()


# =============================================================================
# Түүх
# =============================================================================
class HistoryPage(ctk.CTkScrollableFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.grid_columnconfigure(0, weight=1)
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 12))
        top.grid_columnconfigure(0, weight=1)
        header(top, "Түүх", "Өмнөх дасгалуудын дүн (logs/ хавтас дахь CSV файлуудаас).").grid(row=0, column=0,
                                                                                            sticky="w")
        sec = SECONDARY
        self.filter = ctk.CTkSegmentedButton(top, values=list(HISTORY_FILTERS), command=lambda v: self.refresh(),
                                             font=font(13), width=230, height=32, dynamic_resizing=False, **SEG)
        self.filter.set("Бүгд")
        self.filter.grid(row=0, column=1, padx=(0, 12))
        ctk.CTkButton(top, text="Хавтас нээх", width=120, command=self._open_folder, **sec).grid(row=0, column=2)
        ctk.CTkButton(top, text="Шинэчлэх", width=110, command=self.refresh, **sec).grid(row=0, column=3, padx=(8, 0))

        self.tiles = ctk.CTkFrame(self, fg_color="transparent")
        self.tiles.grid(row=1, column=0, sticky="ew")
        self.tiles.grid_columnconfigure((0, 1, 2, 3), weight=1, uniform="t")
        self.t_sessions = StatTile(self.tiles, "Нийт дасгал")
        self.t_reps = StatTile(self.tiles, "Нийт давталт")
        self.t_acc = StatTile(self.tiles, "Дундаж нарийвчлал")
        self.t_last = StatTile(self.tiles, "Сүүлийн дасгал")
        for i, tile in enumerate((self.t_sessions, self.t_reps, self.t_acc, self.t_last)):
            tile.grid(row=0, column=i, sticky="ew", padx=8, pady=4)

        self.chart_card = Card(self)
        self.chart_card.grid(row=2, column=0, sticky="ew", padx=8, pady=8)
        self.chart_card.grid_columnconfigure(0, weight=1)
        section_title(self.chart_card, "Сүүлийн дасгалууд").grid(row=0, column=0, sticky="w", padx=18, pady=(14, 0))
        self.chart = HistoryChart(self.chart_card)
        self.chart.grid(row=1, column=0, sticky="ew", padx=12, pady=(4, 12))

        self.table = Card(self)
        self.table.grid(row=3, column=0, sticky="ew", padx=8, pady=8)
        self.empty = ctk.CTkLabel(self, text="", font=font(15), text_color=TEXT2)

    def _open_folder(self):
        os.makedirs(self.app.log_dir, exist_ok=True)
        open_path(self.app.log_dir)

    def refresh(self):
        records = load_history(self.app.log_dir)
        ex = HISTORY_FILTERS.get(self.filter.get())
        if ex:
            records = [r for r in records if r.exercise == ex]
        for w in self.table.winfo_children():
            w.destroy()
        if not records:
            for w in (self.tiles, self.chart_card, self.table):
                w.grid_remove()
            self.empty.configure(text="Энэ дасгалаар түүх алга." if ex else
                                 "Одоогоор дасгалын түүх алга. Эхний дасгалаа хийгээд энд буцаж ирээрэй!")
            self.empty.grid(row=4, column=0, sticky="w", padx=12, pady=12)
            return
        self.empty.grid_remove()
        for w in (self.tiles, self.chart_card, self.table):
            w.grid()
        total = sum(r.reps for r in records)
        recent = records[:10]
        acc = sum(r.correct for r in recent) / max(sum(r.reps for r in recent), 1)
        self.t_sessions.set(str(len(records)), "дасгал хийсэн")
        self.t_reps.set(str(total), f"зөв {sum(r.correct for r in records)}")
        self.t_acc.set(f"{acc * 100:.0f}%", "сүүлийн 10 дасгалаар")
        self.t_last.set(records[0].when.strftime("%m/%d"), records[0].when.strftime("%H:%M · ")
                        + EX_TITLES.get(records[0].exercise, records[0].exercise))
        self.chart.set_data(records, lambda k: EX_TITLES.get(k, k))

        cols = ["Огноо", "Дасгал", "Давталт", "Зөв", "Нарийвчлал", "Оноо", "Хамгийн их гарсан алдаа"]
        self.table.grid_columnconfigure(6, weight=1)
        for c, name in enumerate(cols):
            ctk.CTkLabel(self.table, text=name, font=font(13, "bold"), text_color=TEXT2, anchor="w").grid(
                row=0, column=c, sticky="w", padx=14, pady=(12, 6))
        for i, r in enumerate(records[:50], 1):
            top_issue = issue_title(r.issues.most_common(1)[0][0]) if r.issues else "–"
            vals = [r.when.strftime("%Y-%m-%d %H:%M"), EX_TITLES.get(r.exercise, r.exercise), str(r.reps),
                    str(r.correct), f"{r.accuracy * 100:.0f}%",
                    f"{r.avg_score:.0f}" if r.avg_score is not None else "–", top_issue]
            striped = i % 2 == 0  # мөр алгасан дэвсгэр: урт хүснэгтийг нүдээр дагахад амар
            if striped:
                ctk.CTkFrame(self.table, fg_color=INSET, corner_radius=6, height=26).grid(
                    row=i, column=0, columnspan=len(cols), sticky="nsew", padx=6)
            for c, v in enumerate(vals):
                ctk.CTkLabel(self.table, text=v, font=font(13), text_color=TEXT, anchor="w",
                             fg_color=INSET if striped else "transparent").grid(
                    row=i, column=c, sticky="w", padx=14, pady=3)
        ctk.CTkLabel(self.table, text="").grid(row=len(records[:50]) + 1, column=0, pady=2)

    def refresh_theme(self):
        self.chart.redraw()


# =============================================================================
# Заавар
# =============================================================================
HELP = [
    ("Камерыг хэрхэн байрлуулах вэ", [
        "Камераас 2–3 метр зайд зогсож, толгойноос хөл хүртэл бүтэн харагдах ёстой.",
        "Squat: хажуугаараа зогсвол хамгийн нарийн (гүн, их бие, өсгий). Урдаас зогсвол өвдөг дотогш орохыг шалгана.",
        "Push-up: заавал хажуугаас. Камерыг шалнаас 30–60 см өндөрт тавина.",
        "Гэрэлтүүлэг сайн, ар тал энгийн байвал илүү тогтвортой ажиллана.",
    ]),
    ("Дасгал хэрхэн явагддаг вэ", [
        "1. Бэлтгэл: видеоны зүүн дээд буланд шалгах жагсаалт гарна (камер таныг харж байна, бүтэн бие кадрт "
        "багтсан, эхлэх байрлал). Дутуу байгаа алхам шар «›» тэмдэгтэй, биеийн аль хэсэг харагдахгүй байгааг "
        "доод мөрөнд бичнэ.",
        "2. Эхлэх байрлалдаа (squat: шулуун зогсох, push-up: гараа тэнийлгэх) 1 секунд хөдөлгөөнгүй зогсоход "
        "хүрээ ногоон болно.",
        "3. 3-2-1 гэж тоолоод дасгал эхэлнэ. Зорилтот гүнд хүрэхэд богино «бип» дуу гарна. Давталт бүрийн дараа "
        "дуут дохио гарна: өсөх ая = зөв, буух ая = алдаатай.",
        "4. Сетийн зорилгод хүрэхэд амралтын таймер гарна. Бүх сет дуусахад дүнгийн хуудас нээгдэж, өмнөх "
        "дасгалтай тань харьцуулна.",
        "Давталт бүр 0–100 оноо авна: алдаа бүр −20, бүрэн босоогүй −15, гүехэн −15…−45, сануулга (хэт хурдан, "
        "хөлийн байрлал) −10. Сануулга нь давталтыг «алдаатай» болгодоггүй.",
        "Сетийн дундуур камерын өмнөөс 5 секундээс удаан гарвал дасгал түр зогсоно; буцаж ирээд эхлэх "
        "байрлалдаа зогсоход 3-2-1-ээр үргэлжилнэ.",
        "Видеоны доорх график өвдөг (эсвэл тохой)-ны өнцгийг харуулна: шугам ногоон бүсэд орвол хангалттай гүн "
        "суусан/буусан гэсэн үг. Давталт бүрийн хамгийн гүн цэг ногоон (зөв) эсвэл улаан (алдаатай) цэгээр "
        "тэмдэглэгдэнэ.",
    ]),
    ("Товчлуурууд (дасгалын үед)", [
        "Space: тоолол эсвэл амралтыг алгасах   ·   P: түр зогсоох / үргэлжлүүлэх",
        "S: дуу асаах / унтраах   ·   M: толин дүрс   ·   1 / 2: squat / push-up",
        "E: дасгалыг дуусгаж дүн харах   ·   Esc: гарах (давталт хийсэн бол дүнгээ харах эсэхийг асууна)",
        "F эсвэл F11: бүтэн дэлгэц (холоос харахад тохиромжтой; F эсвэл Esc дарж гарна)",
        "Нүүр хуудсанд Enter дарвал дасгал эхэлнэ.",
    ]),
    ("Юуг шалгадаг вэ", [
        "Squat: гүн (өвдөг ≤ 100°), их бие хэт урагш хазайх (> 50°), өвдөг дотогш орох (урдаас), "
        "өсгий газраас салах (хажуугаас), давталтын хооронд бүрэн босоогүй. Сануулга: хөлийн байрлал (урдаас), "
        "хэт хурдан давталт.",
        "Push-up: гүн (тохой ≤ 90°), бэлхүүс унжих / бөгс өргөх (мөр-хонго-шагай < 160°), гараа бүрэн тэнийлгээгүй.",
        "Шалгуурын түвшин (нүүр хуудас): Зөөлөн = өвдөг 110°, тохой 100°; Энгийн = 100°, 90°; Хатуу = 90°, 80°, "
        "их бие 45°-аас бага хазайх, илүү удаан хэмнэл. Бусад босгыг form_checker/config.py файлд өөрчилж болно.",
        "«Дасгалыг автоматаар таних» асаалттай бол хэвтээ (суниалтын) байрлалд орход push-up, босоход squat "
        "руу өөрөө шилжинэ. Сетийн дундуур (давталт хийж байхад) солигдохгүй.",
    ]),
    ("Асуудал гарвал", [
        "Камер нээгдэхгүй: нүүр хуудасны «Камер хайх» товчоор ажиллаж буй камерыг олно. " + camera_help(),
        "Тоолол эхлэхгүй: бие бүтэн харагдаж, эхлэх байрлалдаа 1 секунд зогсох хэрэгтэй. Шууд эхлэх бол Space.",
        "Удаан ажиллаж байна: «Хурдан (lite)» загварыг сонгоно.",
        "Камергүй үзэх бол нүүр хуудаснаас «Демо (камергүй)»-г сонгоно.",
        "Цонх, бичиг хэт жижиг эсвэл том: зүүн цэсний доод талын «Хэмжээ»-г өөрчилнө (жишээ нь Linux-ийн өндөр "
        "нягтралтай дэлгэцэд 150–200%, жижиг дэлгэцтэй зөөврийн компьютерт 90%).",
    ]),
]


class HelpPage(ctk.CTkScrollableFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.grid_columnconfigure(0, weight=1)
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 12))
        top.grid_columnconfigure(0, weight=1)
        header(top, "Заавар", "Аппыг хэрхэн ашиглах вэ").grid(row=0, column=0, sticky="w")
        ctk.CTkButton(top, text="Танилцуулгыг дахин үзэх", width=200, command=app.show_onboarding,
                      **SECONDARY).grid(row=0, column=1, sticky="e")
        for i, (title, lines) in enumerate(HELP, 1):
            card = Card(self)
            card.grid(row=i, column=0, sticky="ew", padx=8, pady=6)
            card.grid_columnconfigure(0, weight=1)
            section_title(card, title).grid(row=0, column=0, sticky="w", padx=18, pady=(14, 4))
            for j, line in enumerate(lines, 1):
                ctk.CTkLabel(card, text=line, font=font(14), text_color=TEXT2, anchor="w", justify="left",
                             wraplength=900).grid(row=j, column=0, sticky="w", padx=18,
                                                  pady=(2, 14 if j == len(lines) else 2))
