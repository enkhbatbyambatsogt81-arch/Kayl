"""Аппын хурд (performance)-ыг хэмжих хэрэгсэл.

Жишээ:
    python benchmark.py --source 0 --frames 300               # вэбкамераар 300 кадр
    python benchmark.py --source squat.mp4 --models lite full # бичлэг дээр загваруудыг харьцуулах
    python benchmark.py --images photos/                      # зураг бүр дээр (IMAGE горим)

Хэмжих зүйлс: кадр унших, pose загвар, дасгалын логик, зурах хугацаа (ms),
нийт FPS, хүн илэрсэн кадрын хувь.
"""

import argparse
import glob
import json
import os
import platform
import time

import cv2
import numpy as np

from form_checker.config import WorkoutConfig
from form_checker.exercises import create_analyzer
from form_checker.pose import PoseEstimator, ensure_model
from form_checker.ui import Renderer
from form_checker.workout import Workout


def stats(ms):
    a = np.asarray(ms, float)
    if a.size == 0:
        return {}
    return {"mean": float(a.mean()), "median": float(np.median(a)), "p95": float(np.percentile(a, 95))}


def bench_stream(source, model, frames, exercise, width, height):
    cap = cv2.VideoCapture(int(source)) if str(source).isdigit() else cv2.VideoCapture(source)
    if str(source).isdigit():
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    fps_src = cap.get(cv2.CAP_PROP_FPS) or 30.0
    # Камерын горимтой адил: эхлэх шат, тоолол, сетийн логик бүгд ажиллана
    workout = Workout(create_analyzer(exercise), WorkoutConfig())
    renderer = Renderer("mn")
    t_read, t_pose, t_logic, t_draw, t_total = [], [], [], [], []
    detected = n = 0
    size = None
    with PoseEstimator(model) as est:
        start = time.perf_counter()
        while n < frames:
            t0 = time.perf_counter()
            ok, frame = cap.read()
            if not ok:
                break
            t1 = time.perf_counter()
            pose = est.process(frame, int(n / fps_src * 1000))
            t2 = time.perf_counter()
            wv = workout.update(pose, n / fps_src)
            t3 = time.perf_counter()
            renderer.render(frame, pose, wv, workout.analyzer.counter, {"fps": 0, "pose_ms": 0}, sound_on=True)
            t4 = time.perf_counter()
            size = frame.shape[1], frame.shape[0]
            if n > 0:  # эхний кадр загвар ачаалах хугацааг агуулдаг тул тооцохгүй
                t_read.append((t1 - t0) * 1000)
                t_pose.append((t2 - t1) * 1000)
                t_logic.append((t3 - t2) * 1000)
                t_draw.append((t4 - t3) * 1000)
                t_total.append((t4 - t0) * 1000)
            detected += pose is not None
            n += 1
        wall = time.perf_counter() - start
    cap.release()
    proc = np.array(t_total) - np.array(t_read) if t_total else np.array([np.nan])
    return {
        "mode": "stream", "source": str(source), "model": model, "frames": n, "resolution": size,
        "detection_rate": detected / max(n, 1),
        "read_ms": stats(t_read), "pose_ms": stats(t_pose), "logic_ms": stats(t_logic),
        "draw_ms": stats(t_draw), "total_ms": stats(t_total),
        "processing_fps": float(1000 / np.mean(proc)),
        "wall_fps": n / wall if wall > 0 else 0.0,
    }


def bench_images(folder, model):
    import mediapipe as mp
    from mediapipe.tasks.python import vision

    paths = sorted(p for ext in ("jpg", "jpeg", "png", "bmp", "webp")
                   for p in glob.glob(os.path.join(folder, "**", f"*.{ext}"), recursive=True))
    opts = vision.PoseLandmarkerOptions(
        base_options=mp.tasks.BaseOptions(model_asset_path=ensure_model(model)),
        running_mode=vision.RunningMode.IMAGE, num_poses=1)
    lat, detected, used = [], 0, 0
    with vision.PoseLandmarker.create_from_options(opts) as lm:
        for i, path in enumerate(paths):
            img = cv2.imread(path)
            if img is None:
                continue
            used += 1
            image = mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
            t0 = time.perf_counter()
            res = lm.detect(image)
            if i > 0:
                lat.append((time.perf_counter() - t0) * 1000)
            detected += bool(res.pose_landmarks)
    return {"mode": "images", "folder": folder, "model": model, "images": used,
            "detection_rate": detected / max(used, 1), "pose_ms": stats(lat)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", help="камерын дугаар эсвэл видео файл")
    ap.add_argument("--images", help="зурагнуудтай хавтас")
    ap.add_argument("--models", nargs="+", default=["lite"], choices=["lite", "full", "heavy"])
    ap.add_argument("--frames", type=int, default=300)
    ap.add_argument("--exercise", default="squat", choices=["squat", "pushup"])
    ap.add_argument("--width", type=int, default=1280)
    ap.add_argument("--height", type=int, default=720)
    ap.add_argument("--json", help="үр дүнг JSON файлд хадгалах")
    args = ap.parse_args()
    if not args.source and not args.images:
        args.source = "0"

    print(f"Машин: {platform.processor() or platform.machine()} | {platform.system()} {platform.release()} | "
          f"CPU цөм {os.cpu_count()}")
    results = []
    for model in args.models:
        if args.images:
            r = bench_images(args.images, model)
            print(f"[{model:5s}] {r['images']} зураг, хүн илэрсэн {r['detection_rate']*100:.1f}%, "
                  f"pose дундаж {r['pose_ms']['mean']:.1f} ms (p95 {r['pose_ms']['p95']:.1f})")
        else:
            r = bench_stream(args.source, model, args.frames, args.exercise, args.width, args.height)
            print(f"[{model:5s}] {r['frames']} кадр {r['resolution']}, илэрсэн {r['detection_rate']*100:.0f}% | "
                  f"pose {r['pose_ms']['mean']:.1f} ms (p95 {r['pose_ms']['p95']:.1f}), "
                  f"логик {r['logic_ms']['mean']:.2f} ms, зурах {r['draw_ms']['mean']:.1f} ms | "
                  f"боловсруулалтын FPS {r['processing_fps']:.0f}, бодит FPS {r['wall_fps']:.0f}")
        results.append(r)
    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
