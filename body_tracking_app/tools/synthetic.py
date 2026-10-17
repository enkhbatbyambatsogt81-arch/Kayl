"""Синтетик (зохиомол) биеийн цэгийн дараалал үүсгэгч.

Камергүйгээр логикийг шалгах зорилготой: энгийн кинематик загвараар
squat / push-up хөдөлгөөнийг 3D-ээр үүсгэж, камер руу проекцлоод
MediaPipe-тэй ижил формат (Pose) болгоно. Давталт бүрийн "жинхэнэ" шошгыг
(зөв эсэх, ямар алдаатай) мэдэж байгаа тул алгоритмын нарийвчлалыг тоогоор хэмжиж болно.
"""

from __future__ import annotations

import math
import os
import sys
from dataclasses import dataclass, field

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from form_checker.pose import Pose  # noqa: E402

# Биеийн сегментийн урт (метр)
SHANK, THIGH, TORSO, UPPER_ARM, FOREARM = 0.43, 0.45, 0.52, 0.30, 0.27
HIP_HALF, SHOULDER_HALF = 0.15, 0.19


@dataclass
class RepSpec:
    """Нэг давталтын тодорхойлолт ба жинхэнэ шошго."""
    min_angle: float                  # хамгийн бага өвдөг/тохойн өнцөг
    issues: list = field(default_factory=list)
    duration: float = 2.4             # сек
    pause: float = 0.6                # дараагийн давталтын өмнөх завсарлага
    top_angle: float = 175.0          # давталтын дараа хүрэх дээд өнцөг


def _angle_profile(reps, fps, start_pause=1.0, rng=None):
    """Давталтуудаас кадр бүрийн гол өнцгийн дараалал + давталт бүрийн индекс."""
    angles, rep_id = [], []
    top = 175.0
    angles += [top] * int(start_pause * fps)
    rep_id += [-1] * int(start_pause * fps)
    for i, r in enumerate(reps):
        n = max(8, int(r.duration * fps))
        for k in range(n):
            ph = k / (n - 1)
            # косинус профайл: дээд -> доод -> дээд
            prev_top = top
            a = r.min_angle + (prev_top - r.min_angle) * (0.5 + 0.5 * math.cos(2 * math.pi * ph))
            if ph > 0.5:
                a = r.min_angle + (r.top_angle - r.min_angle) * (0.5 - 0.5 * math.cos(2 * math.pi * (ph - 0.5)))
            angles.append(a)
            rep_id.append(i)
        top = r.top_angle
        m = int(r.pause * fps)
        angles += [top] * m
        rep_id += [-1] * m
    return np.array(angles), np.array(rep_id)


