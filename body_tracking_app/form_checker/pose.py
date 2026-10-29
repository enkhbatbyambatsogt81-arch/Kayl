"""MediaPipe Pose Landmarker-ийг ороосон класс ба биеийн цэгийн өгөгдлийн бүтэц."""

from __future__ import annotations

import os
import shutil
import time
import urllib.request
from dataclasses import dataclass

import cv2
import numpy as np

# MediaPipe-ийн 33 цэгийн индекс (https://ai.google.dev/edge/mediapipe/solutions/vision/pose_landmarker)
NOSE = 0
L_SHOULDER, R_SHOULDER = 11, 12
L_ELBOW, R_ELBOW = 13, 14
L_WRIST, R_WRIST = 15, 16
L_HIP, R_HIP = 23, 24
L_KNEE, R_KNEE = 25, 26
L_ANKLE, R_ANKLE = 27, 28
L_HEEL, R_HEEL = 29, 30
L_FOOT, R_FOOT = 31, 32

SIDES = {
    "left": dict(shoulder=L_SHOULDER, elbow=L_ELBOW, wrist=L_WRIST, hip=L_HIP,
                 knee=L_KNEE, ankle=L_ANKLE, heel=L_HEEL, foot=L_FOOT),
    "right": dict(shoulder=R_SHOULDER, elbow=R_ELBOW, wrist=R_WRIST, hip=R_HIP,
                  knee=R_KNEE, ankle=R_ANKLE, heel=R_HEEL, foot=R_FOOT),
}

# Араг ясыг зурахад ашиглах холбоосууд (нүүрний жижиг цэгүүдийг алгасав)
SKELETON = [
    (11, 12), (11, 13), (13, 15), (12, 14), (14, 16),
    (11, 23), (12, 24), (23, 24),
    (23, 25), (25, 27), (27, 29), (29, 31), (27, 31),
    (24, 26), (26, 28), (28, 30), (30, 32), (28, 32),
]

MODEL_URL = ("https://storage.googleapis.com/mediapipe-models/pose_landmarker/"
             "pose_landmarker_{v}/float16/latest/pose_landmarker_{v}.task")
MODELS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models")


@dataclass
class Pose:
    """Нэг кадр дахь нэг хүний биеийн цэгүүд.

    img   : (33, 3) пикселийн x, y ба харьцангуй гүн z (пикселээр)
    world : (33, 3) метрээр, хонгоны төвөөс эхтэй 3D координат (байхгүй бол None)
    vis   : (33,)   цэг бүрийн харагдах магадлал 0..1
    """
    img: np.ndarray
    world: np.ndarray | None
    vis: np.ndarray
    width: int
    height: int


BODY_POINTS = (L_SHOULDER, R_SHOULDER, L_HIP, R_HIP, L_KNEE, R_KNEE, L_ANKLE, R_ANKLE)
FEET_POINTS = (L_ANKLE, R_ANKLE, L_HEEL, R_HEEL)


def framing_hint(pose: Pose, min_visibility=0.5, margin=0.01, min_size=0.0):
    """Хүн кадрт бүтэн багтаж байгаа эсэхийг шалгана.

    Бүтэн харагдаж байвал None, үгүй бол юу хийхийг хэлэх мессежийн түлхүүр буцаана:
    frame_side (хажуу тийш гарсан), frame_feet (хөл харагдахгүй), frame_head (толгой харагдахгүй),
    frame_closer (хэт хол, биеийн хэмжээ кадрын min_size хувиас бага).
    MediaPipe кадраас гарсан цэгийн байрлалыг ч таамагладаг тул координатаар нь чиглэлийг мэднэ.
    """
    w, h = pose.width, pose.height
    x, y = pose.img[:, 0], pose.img[:, 1]
    in_x = (x >= margin * w) & (x <= (1 - margin) * w)
    in_y = (y >= margin * h) & (y <= (1 - margin) * h)
    inside = (pose.vis >= min_visibility) & in_x & in_y

    if not in_x[list(BODY_POINTS)].all():
        return "frame_side"
    if not inside[list(FEET_POINTS)].any():
        return "frame_feet"
    if not inside[NOSE]:
        return "frame_head"
    if min_size > 0:
        pts = pose.img[list(BODY_POINTS) + [NOSE], :2]
        span = max(np.ptp(pts[:, 0]) / w, np.ptp(pts[:, 1]) / h)
        if span < min_size:
            return "frame_closer"
    return None


