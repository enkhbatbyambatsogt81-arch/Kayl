"""Цонхны дээр гарч ирэх элементүүд: анх нээхэд гарах танилцуулга, асуулт (баталгаажуулах) карт,
дасгал эхлэхийн өмнөх шалгах жагсаалт.

Tkinter-ийн тусдаа цонх (Toplevel) Windows дээр заримдаа үндсэн цонхны ард нуугддаг тул бүгдийг
үндсэн цонхны дотор place()-ээр давхарлаж харуулна.
"""

from __future__ import annotations

import customtkinter as ctk
from PIL import Image, ImageDraw

from .theme import ACCENT, BG, BORDER, GOOD, INSET, PRIMARY, SECONDARY, TEXT, TEXT2, WARN, font
from .widgets import Card, camera_figure, stick_figure

LIGHT_FIG, DARK_FIG = (42, 120, 214), (120, 170, 235)

ONBOARDING_STEPS = [
    ("Дасгалаа сонго", [
        "Суулт (squat) эсвэл гар дээр суниалтын (push-up) карт дээр дарна.",
        "Зорилгоо сонго: анх удаа бол «Эхлэгч» (2 сет × 8 давталт) хангалттай.",
        "Камергүй бол «Демо» эх үүсвэрээр апп хэрхэн ажилладгийг үзэж болно.",
    ]),
    ("Камераа байрлуул", [
        "Камерыг хажуу талд чинь тавь: апп өвдөг, тохойн өнцгийг хажуугаас хамгийн зөв хэмждэг.",
        "Squat: 2–3 метр зайд, толгойноос хөл хүртэл бүтэн харагдахаар.",
        "Push-up: шалнаас 30–60 см өндөрт, 1.5–2 метр зайд.",
        "Гэрэл сайтай, ард чинь өөр хүн байхгүй байвал илүү нарийн ажиллана.",
    ]),
    ("Эхлэх байрлалдаа зогс", [
        "Дасгалын хуудсанд шалгах жагсаалт гарна. Бүгд ✓ болоод 1 секунд хөдөлгөөнгүй байхад "
        "3-2-1 гэж тоолоод эхэлнэ.",
        "Зорилтот гүнд хүрэхэд богино «бип» дуу гарна. Тэгвэл өндийж болно.",
        "Давталт бүрийн дараа ногоон цэг = зөв, улаан = алдаатай. Юуг засахыг баруун талд бичнэ.",
        "Дуусгах бол E, түр зогсоох бол P, бүтэн дэлгэц F11.",
    ]),
]


def _dots_strip(width, colors):
    """Давталтын цэгүүдийн жижиг жишээ (ногоон, ногоон, улаан, хоосон)."""
    W, H = width * 3, 120
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    r, gap = 36, 30
    x = (W - (len(colors) * 2 * r + (len(colors) - 1) * gap)) / 2
    for c in colors:
        box = [x, H / 2 - r, x + 2 * r, H / 2 + r]
        if c is None:
            d.ellipse(box, outline=(150, 150, 150, 255), width=8)
        else:
            d.ellipse(box, fill=c)
        x += 2 * r + gap
    return img.resize((width, 40), Image.LANCZOS)


def _step_image(step, color):
    """Алхам бүрийн зураг (PIL, тунгалаг дэвсгэртэй)."""
    W, H = 320, 250
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    if step == 0:
        img.alpha_composite(stick_figure("squat", (110, 150), color=color), (10, 40))
        img.alpha_composite(stick_figure("pushup", (180, 90), color=color), (135, 100))
    elif step == 1:
        img.alpha_composite(camera_figure("squat", (300, 120), color=color), (10, 0))
        img.alpha_composite(camera_figure("pushup", (300, 110), color=color), (10, 135))
    else:
        img.alpha_composite(stick_figure("squat", (100, 150), color=color, start=True), (40, 10))
        img.alpha_composite(stick_figure("pushup", (150, 70), color=color, start=True), (150, 90))
        green, red = (12, 163, 12, 255), (208, 59, 59, 255)
        img.alpha_composite(_dots_strip(220, [green, green, red, None]), (50, 195))
    return img


