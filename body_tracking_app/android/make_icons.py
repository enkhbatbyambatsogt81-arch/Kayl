"""Апп эхлүүлэгчийн дүрсийг (app/src/main/res/mipmap-*) зурна: хар дэвсгэр дээр суулт хийж буй цагаан дүрс.

Компьютерын хувилбарын дүрстэй ижил санаа. Дүрсийг өөрчлөх бол энд засаад дахин ажиллуулна (Pillow хэрэгтэй):
    python make_icons.py
"""

from pathlib import Path

from PIL import Image, ImageDraw

RES = Path(__file__).parent / "app/src/main/res"
BLACK = (17, 17, 17, 255)
WHITE = (255, 255, 255, 255)
FLOOR = (255, 255, 255, 110)
SS = 4   # ирмэгийг зөөлрүүлэхийн тулд 4 дахин томоор зураад жижигрүүлнэ

# 0..1 хэмжээст талбай дахь цэгүүд: толгой, мөр, гар, ташаа, өвдөг, шагай, хөл
HEAD, SHOULDER, HAND = (0.56, 0.17), (0.45, 0.32), (0.76, 0.34)
HIP, KNEE, ANKLE, TOE = (0.27, 0.55), (0.52, 0.66), (0.38, 0.85), (0.50, 0.85)


def figure(size):
    """size × size тунгалаг зураг дээр цагаан дүрс."""
    n = size * SS
    img = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    width = max(2, round(n * 0.075))

    def line(points, fill=WHITE, w=width):
        pts = [(x * n, y * n) for x, y in points]
        draw.line(pts, fill=fill, width=w, joint="curve")
        for x, y in pts:   # дугуй үзүүр, үе
            draw.ellipse([x - w / 2, y - w / 2, x + w / 2, y + w / 2], fill=fill)

    line([(0.14, 0.91), (0.86, 0.91)], FLOOR, max(1, width // 3))
    line([HAND, SHOULDER, HIP, KNEE, ANKLE, TOE])
    r = n * 0.085
    draw.ellipse([HEAD[0] * n - r, HEAD[1] * n - r, HEAD[0] * n + r, HEAD[1] * n + r], fill=WHITE)
    return img.resize((size, size), Image.LANCZOS)


def plate(size, shape):
    n = size * SS
    img = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    if shape == "round":
        draw.ellipse([0, 0, n - 1, n - 1], fill=BLACK)
    else:
        draw.rounded_rectangle([0, 0, n - 1, n - 1], radius=n // 5, fill=BLACK)
    return img.resize((size, size), Image.LANCZOS)


def main():
    for name, k in (("mdpi", 1), ("hdpi", 1.5), ("xhdpi", 2), ("xxhdpi", 3), ("xxxhdpi", 4)):
        folder = RES / f"mipmap-{name}"
        folder.mkdir(parents=True, exist_ok=True)
        size = round(48 * k)
        for fname, shape, part in (("ic_launcher.png", "square", 0.72), ("ic_launcher_round.png", "round", 0.62)):
            img = plate(size, shape)
            box = round(size * part)
            img.alpha_composite(figure(box), ((size - box) // 2, (size - box) // 2))
            img.save(folder / fname, optimize=True)
        # Android 8+: дэвсгэр өнгө (values/styles.xml) + урд дүрс. 108dp-ийн голын 66dp л заавал харагдана
        full, box = round(108 * k), round(56 * k)
        fg = Image.new("RGBA", (full, full), (0, 0, 0, 0))
        fg.alpha_composite(figure(box), ((full - box) // 2, (full - box) // 2))
        fg.save(folder / "ic_launcher_foreground.png", optimize=True)


if __name__ == "__main__":
    main()