# ---------------------------------------------------------------------------
# Squat
# ---------------------------------------------------------------------------
def squat_skeleton(knee_angle, issues, depth_frac):
    """Биеийн координатаар (forward, up, lateral) 33 цэгийн 3D байрлал."""
    flex = 180.0 - knee_angle
    alpha = math.radians(0.38 * flex)           # шилбэ урагш хазайх
    beta = math.radians(0.62 * flex)            # гуя хойш хазайх
    lean_k = 0.95 if "squat_lean" in issues else 0.45
    gamma = math.radians(lean_k * math.degrees(beta) + 4)
    heel_lift = math.radians(22 * depth_frac) if "squat_heels" in issues else 0.0
    knee_in = 0.11 * depth_frac if "squat_knees_in" in issues else -0.03 * depth_frac

    P = np.zeros((33, 3))
    for s, sign in (("l", 1), ("r", -1)):
        lat = sign
        toe = np.array([0.16, 0.0])
        heel_rest = np.array([-0.07, 0.0])
        ankle_rest = np.array([0.0, 0.08])
        # өсгий өргөгдвөл хөлийг хурууны үзүүрээр эргүүлнэ
        c, sn = math.cos(-heel_lift), math.sin(-heel_lift)

        def rot(p):
            v = p - toe
            return toe + np.array([c * v[0] - sn * v[1], sn * v[0] + c * v[1]])
        heel, ankle = rot(heel_rest), rot(ankle_rest)
        knee = ankle + SHANK * np.array([math.sin(alpha), math.cos(alpha)])
        hip = knee + THIGH * np.array([-math.sin(beta), math.cos(beta)])
        shoulder = hip + TORSO * np.array([math.sin(gamma), math.cos(gamma)])
        elbow = shoulder + UPPER_ARM * np.array([0.9, -0.2])
        wrist = elbow + FOREARM * np.array([1.0, 0.0])
        lat_ankle, lat_knee = 0.17 * lat, (0.18 - knee_in) * lat
        idx = dict(l=(11, 13, 15, 23, 25, 27, 29, 31), r=(12, 14, 16, 24, 26, 28, 30, 32))[s]
        pts = [(shoulder, SHOULDER_HALF * lat), (elbow, (SHOULDER_HALF + 0.03) * lat),
               (wrist, (SHOULDER_HALF - 0.02) * lat), (hip, HIP_HALF * lat), (knee, lat_knee),
               (ankle, lat_ankle), (heel, lat_ankle), (toe, lat_ankle + 0.02 * lat)]
        for i, (fu, l) in zip(idx, pts):
            P[i] = [fu[0], fu[1], l]
    _head(P)
    return P


def _head(P):
    mid_sh = (P[11] + P[12]) / 2
    mid_hip = (P[23] + P[24]) / 2
    up = mid_sh - mid_hip
    up /= np.linalg.norm(up) + 1e-9
    nose = mid_sh + 0.25 * up
    nose[0] += 0.08
    for i in range(11):
        P[i] = nose + np.array([0.0, 0.02 * (i % 3), 0.02 * ((i % 2) * 2 - 1)])


# ---------------------------------------------------------------------------
# Push-up
# ---------------------------------------------------------------------------
def pushup_skeleton(elbow_angle, issues, depth_frac):
    E = math.radians(elbow_angle)
    d = math.sqrt(UPPER_ARM ** 2 + FOREARM ** 2 - 2 * UPPER_ARM * FOREARM * math.cos(E))
    ankle = np.array([0.0, 0.10])
    sh_y = d + 0.03
    body = THIGH + SHANK + TORSO
    sh_x = math.sqrt(max(body ** 2 - (sh_y - ankle[1]) ** 2, 0.1))
    shoulder = np.array([sh_x, sh_y])
    wrist = np.array([sh_x, 0.03])
    # тохой: мөр-бугуйн дунд цэгээс хойш (хөл рүү) гарна
    # гурвалжин: бугуйгаас мөр рүү чиглэлд a зайд, перпендикуляр h зайд
    dd = np.linalg.norm(shoulder - wrist)
    u = (shoulder - wrist) / dd
    a = (FOREARM ** 2 - UPPER_ARM ** 2 + dd ** 2) / (2 * dd)
    h = math.sqrt(max(FOREARM ** 2 - a ** 2, 0.0))
    elbow = wrist + a * u + h * np.array([-u[1], u[0]]) * (-1 if u[1] > 0 else 1)
    if elbow[0] > shoulder[0]:
        elbow = wrist + a * u - h * np.array([-u[1], u[0]]) * (-1 if u[1] > 0 else 1)
    line = shoulder - ankle
    hip = ankle + 0.55 * line
    normal = np.array([-line[1], line[0]]) / np.linalg.norm(line)  # "дээш" чиглэсэн
    offset = 0.0
    if "pushup_sag" in issues:
        offset = -0.10 - 0.05 * depth_frac
    elif "pushup_pike" in issues:
        offset = 0.16 + 0.04 * depth_frac
    hip = hip + offset * normal
    knee = (ankle + hip) / 2
    heel = ankle + np.array([-0.03, 0.05])
    toe = ankle + np.array([0.04, -0.09])

    P = np.zeros((33, 3))
    for s, lat in (("l", 1), ("r", -1)):
        idx = dict(l=(11, 13, 15, 23, 25, 27, 29, 31), r=(12, 14, 16, 24, 26, 28, 30, 32))[s]
        pts = [(shoulder, SHOULDER_HALF * lat), (elbow, (SHOULDER_HALF + 0.05) * lat),
               (wrist, (SHOULDER_HALF + 0.02) * lat), (hip, HIP_HALF * lat), (knee, 0.12 * lat),
               (ankle, 0.10 * lat), (heel, 0.10 * lat), (toe, 0.10 * lat)]
        for i, (fu, l) in zip(idx, pts):
            P[i] = [fu[0], fu[1], l]
    nose = shoulder + np.array([0.22, 0.05])
    for i in range(11):
        P[i] = [nose[0], nose[1], 0.02 * ((i % 2) * 2 - 1)]
    return P


