"""Davtlagiin club системийн use case диаграмыг SVG болгон үүсгэнэ.

Ажиллуулах: python3 generate_svg.py  ->  use_case.svg
"""
from pathlib import Path

W, H = 1600, 1200
FONT = "DejaVu Sans, Liberation Sans, Arial, sans-serif"

# Бүлэг бүрийн өнгө: (хүрээ, дэвсгэр, use case дүүргэлт)
STUDENT = ("#2f6fb3", "#f2f7fd", "#dcebfb")
CONTENT = ("#2e8b57", "#f1faf4", "#d6f0df")
ADMIN = ("#c0711b", "#fdf6ee", "#fbe3c7")
SECURITY = ("#b23b3b", "#fdf2f2", "#f8d7d7")
COMMON = ("#555f6d", "#f6f7f9", "#e4e8ee")
LINE = "#3d4a5c"

out = []


def add(s):
    out.append(s)


def text(x, y, s, size=14, anchor="middle", weight="normal", color="#1c2733", italic=False):
    style = ' font-style="italic"' if italic else ""
    add(f'<text x="{x}" y="{y}" font-size="{size}" text-anchor="{anchor}" '
        f'font-weight="{weight}" fill="{color}"{style}>{s}</text>')


def group(x, y, w, h, title, colors):
    stroke, bg, _ = colors
    add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="12" fill="{bg}" '
        f'stroke="{stroke}" stroke-width="1.5" stroke-dasharray="6 4"/>')
    text(x + 14, y + 24, title, size=15, anchor="start", weight="bold", color=stroke)


def usecase(cx, cy, rx, ry, code, lines, colors, extra=None):
    stroke, _, fill = colors
    add(f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" fill="{fill}" '
        f'stroke="{stroke}" stroke-width="1.6"/>')
    n = len(lines) + 1 + (1 if extra else 0)
    y0 = cy - (n - 1) * 9 + 5
    text(cx, y0, code, size=12, weight="bold", color=stroke)
    for i, ln in enumerate(lines):
        text(cx, y0 + 18 * (i + 1), ln, size=14)
    if extra:
        add(f'<line x1="{cx - rx + 25}" y1="{y0 + 18 * len(lines) + 6}" '
            f'x2="{cx + rx - 25}" y2="{y0 + 18 * len(lines) + 6}" stroke="{stroke}" stroke-width="0.8"/>')
        text(cx, y0 + 18 * (len(lines) + 1) + 2, extra, size=11, color="#4a5563", italic=True)


def actor(cx, cy, name_mn, name_en, abstract=False, color=LINE):
    # cy = толгойн төв
    dash = ' stroke-dasharray="4 3"' if abstract else ""
    add(f'<g stroke="{color}" stroke-width="2.2" fill="none"{dash}>'
        f'<circle cx="{cx}" cy="{cy}" r="13" fill="#ffffff"/>'
        f'<line x1="{cx}" y1="{cy + 13}" x2="{cx}" y2="{cy + 48}"/>'
        f'<line x1="{cx - 22}" y1="{cy + 25}" x2="{cx + 22}" y2="{cy + 25}"/>'
        f'<line x1="{cx}" y1="{cy + 48}" x2="{cx - 18}" y2="{cy + 75}"/>'
        f'<line x1="{cx}" y1="{cy + 48}" x2="{cx + 18}" y2="{cy + 75}"/></g>')
    y = cy + 95
    if abstract:
        text(cx, cy - 22, "«abstract»", size=12, italic=True, color="#4a5563")
    text(cx, y, name_mn, size=15, weight="bold", italic=abstract)
    text(cx, y + 18, name_en, size=12, color="#4a5563", italic=abstract)


def assoc(d):
    add(f'<path d="{d}" fill="none" stroke="{LINE}" stroke-width="1.6"/>')


def dashed(d, label=None, lx=0, ly=0, color=LINE, anchor="middle"):
    add(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="1.5" '
        f'stroke-dasharray="7 5" marker-end="url(#open)"/>')
    if label:
        text(lx, ly, label, size=12, color=color, anchor=anchor)


