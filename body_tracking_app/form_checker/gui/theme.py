"""Өнгө ба фонтын тохиргоо. (цайвар, харанхуй) хос утгатай."""

import customtkinter as ctk

BG = ("#f3f3f1", "#141414")
SIDEBAR = ("#e9e8e4", "#1c1c1c")
CARD = ("#ffffff", "#212121")
INSET = ("#f0efeb", "#2a2a2a")
BORDER = ("#dddcd6", "#343434")
TEXT = ("#0b0b0b", "#f2f2f0")
TEXT2 = ("#52514e", "#b5b4ad")
MUTED = ("#8a897f", "#8a897f")
ACCENT = ("#2a78d6", "#3987e5")
ACCENT_HOVER = ("#2463b3", "#2a78d6")
ACCENT_SOFT = ("#e3eefb", "#1d2f45")
ZONE = ("#e6f4e6", "#1a2b1a")      # графикийн «хангалттай гүн» бүс (ногооны цайвар өнгө)

# Сонголтын товчлуурын (segmented) өнгө: цайвар горимд саарал дэвсгэр дээр цагаан бичиг уншигдахгүй
# байсан тул бүх төлөвт бараан бичиг, сонгосон нь цэнхэр туяатай.
SEG = dict(
    fg_color=("#e4e4e0", "#2c2c2c"),
    unselected_color=("#e4e4e0", "#2c2c2c"),
    unselected_hover_color=("#d8d8d3", "#383838"),
    selected_color=("#bcd5f5", "#2f5f9e"),
    selected_hover_color=("#a9c8f1", "#3a6db0"),
    text_color=("#0b0b0b", "#f2f2f0"),
    text_color_disabled=("#9a9a94", "#6a6a6a"),
)

# Төлөвийн өнгө: зөв / анхааруулга / алдаа. Үргэлж текст эсвэл тэмдэгтэй хамт ашиглана.
GOOD = "#0ca30c"
WARN = "#fab219"
BAD = "#d03b3b"
INFO = "#3987e5"
LEVEL_COLORS = {"ok": GOOD, "warn": WARN, "info": INFO}

PHASES = {
    "setup":     ("Бэлтгэл", WARN),
    "countdown": ("Эхлэх гэж байна", INFO),
    "active":    ("Дасгал", GOOD),
    "rest":      ("Амралт", INFO),
    "done":      ("Дууссан", GOOD),
}


def mode_index():
    return 1 if ctk.get_appearance_mode() == "Dark" else 0


def pick(pair):
    """(цайвар, харанхуй) хосоос одоогийн горимын өнгийг сонгоно (tk.Canvas-д хэрэгтэй)."""
    return pair[mode_index()] if isinstance(pair, tuple) else pair


def font(size=14, weight="normal"):
    return ctk.CTkFont(size=size, weight=weight)
