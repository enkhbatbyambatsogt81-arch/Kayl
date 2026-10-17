"""Цонхтой интерфейс: дасгал сонгох, тохиргоо, камер, дүн, түүх.

Ажиллуулах:  python gui.py
(Командын мөрийн хувилбар: python main.py)
"""

import sys

try:
    from form_checker.gui.app import run
except ImportError as e:  # customtkinter эсвэл tkinter суугаагүй
    print(f"Цонхтой интерфейсийг ачаалж чадсангүй: {e}\n"
          "Терминалд: python -m pip install -r requirements.txt  гэж ажиллуулаад дахин оролдоно уу.")
    sys.exit(1)

if __name__ == "__main__":
    run()
