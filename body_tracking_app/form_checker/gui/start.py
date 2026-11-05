"""Эхлэх урсгал (2.3): Тавтай морил -> Бэлтгэлийн түвшин -> Дасгал -> (дасгалын хуудсанд) Камерын тохиргоо.

Апп нээгдэхэд олон тохиргоотой нүүр хуудсын оронд энэ урсгал гарна. Түвшин нь давталт, сет, амралт
болон техникийн шалгуурыг нэг дор сонгоно. Нарийвчилсан тохиргоо «Тохиргоо» хуудсанд хэвээр.
"""

from __future__ import annotations

import customtkinter as ctk
from PIL import Image, ImageDraw

from .theme import ACCENT, BORDER, FIGURE, INSET, MUTED, PRIMARY, SECONDARY, SELECT, TEXT, TEXT2, font
from .theme_toggle import ThemeToggle
from .transitions import STEP_SHIFT, Transition, place_fill
from .widgets import Card, stick_figure

APP_NAME = "Ухаалаг дасгалжуулагч"

# Бэлтгэлийн түвшин: нэр, хэнд, (давталт, сет, амралт), техникийн шалгуур (config.LEVEL_OVERRIDES)
LEVELS = {
    "easy": dict(name="Анхан шат", who="Дасгалаа дөнгөж эхэлж буй эсвэл бэртлээс сэргэж буй үед.",
                 goal=(8, 2, 60), rule="Уян", angles="Өвдөг 110°, тохой 100° хүртэл нугарахад тооцогдоно"),
    "normal": dict(name="Дунд шат", who="Тогтмол дасгал хийдэг хүмүүст.",
                   goal=(10, 3, 60), rule="Стандарт", angles="Өвдөг 100°, тохой 90° хүртэл нугарна"),
    "strict": dict(name="Ахисан шат", who="Техникээ төгөлдөржүүлэхийг зорьж буй тамирчдад.",
                   goal=(15, 4, 90), rule="Нарийн", angles="Өвдөг 90°, тохой 80°, нуруу босоо, тайван хэмнэл"),
}
EXERCISES = {
    "squat": ("Суулт", "Squat · гүн, нурууны байрлал, өвдөг"),
    "pushup": ("Гар дээр суниалт", "Push-up · тохойн өнцөг, биеийн шулуун байдал"),
}
STEPS = ("welcome", "level", "exercise")


def apply_level(settings, level):
    """Түвшнийг тохиргоонд бичнэ: шалгуур + давталт, сет, амралт. Дасгалыг хэрэглэгч өөрөө сонгоно."""
    reps, sets, rest = LEVELS[level]["goal"]
    settings.update(level=level, reps=reps, sets=sets, rest=rest, free_mode=False, auto_detect=False)


def _hover(widget, fn):
    widget.bind("<Button-1>", lambda e: fn())
    try:
        widget.configure(cursor="hand2")
    except Exception:  # noqa: BLE001 - зарим элемент cursor дэмждэггүй
        pass
    for child in widget.winfo_children():
        _hover(child, fn)


