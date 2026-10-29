"""Кадр дээр араг яс, тоолуур, зөвлөмжийг зурах.

OpenCV-ийн putText кирилл үсэг дэмждэггүй тул монгол текстийг Pillow-оор зурна.
Кирилл фонт олдохгүй бол автоматаар англи текст рүү шилжинэ.
"""

from __future__ import annotations

import math
import os
import shutil
import subprocess

import cv2
import numpy as np

from .messages import EXERCISE_NAMES, STATE_NAMES, t
from .pose import SKELETON

FONT_CANDIDATES = [
    # Windows
    r"C:\Windows\Fonts\segoeui.ttf", r"C:\Windows\Fonts\arial.ttf", r"C:\Windows\Fonts\tahoma.ttf",
    # macOS
    "/System/Library/Fonts/Supplemental/Arial.ttf", "/Library/Fonts/Arial.ttf",
    "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
    # Linux (Ubuntu/Debian, Fedora, Arch)
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/dejavu-sans-fonts/DejaVuSans.ttf",
    "/usr/share/fonts/TTF/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
    "/usr/share/fonts/google-noto/NotoSans-Regular.ttf",
    "/usr/share/fonts/noto/NotoSans-Regular.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    "/usr/share/fonts/liberation-sans/LiberationSans-Regular.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
]
FONT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "fonts")

# BGR өнгө
GREEN, RED, ORANGE, WHITE, GRAY = (80, 200, 80), (60, 60, 230), (0, 165, 255), (255, 255, 255), (170, 170, 170)
BLUE = (230, 160, 60)
LEVEL_COLORS = {"ok": GREEN, "warn": ORANGE, "info": BLUE}

MAIN_JOINT = {"squat": "knee", "pushup": "elbow"}
# Гол үеийн хоёр хөрш (өнцгийн нум зурахад): squat - хонго, шагай; push-up - мөр, бугуй
ARC_NEIGHBORS = {"squat": ("hip", "ankle"), "pushup": ("shoulder", "wrist")}


def _fontconfig_font():
    """Linux-д дээрх замд фонт олдохгүй бол fontconfig-оос монгол (кирилл) үсэгтэй фонтыг асууна."""
    if not shutil.which("fc-match"):
        return None
    try:
        out = subprocess.run(["fc-match", "-f", "%{file}", "sans-serif:lang=mn"], capture_output=True,
                             text=True, timeout=3).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return None
    return out or None


def _is_font(path):
    return bool(path) and path.lower().endswith((".ttf", ".otf", ".ttc")) and os.path.exists(path)


def _find_font():
    local = [os.path.join(FONT_DIR, f) for f in sorted(os.listdir(FONT_DIR))] if os.path.isdir(FONT_DIR) else []
    for path in local + FONT_CANDIDATES:
        if _is_font(path):
            return path
    path = _fontconfig_font()
    return path if _is_font(path) else None


