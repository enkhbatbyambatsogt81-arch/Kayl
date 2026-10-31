"""Вэбкамераар дасгалын хэлбэрийг шалгах апп (squat, push-up)."""

import sys

__version__ = "2.2"


def safe_console():
    """Кирилл үсгийг бичиж чадахгүй гаралтад (Windows-д гаралтыг файл руу чиглүүлэх, ө ү-гүй cp1251 кодлол)
    print() алдаа өгч апп унахгүй, тэр үсгийг «?» болгоно."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="replace")
        except (AttributeError, ValueError):  # pythonw-д гаралт байхгүй (None)
            pass
