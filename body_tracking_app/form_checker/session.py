"""Дасгалын сешний статистик: давталт бүрийн үр дүн, хурдны хэмжилт, CSV лог."""

from __future__ import annotations

import csv
import os
import time
import numpy as np

from .messages import EXERCISE_NAMES, t


class PerfMeter:
    """Кадр бүрийн хугацааг хэмжиж FPS ба latency-г тооцоолно."""

    def __init__(self, window=30):
        self.window = window
        self.frame_times = []
        self.pose_ms = []
        self.total_ms = []
        self._last = None

    def tick(self, pose_ms, total_ms):
        now = time.perf_counter()
        if self._last is not None:
            self.frame_times.append(now - self._last)
        self._last = now
        self.pose_ms.append(pose_ms)
        self.total_ms.append(total_ms)

    def current(self):
        ft = self.frame_times[-self.window:]
        fps = len(ft) / sum(ft) if ft and sum(ft) > 0 else 0.0
        pm = self.pose_ms[-self.window:]
        return {"fps": fps, "pose_ms": float(np.mean(pm)) if pm else 0.0}

    def summary(self):
        if not self.pose_ms:
            return {}
        ft = np.array(self.frame_times) if self.frame_times else np.array([np.nan])
        return {
            "frames": len(self.pose_ms),
            "fps_mean": float(1.0 / np.nanmean(ft)),
            "pose_ms_mean": float(np.mean(self.pose_ms)),
            "pose_ms_p95": float(np.percentile(self.pose_ms, 95)),
            "total_ms_mean": float(np.mean(self.total_ms)),
        }


def print_summary(workouts, perf: PerfMeter, lang="mn"):
    mn = lang == "mn"
    print("\n========== " + ("Дасгалын дүн" if mn else "Session summary") + " ==========")
    for w in workouts:
        s = w.summary()
        if not s["reps"]:
            continue
        acc = s["accuracy"] * 100
        print(f"{t(w.name, lang, EXERCISE_NAMES)}: {s['reps']} давталт, зөв {s['correct']} ({acc:.0f}%), "
              f"дундаж оноо {s['avg_score']:.0f}, дундаж {s['avg_duration']:.1f} с/давталт"
              if mn else f"{w.name}: {s['reps']} reps, {s['correct']} correct ({acc:.0f}%), "
              f"average score {s['avg_score']:.0f}, {s['avg_duration']:.1f} s/rep")
        if len(s["sets"]) > 1:
            for i, (n, c) in enumerate(s["sets"], 1):
                print(f"   Сет {i}: {n} давталт, {c} зөв" if mn else f"   Set {i}: {n} reps, {c} correct")
        for key, n in s["issues"] + s["warnings"]:
            print(f"   - {t(key, lang)}: {n}")
    s = perf.summary()
    if s:
        print(f"Хурд: дундаж {s['fps_mean']:.1f} FPS, pose {s['pose_ms_mean']:.1f} ms "
              f"(p95 {s['pose_ms_p95']:.1f} ms), нийт боловсруулалт {s['total_ms_mean']:.1f} ms/кадр")


# Аппын хавтас доторх logs/ (програмыг аль хавтаснаас ажиллуулсан ч нэг газар хадгална)
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")


def save_csv(workouts, folder=LOG_DIR):
    rows = [(w.name, set_i, rep_i, r.correct, ";".join(r.issues), round(r.min_angle, 1), round(r.duration, 2),
             r.score, ";".join(r.warnings), getattr(w.analyzer, "level", "normal"))
            for w in workouts for set_i, reps in enumerate(w.sets, 1) for rep_i, r in enumerate(reps, 1)]
    if not rows:
        return None
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, time.strftime("session_%Y%m%d_%H%M%S.csv"))
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        # 2.0: score, warnings, level баганууд нэмэгдсэн (хуучин логуудыг history.py уншсаар байна)
        w.writerow(["exercise", "set", "rep", "correct", "issues", "min_angle_deg", "duration_s", "score",
                    "warnings", "level"])
        w.writerows(rows)
    return path
