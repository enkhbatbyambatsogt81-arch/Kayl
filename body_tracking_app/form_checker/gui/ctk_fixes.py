"""CustomTkinter-ийн нэг алдааны нөхөөс: нуусан элемент хэмжээ солигдоход дахин гарч ирэх.

CustomTkinter элемент бүрийн сүүлийн grid() дуудлагыг санаж, томруулалт өөрчлөгдөхөд (зүүн цэсний «Хэмжээ»,
Windows-д өөр томруулалттай дэлгэц рүү цонхоо чирэх) түүнийгээ дахин дууддаг. Харин grid_remove()-ийг
тооцдоггүй тул нуусан хуудас, товчлуур гэнэт гарч ирээд бусадтайгаа давхацдаг. Энд grid_remove хийхэд тэр
дуудлагыг мартуулж, хоосон grid()-ээр буцааж гаргахад өмнөх байрлалыг нь шинэ хэмжээнд тааруулж хэрэглэнэ.
"""

from __future__ import annotations

import tkinter

import customtkinter as ctk


def _last_grid_kwargs(widget):
    last = getattr(widget, "_last_geometry_manager_call", None)
    if last and getattr(last.get("function"), "__name__", "") in ("grid", "grid_configure"):
        return dict(last.get("kwargs") or {})
    return None


def apply():
    base = getattr(ctk, "CTkBaseClass", None)
    if base is None or getattr(base, "_grid_remove_fixed", False):
        return
    original_grid = base.grid

    def grid_remove(self):
        kwargs = _last_grid_kwargs(self)
        if kwargs:
            self._removed_grid_kwargs = kwargs
        self._last_geometry_manager_call = None   # томруулалт солигдоход дахин байрлуулахгүй
        tkinter.Grid.grid_remove(self)

    def grid(self, **kwargs):
        if kwargs:
            self._removed_grid_kwargs = None
        else:  # tkinter-т хоосон grid() = өмнөх байрлалаараа дахин харагдах
            kwargs = getattr(self, "_removed_grid_kwargs", None) or _last_grid_kwargs(self) or {}
        return original_grid(self, **kwargs)

    grid.__doc__ = original_grid.__doc__
    base.grid_remove = grid_remove
    base.grid = grid
    base._grid_remove_fixed = True
