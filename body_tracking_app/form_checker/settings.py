"""Цонхтой интерфейсийн тохиргоог (сүүлд сонгосон дасгал, давталт, сет ...) хадгалах."""

from __future__ import annotations

import json
import os

SETTINGS_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "settings.json")

DEFAULTS = {
    "exercise": "squat",
    "reps": 10,
    "sets": 3,
    "rest": 60,
    "free_mode": False,
    "sound": True,
    "model": "lite",
    "source": "camera",      # camera / video / demo
    "camera_index": 0,
    "video_path": "",
    "mirror": True,
    "appearance": "dark",    # dark / light / system
    "onboarded": False,      # анх нээхэд гарах танилцуулгыг үзсэн эсэх
    "level": "normal",       # шалгуурын түвшин: easy / normal / strict (2.0)
    "auto_detect": True,     # дасгалыг биеийн байрлалаар автоматаар таних (2.0)
    "ui_scale": 1.0,         # цонхны элементүүдийн хэмжээ (2.1): 1.0 = 100%
}


# Сонголттой утгууд ба тоон хязгаар (гараар засварласан эсвэл гэмтсэн файлаас хамгаална)
CHOICES = {
    "exercise": ("squat", "pushup"),
    "model": ("lite", "full"),          # GUI-д эдгээр хоёр л байна
    "source": ("camera", "video", "demo"),
    "appearance": ("dark", "light", "system"),
    "level": ("easy", "normal", "strict"),
}
RANGES = {"reps": (1, 50), "sets": (1, 10), "rest": (0, 600), "camera_index": (0, 9), "ui_scale": (0.7, 2.5)}


def _valid(key, value):
    default = DEFAULTS[key]
    if isinstance(default, bool) or isinstance(value, bool):
        return isinstance(value, bool) and isinstance(default, bool)
    if isinstance(default, float) and isinstance(value, int):
        value = float(value)  # JSON-д 1.0-ийг 1 гэж бичсэн байж болно
    if not isinstance(value, type(default)):
        return False
    if key in CHOICES:
        return value in CHOICES[key]
    if key in RANGES:
        lo, hi = RANGES[key]
        return lo <= value <= hi
    return True


def load_settings(path=SETTINGS_PATH):
    data = dict(DEFAULTS)
    try:
        with open(path, encoding="utf-8") as f:
            saved = json.load(f)
        if isinstance(saved, dict):
            # Мэдэгдэх түлхүүр, зөв төрөл, зөвшөөрөгдсөн утгыг л авна
            for k, v in saved.items():
                if k in DEFAULTS and _valid(k, v):
                    data[k] = float(v) if isinstance(DEFAULTS[k], float) else v
    except (OSError, ValueError):
        pass
    return data


def save_settings(data, path=SETTINGS_PATH):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump({k: data[k] for k in DEFAULTS if k in data}, f, ensure_ascii=False, indent=2)
        return True
    except OSError:
        return False