def _download(url, path):
    """macOS-ийн python.org Python зэрэгт системийн SSL гэрчилгээ дутуу байдаг тул certifi-г ашиглана
    (mediapipe-тэй хамт суудаг)."""
    context = None
    try:
        import ssl

        import certifi
        context = ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        pass
    with urllib.request.urlopen(url, context=context) as response, open(path, "wb") as f:
        shutil.copyfileobj(response, f)


def ensure_model(variant="lite"):
    """Загварын файл models/ хавтсанд байхгүй бол интернэтээс татна."""
    os.makedirs(MODELS_DIR, exist_ok=True)
    path = os.path.join(MODELS_DIR, f"pose_landmarker_{variant}.task")
    if not os.path.exists(path):
        url = MODEL_URL.format(v=variant)
        print(f"[model] {variant} загварыг татаж байна: {url}")
        _download(url, path + ".part")
        os.replace(path + ".part", path)
    return path


class PoseEstimator:
    """Видео урсгалд зориулсан MediaPipe PoseLandmarker (VIDEO горим)."""

    def __init__(self, variant="lite", min_detection=0.5, min_tracking=0.5):
        import mediapipe as mp
        from mediapipe.tasks.python import vision

        self._mp = mp
        # Замд кирилл үсэг эсвэл зай байвал (жишээ нь «Хүн компьютерын харилцаа») MediaPipe файлыг
        # Windows дээр нээж чаддаггүй. Тиймээс загварыг Python-оор уншаад санах ойгоор дамжуулна.
        with open(ensure_model(variant), "rb") as f:
            model = f.read()
        options = vision.PoseLandmarkerOptions(
            base_options=mp.tasks.BaseOptions(model_asset_buffer=model),
            running_mode=vision.RunningMode.VIDEO,
            num_poses=1,
            min_pose_detection_confidence=min_detection,
            min_pose_presence_confidence=min_detection,
            min_tracking_confidence=min_tracking,
        )
        self._landmarker = vision.PoseLandmarker.create_from_options(options)
        self._last_ts = -1
        self.last_latency_ms = 0.0

    def process(self, frame_bgr, timestamp_ms=None):
        """BGR кадр авч Pose (эсвэл хүн олдоогүй бол None) буцаана."""
        if timestamp_ms is None:
            timestamp_ms = int(time.perf_counter() * 1000)
        # VIDEO горим монотон өсөх timestamp шаарддаг
        timestamp_ms = max(int(timestamp_ms), self._last_ts + 1)
        self._last_ts = timestamp_ms

        h, w = frame_bgr.shape[:2]
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        image = self._mp.Image(image_format=self._mp.ImageFormat.SRGB, data=rgb)
        t0 = time.perf_counter()
        result = self._landmarker.detect_for_video(image, timestamp_ms)
        self.last_latency_ms = (time.perf_counter() - t0) * 1000.0

        if not result.pose_landmarks:
            return None
        lms = result.pose_landmarks[0]
        img = np.array([[p.x * w, p.y * h, p.z * w] for p in lms], dtype=float)
        vis = np.array([p.visibility if p.visibility is not None else 1.0 for p in lms], dtype=float)
        world = None
        if result.pose_world_landmarks:
            world = np.array([[p.x, p.y, p.z] for p in result.pose_world_landmarks[0]], dtype=float)
        return Pose(img=img, world=world, vis=vis, width=w, height=h)

    def close(self):
        self._landmarker.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
