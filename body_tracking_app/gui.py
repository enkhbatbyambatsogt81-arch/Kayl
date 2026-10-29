"""Цонхтой интерфейс: дасгал сонгох, тохиргоо, камер, дүн, түүх.

Ажиллуулах:  start_windows.bat (Windows), bash start.sh (macOS, Linux) эсвэл .venv-ийн Python-оор: python gui.py
(Командын мөрийн хувилбар: python main.py)
"""

import sys

from form_checker import safe_console

safe_console()
try:
    from form_checker.gui.app import run
except ImportError as e:  # customtkinter эсвэл tkinter суугаагүй
    print(f"Цонхтой интерфейсийг ачаалж чадсангүй: {e}\n"
          "Эхлүүлэх скриптийг (start_windows.bat эсвэл bash start.sh) дахин ажиллуулна уу, эсвэл терминалд:\n"
          "python -m pip install -r requirements.txt")
    sys.exit(1)

if __name__ == "__main__":
    run()