class Renderer:
    def __init__(self, lang="mn"):
        self.font_path = None
        self._fonts = {}
        self._mask_cache = {}
        self._width_cache = {}
        try:
            from PIL import Image, ImageDraw, ImageFont  # noqa: F401
            self._pil = (Image, ImageDraw, ImageFont)
            self.font_path = _find_font()
        except ImportError:
            self._pil = None
        if lang == "mn" and (self._pil is None or self.font_path is None):
            print("[ui] Кирилл фонт олдсонгүй, англи текст ашиглана.")
            lang = "en"
        self.lang = lang
        self._texts = []

    # ---- Текст -------------------------------------------------------------
    def _font(self, size):
        if size not in self._fonts:
            self._fonts[size] = self._pil[2].truetype(self.font_path, size)
        return self._fonts[size]

    def _glyph_mask(self, s, size):
        """Текстийн alpha маскыг нэг удаа зураад кэшлэнэ (дараагийн кадруудад дахин ашиглана)."""
        key = (s, size)
        cached = self._mask_cache.get(key)
        if cached is None:
            Image, ImageDraw, _ = self._pil
            font = self._font(size)
            left, top, right, bottom = font.getbbox(s)
            img = Image.new("L", (max(1, right - left), max(1, bottom - top)), 0)
            ImageDraw.Draw(img).text((-left, -top), s, font=font, fill=255)
            cached = (np.asarray(img, np.float32) / 255.0, (left, top))
            if len(self._mask_cache) > 2000:
                self._mask_cache.clear()
            self._mask_cache[key] = cached
        return cached

    def text(self, x, y, s, color=WHITE, size=22):
        """Текстийг дараалалд нэмнэ; flush() үед нэг дор зурна (хурдны үүднээс)."""
        self._texts.append((int(x), int(y), s, color, size))

    def _flush_texts(self, frame):
        if not self._texts:
            return frame
        if self.font_path and self._pil:
            fh, fw = frame.shape[:2]
            for x, y, s, color, size in self._texts:
                mask, (ox, oy) = self._glyph_mask(s, size)
                x0, y0 = x + ox, y + oy
                x1, y1 = x0 + mask.shape[1], y0 + mask.shape[0]
                cx0, cy0, cx1, cy1 = max(0, x0), max(0, y0), min(fw, x1), min(fh, y1)
                if cx1 <= cx0 or cy1 <= cy0:
                    continue
                a = mask[cy0 - y0:cy1 - y0, cx0 - x0:cx1 - x0, None]
                roi = frame[cy0:cy1, cx0:cx1].astype(np.float32)
                frame[cy0:cy1, cx0:cx1] = (roi * (1 - a) + np.array(color, np.float32) * a).astype(np.uint8)
        else:
            for x, y, s, color, size in self._texts:
                s = s.replace("°", " deg")
                cv2.putText(frame, s, (x, y + size), cv2.FONT_HERSHEY_SIMPLEX, size / 32, color, 2, cv2.LINE_AA)
        self._texts = []
        return frame

    # ---- Зурах ----------------------------------------------------------
    @staticmethod
    def _panel(frame, x0, y0, x1, y1, alpha=0.55):
        h, w = frame.shape[:2]
        x0, y0, x1, y1 = max(0, x0), max(0, y0), min(w, x1), min(h, y1)
        if x1 > x0 and y1 > y0:
            # cv2.convertScaleAbs нь numpy-гийн float үржвэрээс хэд дахин хурдан
            frame[y0:y1, x0:x1] = cv2.convertScaleAbs(frame[y0:y1, x0:x1], alpha=1 - alpha)

    def draw_skeleton(self, frame, pose, fb):
        if pose is None:
            return
        pts = pose.img[:, :2].astype(int)
        vis = pose.vis
        for a, b in SKELETON:
            if vis[a] > 0.5 and vis[b] > 0.5:
                cv2.line(frame, tuple(pts[a]), tuple(pts[b]), GRAY, 2, cv2.LINE_AA)
        for i in range(11, 33):
            if vis[i] > 0.5 and i not in fb.bad_joints:
                cv2.circle(frame, tuple(pts[i]), 5, GREEN, -1, cv2.LINE_AA)
        # Алдаатай үеийг хамгийн сүүлд, томоор зурна (бусад цэгт дарагдахгүй)
        for i in fb.bad_joints:
            cv2.circle(frame, tuple(pts[i]), 9, RED, -1, cv2.LINE_AA)
            cv2.circle(frame, tuple(pts[i]), 9, WHITE, 1, cv2.LINE_AA)

        # Гол үеийн өнцгийг үе дээр нь бичнэ
        if fb.main_angle is not None and fb.side is not None:
            from .pose import SIDES
            side = SIDES[fb.side]
            j = side[MAIN_JOINT[fb.exercise]]
            x, y = pts[j]
            if fb.view == "side":
                a, b = (side[k] for k in ARC_NEIGHBORS[fb.exercise])
                self.draw_angle_arc(frame, pts[j], pts[a], pts[b], GREEN if fb.state == "bottom" else WHITE)
            cv2.circle(frame, (int(x), int(y)), 10, WHITE, 2, cv2.LINE_AA)
            self.text(x + 16, y - 38, f"{fb.main_angle:.0f}°", WHITE, 26)

    @staticmethod
    def draw_angle_arc(frame, center, p1, p2, color, radius=38):
        """Үений өнцгийг нумаар харуулна (LearnOpenCV AI Fitness Trainer-ийн дүрслэлийн санаа).
        Доод цэгт хүрэхэд нум ногоон болно."""
        c = np.asarray(center, float)
        a1 = math.degrees(math.atan2(p1[1] - c[1], p1[0] - c[0]))
        a2 = math.degrees(math.atan2(p2[1] - c[1], p2[0] - c[0]))
        sweep = (a2 - a1) % 360
        if sweep > 180:
            a1, sweep = a2, 360 - sweep
        cv2.ellipse(frame, (int(c[0]), int(c[1])), (radius, radius), 0, a1, a1 + sweep, color, 3, cv2.LINE_AA)

    def draw_depth_bar(self, frame, fb, counter):
        """Баруун талд "хэр гүн суусан/буусан" -ыг харуулах багана (counter-ийн босгоор)."""
        if fb.main_angle is None:
            return
        h, w = frame.shape[:2]
        x0, x1, y0, y1 = w - 50, w - 25, int(h * 0.2), int(h * 0.75)
        angle = min(fb.main_angle, fb.metrics.get("depth_angle") or fb.main_angle)
        frac = (counter.top - angle) / (counter.top - counter.depth)
        frac = float(np.clip(frac, 0, 1.15))
        cv2.rectangle(frame, (x0, y0), (x1, y1), GRAY, 2)
        fill = int((y1 - y0) * min(frac, 1.0))
        color = GREEN if frac >= 1.0 else ORANGE
        cv2.rectangle(frame, (x0 + 3, y1 - fill), (x1 - 3, y1 - 3), color, -1)
        cv2.line(frame, (x0 - 6, y0), (x1 + 6, y0), GREEN, 2)  # зорилтот гүн

    def text_width(self, s, size):
        key = (s, size)
        if key not in self._width_cache:
            if self.font_path and self._pil:
                self._width_cache[key] = int(self._font(size).getlength(s))
            else:
                self._width_cache[key] = cv2.getTextSize(s, cv2.FONT_HERSHEY_SIMPLEX, size / 32, 2)[0][0]
        return self._width_cache[key]

    @staticmethod
    def draw_rep_dots(frame, x, y, reps, target, max_w, r=9):
        """Сетийн давталт бүрийг цэгээр: ногоон = зөв, улаан = алдаатай, саарал хүрээ = үлдсэн."""
        n = max(target, len(reps))
        if n == 0:
            return
        if target <= 0:          # чөлөөт горим: сүүлийн давталтууд
            reps = reps[-int(max_w // (2.6 * r)):]
            n = len(reps)
        step = min(2.6 * r, max_w / max(n, 1))
        rr = max(3, min(r, int(step / 2.6)))
        for i in range(n):
            c = (int(x + rr + i * step), int(y + rr))
            if i < len(reps):
                cv2.circle(frame, c, rr, GREEN if reps[i].correct else RED, -1, cv2.LINE_AA)
            else:
                cv2.circle(frame, c, rr, GRAY, 1, cv2.LINE_AA)

    def draw_hud(self, frame, wv, perf, show_help=True, sound_on=None):
        fb = wv.fb
        h, w = frame.shape[:2]
        lang = self.lang
        mn = lang == "mn"
        s = max(0.6, min(1.4, h / 720))  # дэлгэцийн хэмжээнд тааруулах

        self._draw_message_bar(frame, wv, s)
        if wv.phase == "done":
            return  # дүнгийн дэлгэц гол мэдээллийг харуулна

        # Зүүн дээд самбар
        pw = int(430 * s)
        self._panel(frame, 0, 0, pw, int(212 * s))
        self.text(12 * s, 8 * s, t(fb.exercise, lang, EXERCISE_NAMES), WHITE, int(26 * s))
        reps_txt = f"{len(wv.set_reps)}/{wv.target}" if wv.target > 0 else f"{wv.total_reps}"
        self.text(12 * s, 42 * s, f"{'Давталт' if mn else 'Reps'}: {reps_txt}", WHITE, int(34 * s))
        correct = sum(r.correct for r in wv.set_reps) if wv.target > 0 else wv.total_correct
        self.text(250 * s, 48 * s, f"{'Зөв' if mn else 'Correct'}: {correct}", GREEN, int(28 * s))
        state = t(fb.state, lang, STATE_NAMES)
        angle = f" | {fb.main_angle:.0f}°" if fb.main_angle is not None else ""
        set_txt = f"{'Сет' if mn else 'Set'} {wv.set_index}/{wv.sets_total}  |  " if wv.target > 0 else ""
        self.text(12 * s, 90 * s, f"{set_txt}{state}{angle}", GRAY, int(22 * s))
        self.draw_rep_dots(frame, 14 * s, 122 * s, wv.set_reps, wv.target, pw - 28 * s, r=int(9 * s))
        view = {"side": ("хажуугаас", "side"), "front": ("урдаас", "front")}.get(fb.view)
        if view:
            score = ""
            if wv.set_reps or fb.last_rep is not None:
                last = fb.last_rep or wv.set_reps[-1]
                score = f"   {'Сүүлийн оноо' if mn else 'Last score'}: {last.score}"
            self.text(12 * s, 150 * s, f"{'Харагдац' if mn else 'View'}: {view[0 if mn else 1]}{score}", GRAY,
                      int(20 * s))
        snd = ""
        if sound_on is not None:
            snd = (" | дуу: " + ("асаалттай" if sound_on else "унтраалттай")) if mn else \
                  (" | sound: " + ("on" if sound_on else "off"))
        self.text(12 * s, 178 * s, f"FPS {perf.get('fps', 0):.0f} | pose {perf.get('pose_ms', 0):.0f} ms{snd}",
                  GRAY, int(18 * s))

        if show_help:
            help_txt = ("1/2: дасгал  Space: алгасах  S: дуу  E: дуусгах  R: шинээр  Q: гарах" if mn
                        else "1/2: exercise  Space: skip  S: sound  E: finish  R: restart  Q: quit")
            size = int(18 * s)
            self._panel(frame, w - self.text_width(help_txt, size) - int(24 * s), 0, w, int(34 * s), alpha=0.45)
            self.text(w - self.text_width(help_txt, size) - 12 * s, 7 * s, help_txt, GRAY, size)

    def _draw_message_bar(self, frame, wv, s):
        """Доод зурвас: нэг удаад зөвхөн нэг, хамгийн чухал зөвлөмж."""
        h, w = frame.shape[:2]
        color = LEVEL_COLORS.get(wv.level, WHITE)
        bar_h = int(64 * s)
        self._panel(frame, 0, h - bar_h, w, h, alpha=0.65)
        cv2.rectangle(frame, (0, h - bar_h), (8, h), color, -1)
        msg = t(wv.message, self.lang)
        size = int(30 * s)
        # Нарийн (босоо) бичлэг дээр текст багтахгүй бол фонтыг багасгана
        while size > 12 and self.text_width(msg, size) > w - 34 * s:
            size -= 2
        self.text(22 * s, h - bar_h + (64 * s - size) / 2 - 2 * s, msg, color, size)

    # ---- Дасгалын шатуудын дэлгэц ------------------------------------------
    def draw_setup(self, frame, wv):
        """Эхлэх шат: кадрын хүрээ (улбар шар = бэлэн биш, ногоон = бэлэн) + барих явцын цагираг."""
        h, w = frame.shape[:2]
        ready = wv.message == "hold_position"
        cv2.rectangle(frame, (3, 3), (w - 4, h - 4), GREEN if ready else ORANGE, 6)
        if ready:
            c, r = (w // 2, int(h * 0.16)), int(min(w, h) * 0.06)
            cv2.circle(frame, c, r, GRAY, 3, cv2.LINE_AA)
            cv2.ellipse(frame, c, (r, r), -90, 0, 360 * wv.ready_progress, GREEN, 6, cv2.LINE_AA)

    def draw_countdown(self, frame, wv):
        h, w = frame.shape[:2]
        r = int(min(w, h) * 0.17)
        c = (w // 2, h // 2)
        # Зөвхөн тойргийн орчмыг бүдгэрүүлнэ (бүтэн кадрыг хуулахаас хурдан)
        x0, y0, x1, y1 = max(0, c[0] - r), max(0, c[1] - r), min(w, c[0] + r + 1), min(h, c[1] + r + 1)
        roi = frame[y0:y1, x0:x1]
        mask = np.zeros(roi.shape[:2], np.uint8)
        cv2.circle(mask, (c[0] - x0, c[1] - y0), r, 255, -1, cv2.LINE_AA)
        roi[:] = np.where(mask[..., None] > 0, cv2.convertScaleAbs(roi, alpha=0.5), roi)
        cv2.circle(frame, c, r, BLUE, 4, cv2.LINE_AA)
        size = int(r * 1.5)
        txt = str(wv.countdown)
        self.text(c[0] - self.text_width(txt, size) // 2, c[1] - int(size * 0.62), txt, WHITE, size)

    def _center_panel(self, frame, pw, ph):
        h, w = frame.shape[:2]
        x0, y0 = (w - pw) // 2, max(0, (h - ph) // 2 - int(h * 0.03))
        self._panel(frame, x0, y0, x0 + pw, y0 + ph, alpha=0.85)
        cv2.rectangle(frame, (x0, y0), (x0 + pw, y0 + ph), GRAY, 1)
        return x0, y0

    def draw_rest(self, frame, wv):
        h, w = frame.shape[:2]
        mn = self.lang == "mn"
        s = max(0.6, min(1.4, h / 720))
        x0, y0 = self._center_panel(frame, int(420 * s), int(250 * s))
        cx = x0 + int(210 * s)
        title = "Амралт" if mn else "Rest"
        self.text(cx - self.text_width(title, int(32 * s)) // 2, y0 + 16 * s, title, BLUE, int(32 * s))
        left = int(math.ceil(wv.rest_left or 0))
        clock = f"{left // 60}:{left % 60:02d}"
        self.text(cx - self.text_width(clock, int(90 * s)) // 2, y0 + 58 * s, clock, WHITE, int(90 * s))
        nxt = (f"Дараагийн сет: {wv.set_index + 1}/{wv.sets_total}" if mn
               else f"Next set: {wv.set_index + 1}/{wv.sets_total}")
        self.text(cx - self.text_width(nxt, int(24 * s)) // 2, y0 + 170 * s, nxt, GRAY, int(24 * s))
        hint = "Space: алгасах" if mn else "Space: skip"
        self.text(cx - self.text_width(hint, int(20 * s)) // 2, y0 + 208 * s, hint, GRAY, int(20 * s))

    def draw_summary(self, frame, summary, sets):
        """Дасгал дууссаны дараах дүнгийн дэлгэц."""
        h, w = frame.shape[:2]
        lang, mn = self.lang, self.lang == "mn"
        s = max(0.6, min(1.4, h / 720))
        n_issue = min(2, len(summary["issues"]))
        pw = int(min(w - 40, 760 * s))
        ph = int((128 + 34 * len(sets) + 44 + 32 + 32 * n_issue + 76) * s)
        x0, y0 = self._center_panel(frame, pw, ph)
        x, y = x0 + int(24 * s), y0 + int(16 * s)
        self.text(x, y, "Дасгалын дүн" if mn else "Workout summary", WHITE, int(36 * s))
        self.text(x, y + 48 * s, t(summary["exercise"], lang, EXERCISE_NAMES), GRAY, int(24 * s))
        acc = summary["accuracy"] * 100
        line = (f"Нийт давталт: {summary['reps']}   Зөв: {summary['correct']} ({acc:.0f}%)" if mn
                else f"Total reps: {summary['reps']}   Correct: {summary['correct']} ({acc:.0f}%)")
        self.text(x, y + 84 * s, line, GREEN if acc >= 80 else ORANGE, int(28 * s))
        yy = y + 128 * s
        for i, set_reps in enumerate(sets, 1):
            label = f"{'Сет' if mn else 'Set'} {i}:"
            self.text(x, yy, label, GRAY, int(22 * s))
            self.draw_rep_dots(frame, x + 90 * s, yy + 4 * s, set_reps, len(set_reps), pw - 140 * s, r=int(9 * s))
            yy += 34 * s
        dur = (f"Дундаж хугацаа: {summary['avg_duration']:.1f} с / давталт   Дундаж оноо: "
               f"{summary.get('avg_score', 0):.0f}" if mn
               else f"Average time: {summary['avg_duration']:.1f} s / rep   Average score: "
               f"{summary.get('avg_score', 0):.0f}")
        self.text(x, yy + 4 * s, dur, GRAY, int(22 * s))
        yy += 40 * s
        if summary["issues"]:
            self.text(x, yy, "Хамгийн их гарсан алдаа:" if mn else "Most common mistakes:", WHITE, int(22 * s))
            for key, n in summary["issues"][:n_issue]:
                yy += 32 * s
                times = f"{n} удаа" if mn else f"{n}x"
                self.text(x + 16 * s, yy, f"• {t(key, lang)}: {times}", ORANGE, int(21 * s))
        else:
            self.text(x, yy, "Алдаагүй! Маш сайн." if mn else "No mistakes. Excellent!", GREEN, int(22 * s))
        foot = "R: дахин эхлэх    Q: гарах" if mn else "R: restart    Q: quit"
        self.text(x, y0 + ph - 40 * s, foot, GRAY, int(20 * s))

    def render(self, frame, pose, wv, counter, perf, show_help=True, sound_on=None, summary=None, sets=None,
               hud=True):
        """hud=False үед зөвхөн видео дээрх зүйлсийг (араг яс, зөвлөмжийн мөр, тоолол, амралт) зурна;
        тоолуур, самбарыг цонхтой интерфейс (gui) өөрөө харуулна."""
        h = frame.shape[0]
        self.draw_skeleton(frame, pose, wv.fb)
        if hud and wv.phase != "done":
            self.draw_depth_bar(frame, wv.fb, counter)
        if wv.phase == "setup":
            self.draw_setup(frame, wv)
        if hud:
            self.draw_hud(frame, wv, perf, show_help, sound_on)
        else:
            self._draw_message_bar(frame, wv, max(0.6, min(1.4, h / 720)))
        # Төвийн цонхнууд HUD-ийн текстийн дээр гарах ёстой тул HUD-ийн текстийг эхлээд зурна
        frame = self._flush_texts(frame)
        if wv.phase == "countdown" and wv.countdown:
            self.draw_countdown(frame, wv)
        elif wv.phase == "rest":
            self.draw_rest(frame, wv)
        elif wv.phase == "done" and summary is not None:
            self.draw_summary(frame, summary, sets or [])
        return self._flush_texts(frame)