def generalize(x1, y1, x2, y2):
    add(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{LINE}" '
        f'stroke-width="1.6" marker-end="url(#tri)"/>')


add(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
    f'font-family="{FONT}">')
add('<defs>'
    f'<marker id="open" viewBox="0 0 12 12" refX="11" refY="6" markerWidth="11" markerHeight="11" orient="auto">'
    f'<path d="M1,1 L11,6 L1,11" fill="none" stroke="{LINE}" stroke-width="1.5"/></marker>'
    f'<marker id="tri" viewBox="0 0 16 16" refX="15" refY="8" markerWidth="16" markerHeight="16" orient="auto">'
    f'<path d="M1,1 L15,8 L1,15 Z" fill="#ffffff" stroke="{LINE}" stroke-width="1.5"/></marker>'
    '</defs>')
add(f'<rect width="{W}" height="{H}" fill="#ffffff"/>')

text(W / 2, 40, "Davtlagiin club — Use Case диаграм", size=24, weight="bold")

# Системийн хил
add(f'<rect x="190" y="70" width="1050" height="940" rx="6" fill="none" stroke="{LINE}" stroke-width="2"/>')
text(715, 98, "Davtlagiin club систем", size=17, weight="bold", color=LINE)

# --- Нийтлэг: нэвтрэх ---
usecase(720, 145, 115, 30, "UC-01", ["Нэвтрэх"], COMMON)

# --- ① Оюутны суралцах ---
group(215, 190, 470, 600, "① Суралцах (Оюутан)", STUDENT)
usecase(450, 255, 165, 29, "UC-02", ["Хичээлд элсэх"], STUDENT)
usecase(450, 330, 165, 29, "UC-03", ["Нийтэлсэн агуулга үзэх"], STUDENT)
usecase(450, 405, 165, 29, "UC-06", ["Өөрийн ахиц үзэх"], STUDENT)
usecase(450, 480, 165, 29, "UC-04", ["Давтах төлөвлөгөө удирдах"], STUDENT)
usecase(450, 585, 195, 46, "UC-05", ["Дадлагын сорил ажиллах"], STUDENT,
        extra="extension point: Сорилын багц сонгох")
usecase(335, 728, 108, 36, "UC-14", ["Алдсан асуултаа", "давтах"], STUDENT)
usecase(572, 728, 108, 36, "UC-13", ["Хариултын", "тайлбар үзэх"], STUDENT)
dashed("M 340 692 L 392 633", "«extend» ¹", 330, 660, anchor="end")
dashed("M 508 633 L 556 692", "«include» ²", 545, 655, anchor="start")

# --- Нийтлэг: алдааны мэдээлэл ---
usecase(810, 700, 100, 40, "UC-09", ["Агуулгын алдаа", "шийдвэрлэх"], COMMON)

# --- ④ Удирдлага ---
group(935, 190, 280, 110, "④ Удирдлага (Админ)", ADMIN)
usecase(1075, 260, 120, 28, "UC-11", ["Бүртгэл, эрх удирдах"], ADMIN)

# --- ③ Агуулгын ажил ---
group(935, 320, 280, 470, "③ Агуулга (Багш, Хянагч)", CONTENT)
usecase(1075, 400, 125, 30, "UC-07", ["Төсөл бэлтгэж илгээх"], CONTENT)
usecase(1075, 480, 125, 30, "UC-10", ["Нэгтгэсэн тайлан үзэх"], CONTENT)
usecase(1075, 620, 125, 30, "UC-08", ["Агуулгыг хянаж нийтлэх"], CONTENT)

