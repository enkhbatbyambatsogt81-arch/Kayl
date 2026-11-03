"""Бэлэн файл зөв угсрагдсан эсэхийг цонх нээлгүйгээр шалгах: python gui.py --self-test

Загвар, дуу, MediaPipe, OpenCV, цонхны сан бүгд ачаалагдаж байвал 0, үгүй бол 1 буцаана.
GitHub Actions-д Windows, macOS, Linux файл бүрийг угсарсны дараа ажиллуулж шалгана.
"""

from __future__ import annotations

import os
import sys
import traceback


def run_self_test(out=None) -> int:
    out = out or sys.stdout
    log_path = os.environ.get("SELFTEST_LOG")  # Windows-ийн цонхтой exe-д stdout байхгүй тул файлд бичнэ

    def say(text):
        if out is not None:
            print(text, file=out, flush=True)
        if log_path:
            with open(log_path, "w", encoding="utf-8") as f:
                f.write(text + "\n")

    try:
        import cv2
        import numpy as np

        from . import __version__
        from .paths import DATA_DIR, FROZEN, RES_DIR
        from .pose import MODELS_DIR, PoseEstimator

        for variant in ("lite", "full"):
            path = os.path.join(MODELS_DIR, f"pose_landmarker_{variant}.task")
            if not os.path.exists(path):
                raise FileNotFoundError(path)
        sounds = [f for f in os.listdir(os.path.join(RES_DIR, "sounds")) if f.endswith(".wav")]
        if not sounds:
            raise FileNotFoundError(os.path.join(RES_DIR, "sounds"))
        with PoseEstimator("lite") as est:
            est.process(np.zeros((240, 320, 3), np.uint8), 0)

        import customtkinter  # noqa: F401  (цонх нээхгүй, зөвхөн сан ачаалагдаж буйг шалгана)
        import tkinter  # noqa: F401

        from tools.synthetic import squat_skeleton  # noqa: F401  (демо горим)

        say(f"OK: v{__version__}, OpenCV {cv2.__version__}, frozen={FROZEN}, "
            f"res={RES_DIR}, data={DATA_DIR}, sounds={len(sounds)}")
        return 0
    except Exception:  # noqa: BLE001
        say("FAIL\n" + traceback.format_exc())
        return 1
