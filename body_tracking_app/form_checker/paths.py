"""Аппын файлууд хаана байрлахыг нэг газар тодорхойлно.

- RES_DIR: загвар, дуу, фонт зэрэг аппын дагалдах файлууд (зөвхөн уншина).
- DATA_DIR: тохиргоо (settings.json) ба дасгалын түүх (logs/) хадгалагдах хавтас.

Эх кодоос ажиллуулахад хоёулаа аппын хавтас. Татаж авсан бэлэн файлаас (PyInstaller) ажиллуулахад
дагалдах файлууд багц дотроос уншигдаж, тохиргоо ба түүх хэрэглэгчийн хавтсанд хадгалагдана:
Windows: %APPDATA%\\UkhaalagDasgaljuulagch, macOS: ~/Library/Application Support/UkhaalagDasgaljuulagch,
Linux: ~/.local/share/UkhaalagDasgaljuulagch.
"""

from __future__ import annotations

import os
import sys

APP_ID = "UkhaalagDasgaljuulagch"
FROZEN = bool(getattr(sys, "frozen", False))
SOURCE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def user_data_dir(platform=sys.platform, env=os.environ, home=None) -> str:
    home = home or os.path.expanduser("~")
    if platform.startswith("win"):
        base = env.get("APPDATA") or os.path.join(home, "AppData", "Roaming")
    elif platform == "darwin":
        base = os.path.join(home, "Library", "Application Support")
    else:
        base = env.get("XDG_DATA_HOME") or os.path.join(home, ".local", "share")
    return os.path.join(base, APP_ID)


RES_DIR = getattr(sys, "_MEIPASS", SOURCE_DIR) if FROZEN else SOURCE_DIR
DATA_DIR = user_data_dir() if FROZEN else SOURCE_DIR