# ---------------------------------------------------------------------------
# Камер
# ---------------------------------------------------------------------------
def project(P, view, width=1280, height=720, facing=1, noise_px=3.0, noise_world=None, rng=None):
    """Биеийн координатыг (forward, up, lateral) зураг + world координат руу хөрвүүлнэ."""
    rng = rng or np.random.default_rng()
    hip_mid = (P[23] + P[24]) / 2
    rel = P - hip_mid
    scale = height * 0.42  # пиксел / метр

    if view == "side":
        # forward -> зургийн x (facing = 1: баруун тийш), lateral -> гүн
        x = facing * rel[:, 0]
        z = -rel[:, 2] * facing
    else:
        # урдаас: lateral -> зургийн x (толин дүрс), forward -> камер руу (гүн сөрөг)
        x = -rel[:, 2]
        z = -rel[:, 0]
    y = -rel[:, 1]
    world = np.stack([x, y, z], axis=1)

    cx = width / 2
    base_y = height * 0.92 - hip_mid[1] * scale  # газар (up=0) зургийн доод хэсэгт
    img = np.stack([cx + x * scale, base_y + y * scale, z * scale], axis=1)
    img[:, :2] += rng.normal(0, noise_px, size=(33, 2))
    if noise_world is None:
        noise_world = noise_px / scale  # пикселийн шуугиантай ижил хэмжээний метр
    world += rng.normal(0, noise_world, size=(33, 3)) * np.array([1, 1, 2])

    vis = np.full(33, 0.97)
    if view == "side":
        # камераас хол талын мөчир хагас далдлагдана
        far = (12, 14, 16, 24, 26, 28, 30, 32) if facing == 1 else (11, 13, 15, 23, 25, 27, 29, 31)
        vis[list(far)] = 0.55
    return Pose(img=img, world=world, vis=vis, width=width, height=height)


def make_sequence(exercise, reps, view="side", fps=30, noise_px=3.0, outlier_rate=0.03,
                  dropout_rate=0.01, facing=1, seed=0, start_pause=1.0):
    """Бүтэн дараалал: [(t, Pose|None)], rep_id массив, давталтын тодорхойлолтууд."""
    rng = np.random.default_rng(seed)
    angles, rep_id = _angle_profile(reps, fps, start_pause)
    frames = []
    for k, (a, rid) in enumerate(zip(angles, rep_id)):
        issues = reps[rid].issues if rid >= 0 else []
        if exercise == "squat":
            depth_frac = float(np.clip((175 - a) / (175 - 90), 0, 1))
            P = squat_skeleton(a, issues, depth_frac)
        else:
            depth_frac = float(np.clip((175 - a) / (175 - 80), 0, 1))
            P = pushup_skeleton(a, issues, depth_frac)
        if rng.random() < dropout_rate:
            frames.append((k / fps, None))
            continue
        npx = noise_px * (5 if rng.random() < outlier_rate else 1)
        frames.append((k / fps, project(P, view, facing=facing, noise_px=npx, rng=rng)))
    return frames, rep_id