def _settings_icon(size=18):
    """«Нарийвчилсан тохиргоо» товчны гулсуурт дүрс (3 зураас, бөмбөлөгтэй)."""
    def draw(rgb):
        k = 4
        img = Image.new("RGBA", (size * k, size * k), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        w = max(1, round(1.7 * k))
        for i, x in enumerate((0.65, 0.3, 0.55)):
            y = (0.22 + i * 0.28) * size * k
            d.line((1.5 * k, y, (size - 1.5) * k, y), fill=rgb + (255,), width=w)
            cx = x * size * k
            r = 2.6 * k
            d.ellipse((cx - r, y - r, cx + r, y + r), fill=rgb + (255,))
        return img.resize((size, size), Image.LANCZOS)
    return ctk.CTkImage(light_image=draw((17, 17, 17)), dark_image=draw((242, 242, 242)), size=(size, size))


class ChoiceCard(Card):
    """Сонгох карт: сонгосон үед 2px цэнхэр хүрээ ба ✓ тэмдэг."""

    def __init__(self, master, on_pick):
        super().__init__(master, corner_radius=18)
        self.on_pick = on_pick
        self.grid_columnconfigure(0, weight=1)
        self.mark = ctk.CTkLabel(self, text="", width=26, height=26, corner_radius=13, font=font(13, "bold"))

    def finish(self):
        self.mark.place(relx=1.0, x=-20, y=20, anchor="ne")
        _hover(self, self.on_pick)

    def set_selected(self, selected):
        self.configure(border_color=SELECT if selected else BORDER, border_width=2 if selected else 1)
        self.mark.configure(text="✓" if selected else "", fg_color=SELECT if selected else "transparent",
                            text_color="#ffffff")


class StartFlow(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.step = "welcome"
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # --- дээд мөр: буцах, алхмын заалт
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", padx=8, pady=(4, 0))
        top.grid_columnconfigure((0, 2), weight=1, uniform="side")
        self.back_btn = ctk.CTkButton(top, text="←  Буцах", width=100, height=40, font=font(15),
                                      fg_color="transparent", text_color=TEXT2, hover_color=INSET, command=self.back)
        self.back_btn.grid(row=0, column=0, sticky="w")
        self.brand = ctk.CTkLabel(top, text=APP_NAME, font=font(17, "bold"), text_color=TEXT)
        self.brand.grid(row=0, column=0, sticky="w", padx=4)
        prog = ctk.CTkFrame(top, fg_color="transparent")
        prog.grid(row=0, column=1)
        bars = ctk.CTkFrame(prog, fg_color="transparent")
        bars.pack()
        self.bars = [ctk.CTkFrame(bars, width=56, height=4, corner_radius=2, fg_color=BORDER) for _ in range(3)]
        for b in self.bars:
            b.pack(side="left", padx=3)
        self.step_lbl = ctk.CTkLabel(prog, text="", font=font(13), text_color=TEXT2)
        self.step_lbl.pack(pady=(4, 0))
        self.prog = prog
        right = ctk.CTkFrame(top, fg_color="transparent")
        right.grid(row=0, column=2, sticky="e")
        ThemeToggle(right, app).pack(side="right")
        # 3.0: товч гэдэг нь шууд танигдахаар хүрээтэй, дүрстэй
        self.more_btn = ctk.CTkButton(right, text="Нарийвчилсан тохиргоо", image=_settings_icon(), compound="left",
                                      width=214, height=40, corner_radius=10, font=font(14, "bold"),
                                      command=lambda: app.show("home"), **SECONDARY)
        self.more_btn.pack(side="right", padx=(0, 10))

        # 3.1: алхмууд нэг талбайд давхарлан байрлаж, урагшлахад баруунаас, буцахад зүүнээс гулсаж орно
        self.body = ctk.CTkFrame(self, fg_color="transparent")
        self.body.grid(row=1, column=0, sticky="nsew", pady=(8, 0))
        self._slide = None
        self.frames = {"welcome": self._build_welcome(), "level": self._build_level(),
                       "exercise": self._build_exercise()}

        # --- доод мөр: тайлбар + үндсэн товч
        foot = ctk.CTkFrame(self, fg_color="transparent")
        foot.grid(row=2, column=0, sticky="ew", padx=8, pady=(8, 4))
        foot.grid_columnconfigure(0, weight=1)
        self.foot_note = ctk.CTkLabel(foot, text="", font=font(14), text_color=TEXT2, anchor="w")
        self.foot_note.grid(row=0, column=0, sticky="w", padx=4)
        self.next_btn = ctk.CTkButton(foot, text="", height=52, width=230, font=font(17, "bold"), corner_radius=12,
                                      command=self.next, **PRIMARY)
        self.next_btn.grid(row=0, column=1, sticky="e")
        self.refresh()
        self.render()

    # ---- алхам бүрийн агуулга
    def _build_welcome(self):
        f = ctk.CTkFrame(self.body, fg_color="transparent")
        f.grid_columnconfigure((0, 1), weight=1, uniform="half")
        f.grid_rowconfigure(0, weight=1)
        text = ctk.CTkFrame(f, fg_color="transparent")
        text.grid(row=0, column=0, sticky="w", padx=(48, 24))
        ctk.CTkLabel(text, text="Тавтай морилно уу", font=font(14, "bold"), text_color=TEXT2,
                     anchor="w").pack(anchor="w")
        ctk.CTkLabel(text, text="Дасгал бүрээ\nзөв техникээр", font=font(44, "bold"), text_color=TEXT,
                     anchor="w", justify="left").pack(anchor="w", pady=(10, 14))
        ctk.CTkLabel(text, text="Камер таны хөдөлгөөнийг бодит хугацаанд шинжилж, давталтыг тоолж, "
                                "техникийн алдааг тэр даруй сануулна.",
                     font=font(17), text_color=TEXT2, anchor="w", justify="left", wraplength=440).pack(anchor="w")
        pic = ctk.CTkFrame(f, fg_color=INSET, corner_radius=28)
        pic.grid(row=0, column=1, sticky="nsew", padx=(24, 8), pady=8)
        img = ctk.CTkImage(light_image=stick_figure("squat", (340, 260), color=FIGURE[0]),
                           dark_image=stick_figure("squat", (340, 260), color=FIGURE[1]), size=(340, 260))
        ctk.CTkLabel(pic, text="", image=img).place(relx=0.5, rely=0.5, anchor="center")
        return f

    def _title(self, master, title, sub):
        ctk.CTkLabel(master, text=title, font=font(34, "bold"), text_color=TEXT).pack(pady=(12, 6))
        ctk.CTkLabel(master, text=sub, font=font(16), text_color=TEXT2).pack(pady=(0, 24))

    def _build_level(self):
        f = ctk.CTkFrame(self.body, fg_color="transparent")
        self._title(f, "Бэлтгэлийн түвшингээ сонгоно уу",
                    "Түвшин нь давталт, сетийн тоо болон техникийн шалгуурын нарийвчлалыг тодорхойлно.")
        row = ctk.CTkFrame(f, fg_color="transparent")
        row.pack(fill="x", padx=8)
        row.grid_columnconfigure((0, 1, 2), weight=1, uniform="lvl")
        self.level_cards = {}
        for col, (key, lv) in enumerate(LEVELS.items()):
            card = ChoiceCard(row, lambda k=key: self.pick_level(k))
            card.grid(row=0, column=col, sticky="nsew", padx=10)
            bars = ctk.CTkFrame(card, fg_color="transparent")
            bars.grid(row=0, column=0, sticky="w", padx=24, pady=(24, 14))
            for i in range(3):
                ctk.CTkFrame(bars, width=6, height=12 + 4 * i, corner_radius=2,
                             fg_color=ACCENT if i < col + 1 else BORDER).pack(side="left", padx=2, anchor="s")
            name = ctk.CTkFrame(card, fg_color="transparent")
            name.grid(row=1, column=0, sticky="w", padx=24)
            ctk.CTkLabel(name, text=lv["name"], font=font(22, "bold"), text_color=TEXT).pack(side="left")
            if key == "normal":
                ctk.CTkLabel(name, text="Зөвлөмж", font=font(12, "bold"), text_color=TEXT, fg_color=INSET,
                             corner_radius=10, height=24, width=76).pack(side="left", padx=(10, 0))
            ctk.CTkLabel(card, text=lv["who"], font=font(14), text_color=TEXT2, anchor="w", justify="left",
                         wraplength=260).grid(row=2, column=0, sticky="w", padx=24, pady=(6, 14))
            ctk.CTkFrame(card, height=1, fg_color=BORDER).grid(row=3, column=0, sticky="ew", padx=24)
            reps, sets, rest = lv["goal"]
            facts = (("Сет × давталт", f"{sets} × {reps}"), ("Амралт", f"{rest} сек"),
                     ("Техникийн шалгуур", lv["rule"]))
            for i, (k, v) in enumerate(facts):
                r = ctk.CTkFrame(card, fg_color="transparent")
                r.grid(row=4 + i, column=0, sticky="ew", padx=24, pady=(12 if i == 0 else 4, 0))
                ctk.CTkLabel(r, text=k, font=font(14), text_color=TEXT2).pack(side="left")
                ctk.CTkLabel(r, text=v, font=font(14, "bold"), text_color=TEXT).pack(side="right")
            ctk.CTkLabel(card, text=lv["angles"], font=font(12), text_color=MUTED, anchor="w", justify="left",
                         wraplength=260).grid(row=7, column=0, sticky="w", padx=24, pady=(10, 22))
            card.finish()
            self.level_cards[key] = card
        return f

    def _build_exercise(self):
        f = ctk.CTkFrame(self.body, fg_color="transparent")
        self._title(f, "Дасгалаа сонгоно уу", "Дасгалын явцад ч өөрчлөх боломжтой.")
        row = ctk.CTkFrame(f, fg_color="transparent")
        row.pack(fill="x", padx=60)
        row.grid_columnconfigure((0, 1), weight=1, uniform="ex")
        self.ex_cards = {}
        for col, (key, (title, sub)) in enumerate(EXERCISES.items()):
            card = ChoiceCard(row, lambda k=key: self.pick_exercise(k))
            card.grid(row=0, column=col, sticky="nsew", padx=10)
            pic = ctk.CTkFrame(card, fg_color=INSET, corner_radius=12, height=190)
            pic.grid(row=0, column=0, sticky="ew", padx=18, pady=(18, 0))
            pic.grid_propagate(False)
            img = ctk.CTkImage(light_image=stick_figure(key, (220, 150), color=FIGURE[0]),
                               dark_image=stick_figure(key, (220, 150), color=FIGURE[1]), size=(220, 150))
            ctk.CTkLabel(pic, text="", image=img).place(relx=0.5, rely=0.5, anchor="center")
            ctk.CTkLabel(card, text=title, font=font(21, "bold"), text_color=TEXT, anchor="w").grid(
                row=1, column=0, sticky="w", padx=20, pady=(16, 0))
            ctk.CTkLabel(card, text=sub, font=font(14), text_color=TEXT2, anchor="w").grid(
                row=2, column=0, sticky="w", padx=20, pady=(2, 20))
            card.finish()
            card.mark.place_configure(rely=1.0, y=-24, anchor="se")
            self.ex_cards[key] = card
        return f

    # ---- төлөв
    def refresh(self):
        s = self.app.settings
        level = s["level"] if s["level"] in LEVELS else "normal"
        for k, c in self.level_cards.items():
            c.set_selected(k == level)
        for k, c in self.ex_cards.items():
            c.set_selected(k == s["exercise"])

    def pick_level(self, key):
        apply_level(self.app.settings, key)
        self.refresh()

    def pick_exercise(self, key):
        self.app.settings["exercise"] = key
        self.refresh()

    def open(self):
        """Апп нээгдэх, эсвэл «Эхлэх» цэс дарахад эхний алхмаас."""
        self.step = "welcome"
        self.refresh()
        self.render()

    def finish_transition(self):
        if self._slide is not None:
            self._slide.finish()
            self._slide = None

    def render(self, direction=0):
        """direction: 1 урагшлах, -1 буцах, 0 хөдөлгөөнгүй (урсгал шинээр нээгдэх үед)."""
        self.finish_transition()
        step = self.step
        frame = self.frames[step]
        shown = [f for name, f in self.frames.items() if name != step and f.winfo_manager()]

        def reveal():
            frame.lift()
            for f in shown:
                f.place_forget()
            self._render_chrome(step)

        place_fill(frame)
        if not direction or not shown or not self.winfo_ismapped():
            reveal()
            return
        frame.lower(shown[0])   # шинэ алхмыг доор нь зурж бэлдэнэ
        self._slide = Transition(self, frame, reveal, dx=STEP_SHIFT * direction)

    def _render_chrome(self, step):
        """Дээд мөр (буцах, алхмын заалт) ба доод мөрийн товч."""
        index = STEPS.index(step)
        welcome = step == "welcome"
        self.back_btn.grid_remove() if welcome else self.back_btn.grid()
        self.brand.grid() if welcome else self.brand.grid_remove()
        self.prog.grid_remove() if welcome else self.prog.grid()
        for i, b in enumerate(self.bars):
            b.configure(fg_color=ACCENT if i < index else BORDER)
        self.step_lbl.configure(text=f"Алхам {index} / 3")
        if welcome:
            self.foot_note.configure(text="эсвэл Enter товч дарна уу")
            self.next_btn.configure(text="Эхлэх  →")
        elif step == "level":
            self.foot_note.configure(text="Түвшнээ «Нарийвчилсан тохиргоо»-ноос хүссэн үедээ өөрчилж болно.")
            self.next_btn.configure(text="Үргэлжлүүлэх  →")
        else:
            self.foot_note.configure(text="Дараагийн алхамд камераа тохируулна.")
            self.next_btn.configure(text="Үргэлжлүүлэх  →")

    def next(self):
        if self.step == "exercise":
            s = self.app.settings
            if s["source"] == "video":   # урсгал нь камер эсвэл демогоор явна; видео бол тохиргооны хуудсанд
                s["source"] = "camera"
            self.app.start_workout()
            return
        if self.step == "level":   # сонгосон (эсвэл өмнө нь хадгалсан) түвшний зорилгыг хэрэглэнэ
            level = self.app.settings["level"]
            apply_level(self.app.settings, level if level in LEVELS else "normal")
        self.step = STEPS[STEPS.index(self.step) + 1]
        self.refresh()
        self.render(direction=1)

    def back(self):
        i = STEPS.index(self.step)
        if i > 0:
            self.step = STEPS[i - 1]
            self.render(direction=-1)

    def on_key(self, k):
        if k == "return":
            self.next()
        elif k in ("escape", "backspace"):
            self.back()
        elif self.step == "level" and k in ("1", "2", "3"):
            self.pick_level(list(LEVELS)[int(k) - 1])
        elif self.step == "exercise" and k in ("1", "2"):
            self.pick_exercise(list(EXERCISES)[int(k) - 1])