class Onboarding(ctk.CTkFrame):
    """Анх нээхэд гарах 3 алхамтай танилцуулга. «Заавар» хуудаснаас дахин нээж болно."""

    def __init__(self, master, on_close, on_demo):
        super().__init__(master, fg_color=BG, corner_radius=0)
        self.on_close, self.on_demo = on_close, on_demo
        self.step = 0
        self._open = False
        self.images = [ctk.CTkImage(light_image=_step_image(i, LIGHT_FIG), dark_image=_step_image(i, DARK_FIG),
                                    size=(320, 250)) for i in range(len(ONBOARDING_STEPS))]
        card = Card(self, border_width=1, width=880, height=480)  # тогтмол хэмжээ: алхам солиход үсрэхгүй
        card.place(relx=0.5, rely=0.5, anchor="center")
        card.grid_propagate(False)
        card.grid_columnconfigure(1, weight=1)
        card.grid_rowconfigure(2, weight=1)
        self.kicker = ctk.CTkLabel(card, text="", font=font(13, "bold"), text_color=ACCENT, anchor="w")
        self.kicker.grid(row=0, column=0, columnspan=2, sticky="w", padx=28, pady=(24, 0))
        self.title = ctk.CTkLabel(card, text="", font=font(26, "bold"), text_color=TEXT, anchor="w")
        self.title.grid(row=1, column=0, columnspan=2, sticky="w", padx=28, pady=(2, 12))
        self.pic = ctk.CTkLabel(card, text="", width=320, height=250)
        self.pic.grid(row=2, column=0, sticky="n", padx=(20, 8), pady=(0, 8))
        self.body = ctk.CTkFrame(card, fg_color="transparent", width=420)
        self.body.grid(row=2, column=1, sticky="nw", padx=(8, 28))
        self.lines = []
        for i in range(4):
            lbl = ctk.CTkLabel(self.body, text="", font=font(15), text_color=TEXT2, anchor="w", justify="left",
                               wraplength=400)
            lbl.grid(row=i, column=0, sticky="w", pady=(0, 10))
            self.lines.append(lbl)
        self.dots = ctk.CTkFrame(card, fg_color="transparent")
        self.dots.grid(row=3, column=0, sticky="w", padx=28, pady=(8, 24))
        self.dot_lbls = [ctk.CTkLabel(self.dots, text="●", font=font(16)) for _ in ONBOARDING_STEPS]
        for d in self.dot_lbls:
            d.pack(side="left", padx=3)
        bar = ctk.CTkFrame(card, fg_color="transparent")
        bar.grid(row=3, column=1, sticky="e", padx=28, pady=(8, 24))
        sec = SECONDARY
        b = dict(height=42, font=font(15), corner_radius=10)
        self.skip_btn = ctk.CTkButton(bar, text="Алгасах", width=100, command=self.close, fg_color="transparent",
                                      text_color=TEXT2, hover_color=INSET, **b)
        self.back_btn = ctk.CTkButton(bar, text="← Өмнөх", width=110, command=self.back, **b, **sec)
        self.demo_btn = ctk.CTkButton(bar, text="Камергүй туршиж үзэх", width=200, command=self._demo, **b, **sec)
        self.next_btn = ctk.CTkButton(bar, text="", width=150, command=self.next, **PRIMARY, **b)

    # ---- харуулах / нуух
    def open(self):
        self.step = 0
        self._render()
        self.place(x=0, y=0, relwidth=1, relheight=1)
        self.lift()
        self._open = True

    @property
    def visible(self):
        return self._open  # winfo_ismapped() дэлгэц шинэчлэгдэхээс өмнө худал буцаадаг

    def close(self):
        self.place_forget()
        self._open = False
        self.on_close()

    def _demo(self):
        self.close()
        self.on_demo()

    def next(self):
        if self.step >= len(ONBOARDING_STEPS) - 1:
            self.close()
        else:
            self.step += 1
            self._render()

    def back(self):
        if self.step > 0:
            self.step -= 1
            self._render()

    def on_key(self, k):
        if k in ("return", "right", "space"):
            self.next()
        elif k == "left":
            self.back()
        elif k == "escape":
            self.close()

    def _render(self):
        title, lines = ONBOARDING_STEPS[self.step]
        last = self.step == len(ONBOARDING_STEPS) - 1
        self.kicker.configure(text=f"ТАВТАЙ МОРИЛ · АЛХАМ {self.step + 1} / {len(ONBOARDING_STEPS)}")
        self.title.configure(text=title)
        self.pic.configure(image=self.images[self.step])
        for i, lbl in enumerate(self.lines):
            lbl.configure(text=f"•  {lines[i]}" if i < len(lines) else "")
        for i, d in enumerate(self.dot_lbls):
            d.configure(text_color=ACCENT if i == self.step else BORDER)
        for w in (self.skip_btn, self.back_btn, self.demo_btn, self.next_btn):
            w.pack_forget()
        if not last:
            self.skip_btn.pack(side="left", padx=(0, 8))
        if self.step > 0:
            self.back_btn.pack(side="left", padx=(0, 8))
        if last:
            self.demo_btn.pack(side="left", padx=(0, 8))
        self.next_btn.configure(text="Ойлголоо" if last else "Дараах →")
        self.next_btn.pack(side="left")


