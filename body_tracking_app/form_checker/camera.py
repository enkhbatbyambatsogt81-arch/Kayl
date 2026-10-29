"""Вэбкамер нээх: үйлдлийн систем бүрт тохирох OpenCV backend, камер хайх, алдааны зөвлөгөө.

Windows, macOS, Linux камераа өөр өөр замаар нээдэг тул нэг backend бүтэлгүйтвэл дараагийнхыг
оролдоно. Зарим камер нээгдсэн ч эхний хэдэн кадрыг хоосон буцаадаг (macOS-д зөвшөөрөл өгсний дараа,
Windows-ийн Media Foundation) тул кадр уншигдтал хэсэг хүлээж шалгана.
"""

from __future__ import annotations

import sys
import time

import cv2

IS_WINDOWS = sys.platform.startswith("win")
IS_MAC = sys.platform == "darwin"

# Үйлдлийн системийн камерын backend-ууд, оролдох дарааллаар
BACKENDS = {
    "win": ("CAP_DSHOW", "CAP_MSMF"),   # DirectShow хурдан нээгддэг; болохгүй бол Media Foundation
    "mac": ("CAP_AVFOUNDATION",),
    "linux": ("CAP_V4L2",),
}


def platform_key():
    return "win" if IS_WINDOWS else "mac" if IS_MAC else "linux"


def backends():
    """Энэ системд оролдох backend-ийн жагсаалт; төгсгөлд нь OpenCV өөрөө сонгох CAP_ANY."""
    apis = [getattr(cv2, name) for name in BACKENDS[platform_key()] if hasattr(cv2, name)]
    return apis + [cv2.CAP_ANY]


def open_camera(index, width=None, height=None, warmup=2.0):
    """Камерыг нээж, кадр уншигдаж байгааг шалгана. Амжилттай бол VideoCapture, үгүй бол None."""
    for api in backends():
        cap = cv2.VideoCapture(int(index), api)
        if not cap.isOpened():
            cap.release()
            continue
        if width and height:
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        deadline = time.monotonic() + warmup
        while True:
            ok, frame = cap.read()
            if ok and frame is not None and frame.size:
                return cap
            if time.monotonic() >= deadline:
                break
            time.sleep(0.05)
        cap.release()
    return None


def find_cameras(max_index=5, warmup=1.0):
    """0..max_index-1 дугаартай камеруудаас кадр өгч байгааг нь буцаана (нүүр хуудасны «Камер хайх»)."""
    level = None
    try:  # байхгүй дугаарыг оролдоход OpenCV-ийн алдааны мөрүүд терминалыг дүүргэхгүй
        level = cv2.utils.logging.getLogLevel()
        cv2.utils.logging.setLogLevel(cv2.utils.logging.LOG_LEVEL_SILENT)
    except (AttributeError, cv2.error):
        pass
    try:
        found = []
        for index in range(max_index):
            cap = open_camera(index, warmup=warmup)
            if cap is not None:
                cap.release()
                found.append(index)
        return found
    finally:
        if level is not None:
            cv2.utils.logging.setLogLevel(level)


CAMERA_HELP = {
    "win": "Zoom, Teams зэрэг камер ашиглаж буй програмыг хаана уу. Windows-ийн Settings → Privacy & security → "
           "Camera хэсэгт «Let desktop apps access your camera»-г асаана.",
    "mac": "System Settings → Privacy & Security → Camera хэсэгт Terminal (эсвэл VS Code)-ийг зөвшөөрөөд "
           "програмаа дахин эхлүүлнэ. FaceTime, Zoom зэрэг камер ашиглаж буй програмыг хаана.",
    "linux": "Камер холбогдсон эсэхийг «ls /dev/video*» командаар шалгана. Эрх хүрэхгүй бол "
             "«sudo usermod -aG video $USER» ажиллуулаад дахин нэвтэрнэ.",
}


def camera_help():
    """Камер нээгдэхгүй үед энэ үйлдлийн системд юу шалгахыг хэлэх зөвлөгөө."""
    return CAMERA_HELP[platform_key()]
