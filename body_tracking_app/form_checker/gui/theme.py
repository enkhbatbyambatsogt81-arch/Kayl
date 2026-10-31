"""Өнгө ба фонтын тохиргоо. (цайвар, харанхуй) хос утгатай.

2.2: цагаан, минимал загвар (цайвар горим анхдагч). Цагаан дэвсгэр, нимгэн саарал хүрээ, хар-цагаан товчлуур.
Өнгийг зөвхөн утгатай газар хэрэглэнэ: ногоон = зөв, улаан = алдаатай, шар = анхааруулга.
"""

import customtkinter as ctk

BG = ("#ffffff", "#141414")
SIDEBAR = ("#fafafa", "#1a1a1a")
CARD = ("#ffffff", "#1f1f1f")
INSET = ("#f5f5f5", "#2a2a2a")
BORDER = ("#e8e8e8", "#333333")
BORDER_STRONG = ("#d4d4d4", "#454545")   # товчлуур, асуулт зэрэг дарж болох зүйлийн хүрээ
TEXT = ("#111111", "#f2f2f2")
TEXT2 = ("#5c5c5c", "#b3b3b3")
MUTED = ("#9a9a9a", "#8a8a8a")
ACCENT = ("#111111", "#f2f2f2")          # үндсэн үйлдэл, сонгосон зүйл: хар (харанхуй горимд цагаан)
ACCENT_HOVER = ("#333333", "#d6d6d6")
ON_ACCENT = ("#ffffff", "#111111")       # ACCENT дэвсгэр дээрх бичиг
ACCENT_SOFT = ("#f0f0f0", "#2a2a2a")     # сонгосон цэсний дэвсгэр
ZONE = ("#eef7ee", "#1a2b1a")            # графикийн «хангалттай гүн» бүс (ногооны цайвар өнгө)
VIDEO_BG = ("#f5f5f5", "#000000")        # видеоны эргэн тойрон (кадрын харьцаа таарахгүй үед)
FIGURE = ((17, 17, 17), (235, 235, 235))  # дүрсний өнгө (RGB): цайвар, харанхуй горимд

# Сонголтын товчлуур (segmented): саарал зам дээр сонгосон нь цагаан «таблет», бичиг үргэлж бараан
# (CustomTkinter-д сонгосон, сонгоогүйн бичгийн өнгө нэг байдаг).
SEG = dict(
    fg_color=("#ececec", "#2a2a2a"),
    unselected_color=("#ececec", "#2a2a2a"),
    unselected_hover_color=("#e2e2e2", "#333333"),
    selected_color=("#ffffff", "#4a4a4a"),
    selected_hover_color=("#ffffff", "#525252"),
    text_color=TEXT,
    text_color_disabled=("#b5b5b5", "#666666"),
)

# Товчлуурын хэв маяг. Идэвхгүй (disabled) үед бичиг нь бүдгэрч, дарах боломжгүй нь шууд харагдана.
PRIMARY = dict(fg_color=ACCENT, hover_color=ACCENT_HOVER, text_color=ON_ACCENT,
               text_color_disabled=("#8f8f8f", "#8a8a8a"))
SECONDARY = dict(fg_color="transparent", border_width=1, border_color=BORDER_STRONG, text_color=TEXT,
                 hover_color=INSET, text_color_disabled=MUTED)

# Төлөвийн өнгө: зөв / анхааруулга / алдаа. Үргэлж текст эсвэл тэмдэгтэй хамт ашиглана.
GOOD = "#0ca30c"
WARN = "#fab219"
BAD = "#d03b3b"
INFO = ACCENT
WARN_TEXT = ("#8a5a00", "#f3c35a")       # шар өнгийн бичиг: цагаан дэвсгэр дээр тод шар уншигдахгүй
GOOD_SOFT, GOOD_TEXT = ("#e8f5e8", "#173018"), ("#0e7a0e", "#7bd87b")
WARN_SOFT = ("#fff3d6", "#3a2e12")
LEVEL_COLORS = {"ok": GOOD, "warn": WARN, "info": INFO}