# --- ⑤ Хандалтын хяналт ---
group(215, 850, 1000, 140, "⑤ Хандалтын хяналт", SECURITY)
usecase(450, 930, 150, 32, "UC-12", ["Хандалтын эрх шалгах"], SECURITY)
dashed("M 450 790 L 450 896", "«include»", 460, 830, color=SECURITY[0], anchor="start")
dashed("M 1000 790 L 590 912", "«include»", 820, 840, color=SECURITY[0], anchor="start")
add(f'<rect x="650" y="895" width="550" height="82" rx="6" fill="#fffbe6" stroke="#d4b84a"/>')
text(665, 918, "UC-12-ыг бүх хамгаалагдсан үйлдэл (UC-02 … UC-11, UC-13, UC-14)", size=13, anchor="start")
text(665, 938, "«include» хийнэ: үйлдэл бүрийн өмнө хэрэглэгчийн эрхийг шалгана.", size=13, anchor="start")
text(665, 962, "Зураг ойлгомжтой байхын тулд сум бүрийг тусад нь зураагүй.", size=12,
     anchor="start", italic=True, color="#6b5d1f")

# --- Акторууд ---
actor(95, 400, "Оюутан", "Student")
actor(1500, 95, "Агуулгын ажилтан", "ContentStaff", abstract=True)
actor(1335, 200, "Админ", "Administrator")
actor(1335, 360, "Багш", "Teacher")
actor(1335, 560, "Хянагч", "Reviewer")

# Оюутан
assoc("M 122 435 L 285 255")
assoc("M 122 440 L 285 330")
assoc("M 122 445 L 285 405")
assoc("M 122 450 L 285 480")
assoc("M 122 458 L 255 585")
assoc("M 95 385 C 100 160 380 140 605 145")                # -> UC-01
assoc("M 110 495 C 140 880 600 880 722 718")               # -> UC-09
# Агуулгын ажилтан (Багш, Хянагч хоёул өвлөнө) -> UC-01
assoc("M 1475 135 C 1300 70 1000 110 835 140")
# Админ
assoc("M 1310 230 C 1200 150 1000 150 832 152")            # -> UC-01
assoc("M 1310 240 L 1195 260")                              # -> UC-11
# Багш
assoc("M 1310 390 L 1200 400")
assoc("M 1310 400 L 1200 480")
# Хянагч
assoc("M 1310 590 L 1200 620")
assoc("M 1310 600 C 1150 700 1000 710 910 700")            # -> UC-09
# Удамшил
generalize(1362, 385, 1480, 228)
generalize(1362, 585, 1500, 228)

# --- Тайлбар ---
add(f'<rect x="40" y="1030" width="1520" height="150" rx="8" fill="#fafbfc" stroke="#c9d1db"/>')
text(60, 1058, "Тэмдэглэгээ", size=15, anchor="start", weight="bold")
assoc("M 60 1085 L 120 1085")
text(132, 1090, "Актор тухайн үйлдлийг гүйцэтгэнэ", size=13, anchor="start")
dashed("M 430 1085 L 490 1085")
text(502, 1090, "«include» — үргэлж хамт гүйцэтгэгдэнэ", size=13, anchor="start")
dashed("M 830 1085 L 890 1085")
text(902, 1090, "«extend» — нөхцөл биелсэн үед нэмэгдэнэ", size=13, anchor="start")
generalize(1230, 1085, 1290, 1085)
text(1302, 1090, "Удамшил (төрөлжүүлэлт)", size=13, anchor="start")
text(60, 1125, "¹ UC-14 нь UC-05-ыг өргөтгөнө: оюутанд өмнө нь буруу хариулсан асуулт байгаа "
     "БӨГӨӨД тэр давтахыг сонгосон үед.", size=13, anchor="start")
text(60, 1147, "² UC-13: сорилын хариуг илгээсний (SUBMITTED) дараа тайлбар харагдана.",
     size=13, anchor="start")
text(60, 1169, "Багш, Хянагч нь хийсвэр «Агуулгын ажилтан»-ы төрөл тул түүний холбоосыг (UC-01) "
     "өвлөнө. Тасархай хүрээтэй дүрс = хийсвэр актор.", size=13, anchor="start")

add("</svg>")

Path(__file__).with_name("use_case.svg").write_text("\n".join(out), encoding="utf-8")
print("use_case.svg үүслээ")