class ConfirmCard(Card):
    """Цонхны дотор гарах асуулт. buttons: [(текст, функц, "primary"|"secondary"), ...]."""

    def __init__(self, master, title, text, buttons):
        super().__init__(master, border_width=2, border_color=ACCENT)
        self.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(self, text=title, font=font(22, "bold"), text_color=TEXT, anchor="w").grid(
            row=0, column=0, sticky="w", padx=26, pady=(22, 4))
        self.text = ctk.CTkLabel(self, text=text, font=font(15), text_color=TEXT2, anchor="w", justify="left",
                                 wraplength=460)
        self.text.grid(row=1, column=0, sticky="w", padx=26, pady=(0, 18))
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.grid(row=2, column=0, sticky="e", padx=22, pady=(0, 22))
        for label, fn, style in buttons:
            kw = PRIMARY if style == "primary" else SECONDARY
            ctk.CTkButton(bar, text=label, command=fn, height=42, font=font(15), corner_radius=10, **kw).pack(
                side="left", padx=4)
        self._open = False

    def open(self, text=None):
        if text is not None:
            self.text.configure(text=text)
        self.place(relx=0.5, rely=0.45, anchor="center")
        self.lift()
        self._open = True

    def close(self):
        self.place_forget()
        self._open = False

    @property
    def visible(self):
        return self._open


class SetupChecklist(ctk.CTkFrame):
    """Видеон дээр гарах «эхлэхэд юу дутуу байна» жагсаалт. Видео үргэлж харанхуй дэвсгэртэй тул
    өнгөний горимоос үл хамааран бараан карт ашиглана. Холоос уншигдахаар том фонттой."""

    FG, MUTE, BGC = "#f2f2f0", "#9a9a94", "#1d1d1d"
    ITEMS = {
        "squat": ("Камер таныг харж байна", "Бүтэн бие кадрт багтсан", "Шулуун зогссон",
                  "1 секунд хөдөлгөөнгүй байх"),
        "pushup": ("Камер таныг харж байна", "Хажуугаараа, бүтэн бие харагдаж байна",
                   "Гараа тэнийлгэсэн (планк)", "1 секунд хөдөлгөөнгүй байх"),
    }

    def __init__(self, master):
        super().__init__(master, fg_color=self.BGC, corner_radius=12, border_width=1, border_color="#3a3a3a")
        self.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(self, text="Эхлэхэд бэлдэж байна", font=font(17, "bold"), text_color=self.FG,
                     anchor="w").grid(row=0, column=0, columnspan=2, sticky="w", padx=16, pady=(12, 6))
        self.icons, self.texts = [], []
        for i in range(4):
            ic = ctk.CTkLabel(self, text="○", font=font(18, "bold"), width=24, text_color=self.MUTE)
            ic.grid(row=i + 1, column=0, sticky="w", padx=(16, 6), pady=2)
            tx = ctk.CTkLabel(self, text="", font=font(16), text_color=self.MUTE, anchor="w")
            tx.grid(row=i + 1, column=1, sticky="w", padx=(0, 16), pady=2)
            self.icons.append(ic)
            self.texts.append(tx)
        self.hold = ctk.CTkProgressBar(self, height=8, progress_color=GOOD, fg_color="#3a3a3a", width=220)
        self.hold.grid(row=5, column=1, sticky="w", padx=(0, 16), pady=(2, 4))
        self.hold.set(0)
        ctk.CTkLabel(self, text="Хүлээлгүй эхлэх бол Space", font=font(12), text_color=self.MUTE, anchor="w").grid(
            row=6, column=0, columnspan=2, sticky="w", padx=16, pady=(2, 12))
        self._key = None

    def set(self, exercise, checks, progress):
        done = list(checks) + [progress >= 1.0]
        key = (exercise, tuple(done), round(progress, 2))
        if key == self._key:
            return
        self._key = key
        current = next((i for i, ok in enumerate(done) if not ok), None)
        for i, (ic, tx, label) in enumerate(zip(self.icons, self.texts, self.ITEMS[exercise])):
            if done[i]:
                ic.configure(text="✓", text_color=GOOD)
                tx.configure(text=label, text_color=self.FG)
            elif i == current:
                ic.configure(text="›", text_color=WARN)
                tx.configure(text=label, text_color=self.FG)
            else:
                ic.configure(text="○", text_color=self.MUTE)
                tx.configure(text=label, text_color=self.MUTE)
        self.hold.set(progress if all(checks) else 0)

    def show(self):
        if not self.winfo_ismapped():
            self.place(x=14, y=14, anchor="nw")
            self.lift()

    def hide(self):
        if self.winfo_ismapped():
            self.place_forget()
            self._key = None