# Дасгалын шатны шошго: (нэр, дэвсгэр, бичиг). Цайвар дэвсгэр дээр өнгөт бичиг.
PHASES = {
    "setup":     ("Бэлтгэл", WARN_SOFT, WARN_TEXT),
    "countdown": ("Эхлэх гэж байна", INSET, TEXT),
    "active":    ("Дасгал", GOOD_SOFT, GOOD_TEXT),
    "rest":      ("Амралт", INSET, TEXT),
    "done":      ("Дууссан", GOOD_SOFT, GOOD_TEXT),
}

# CustomTkinter-ийн «blue» сэдвийн оронд: тусгай өнгө өгөөгүй элемент бүр (гулсуур, унтраалга, цэс,
# гүйлгэх зурвас ...) эдгээрийг авна.
CTK_THEME = {
    "CTk": dict(fg_color=BG),
    "CTkToplevel": dict(fg_color=BG),
    "CTkFrame": dict(fg_color=CARD, top_fg_color=INSET, border_color=BORDER),
    "CTkButton": dict(fg_color=ACCENT, hover_color=ACCENT_HOVER, border_color=BORDER_STRONG, text_color=ON_ACCENT,
                      text_color_disabled=MUTED),
    "CTkLabel": dict(text_color=TEXT),
    # border_width=0: зам ба бөөрөнхий товч ижил өндөртэй, цагаан товч саарал/хар зам дээр тод харагдана
    "CTkSwitch": dict(border_width=0, fg_color=("#d6d6d6", "#4a4a4a"), progress_color=ACCENT,
                      button_color=("#ffffff", "#2b2b2b"), button_hover_color=("#f2f2f2", "#3a3a3a"),
                      text_color=TEXT, text_color_disabled=MUTED),
    "CTkSlider": dict(fg_color=("#e6e6e6", "#3a3a3a"), progress_color=ACCENT, button_color=ACCENT,
                      button_hover_color=ACCENT_HOVER),
    "CTkProgressBar": dict(fg_color=("#ededed", "#333333"), progress_color=ACCENT, border_color=BORDER),
    "CTkOptionMenu": dict(fg_color=INSET, button_color=("#ebebeb", "#333333"),
                          button_hover_color=("#e0e0e0", "#3d3d3d"), text_color=TEXT, text_color_disabled=MUTED),
    "CTkScrollbar": dict(button_color=("#e3e3e3", "#3a3a3a"), button_hover_color=("#cdcdcd", "#4a4a4a")),
    "CTkSegmentedButton": SEG,
    "DropdownMenu": dict(fg_color=CARD, hover_color=INSET, text_color=TEXT),
}


def apply_ctk_theme():
    """CTK_THEME-ийг CustomTkinter-ийн одоогийн сэдэвт бичнэ. Цонх үүсгэхээс өмнө дуудна.

    Зөвхөн сэдэвт байгаа түлхүүрийг солино: CustomTkinter 5.2 ба 6.0 хоёуланд ажиллана.
    """
    theme = ctk.ThemeManager.theme
    for widget, values in CTK_THEME.items():
        section = theme.get(widget)
        if not isinstance(section, dict):
            continue
        for key, value in values.items():
            if key in section:
                section[key] = list(value) if isinstance(value, tuple) else value


def mode_index():
    return 1 if ctk.get_appearance_mode() == "Dark" else 0


def pick(pair):
    """(цайвар, харанхуй) хосоос одоогийн горимын өнгийг сонгоно (tk.Canvas-д хэрэгтэй)."""
    return pair[mode_index()] if isinstance(pair, tuple) else pair


def font(size=14, weight="normal"):
    return ctk.CTkFont(size=size, weight=weight)


def font_family():
    """CTk-ийн сэдвийн фонт (Windows, Linux: Roboto; macOS: системийн фонт)."""
    try:
        return ctk.ThemeManager.theme["CTkFont"]["family"]
    except (AttributeError, KeyError, TypeError):
        return "TkDefaultFont"


def canvas_font(px, weight="normal"):
    """tk.Canvas дээрх текстийн фонт: бусад бичигтэй ижил хэлбэр, хэмжээг пикселээр (Tk-д сөрөг тоо)."""
    return (font_family(), -max(6, round(px)), weight)
