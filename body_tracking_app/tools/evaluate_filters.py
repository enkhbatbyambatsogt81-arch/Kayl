"""Өнцгийн шүүлтүүрүүдийг (1.x: медиан + EMA, 2.0: медиан + 1€) синтетик өгөгдөл дээр харьцуулна.

Ажиллуулах:  python tools/evaluate_filters.py [--sequences 20] [--json out.json]

Синтетик дарааллын "жинхэнэ" өнцгийг мэддэг тул шүүсэн өнцгийг түүнтэй харьцуулж:
  * RMSE      - жинхэнэ өнцгөөс дундаж квадрат хазайлт (°);
  * хоцрогдол - шүүсэн дохиог хэдэн мс хойш шилжүүлэхэд жинхэнэтэй хамгийн сайн таарах вэ;
  * чичиргээ  - хүн хөдөлгөөнгүй байх үеийн кадр хоорондын дундаж өөрчлөлт (°/кадр);
  * гүний алдаа - давталт бүрт бүртгэсэн хамгийн бага өнцөг (RepResult.min_angle) жинхэнээсээ хэр зөрөх вэ (°).
    Шүүлтүүр доод цэгийг "тайрвал" гүн суусан давталтыг гүехэн гэж буруу дүгнэнэ. 2.0-д тоолол 1€-оор,
    харин гүний үнэлгээ 1.x-ийн хурдан шүүлтүүрээр явдаг тул энэ үзүүлэлт хоёр хувилбарт ойролцоо.
-ийг тооцоолно. Зөвхөн хажуугийн харагдацыг ашиглана (урдаас харахад өнцгийг шууд биш, сегментийн
богинолтоос тооцдог тул жинхэнэ өнцөгтэй шууд харьцуулах боломжгүй).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import replace

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from form_checker.config import CommonConfig  # noqa: E402
from form_checker.exercises import create_analyzer  # noqa: E402
from tools.synthetic import RepSpec, _angle_profile, make_sequence  # noqa: E402

FPS = 30
FILTERS = {
    "1.x: медиан(5) + EMA(0.5)": dict(filter_kind="ema", median_window=5, smoothing_alpha=0.5),
    "2.0: медиан(5) + 1€": dict(filter_kind="one_euro", median_window=5),
    "медиан(5) + 1€ (beta 0.05)": dict(filter_kind="one_euro", median_window=5, one_euro_min_cutoff=1.0,
                                       one_euro_beta=0.05),
    "медиан(3) + 1€": dict(filter_kind="one_euro", median_window=3),
    "зөвхөн 1€ (медиангүй)": dict(filter_kind="one_euro", median_window=1),
    "зөвхөн EMA(0.5)": dict(filter_kind="ema", median_window=1, smoothing_alpha=0.5),
}


def random_reps(exercise, rng, n):
    lo, hi = (65, 115) if exercise == "squat" else (62, 105)
    return [RepSpec(rng.uniform(lo, hi), [], duration=rng.uniform(1.2, 3.0), pause=rng.uniform(0.4, 1.2))
            for _ in range(n)]


def run_filter(exercise, frames, common):
    analyzer = create_analyzer(exercise, common=common)
    out = []
    for t, pose in frames:
        fb = analyzer.update(pose, t)
        out.append(np.nan if fb.main_angle is None else fb.main_angle)
    return np.array(out, float), analyzer.reps


def metrics(est, truth, rep_id, reps=None):
    ok = ~np.isnan(est)
    err = est[ok] - truth[ok]
    rmse = float(np.sqrt(np.mean(err ** 2)))
    # Хоцрогдол: est[t] ≈ truth[t - k] байх k
    best_k, best = 0, np.inf
    for k in range(0, 11):
        e, tr = est[k:], truth[:len(truth) - k]
        m = ~np.isnan(e)
        v = float(np.mean((e[m] - tr[m]) ** 2))
        if v < best:
            best_k, best = k, v
    # Чичиргээ: жинхэнэ өнцөг тогтмол байх кадрууд (давталтын хоорондох завсарлага)
    still = (np.abs(np.diff(truth)) < 1e-9) & ok[1:] & ok[:-1]
    jitter = float(np.mean(np.abs(np.diff(est))[still])) if still.any() else float("nan")
    # Давталт бүрийн доод цэг: тоо таарсан үед бүртгэсэн min_angle-ийг жинхэнэтэй харьцуулна
    depth_err = []
    ids = sorted(set(rep_id.tolist()) - {-1})
    if reps is not None and len(reps) == len(ids):
        for r, rep in zip(ids, reps):
            depth_err.append(float(rep.min_angle - truth[rep_id == r].min()))
    return {"rmse": rmse, "lag_ms": best_k * 1000.0 / FPS, "jitter": jitter,
            "depth_err": float(np.mean(np.abs(depth_err))) if depth_err else float("nan"),
            "depth_bias": float(np.mean(depth_err)) if depth_err else float("nan")}


def evaluate(n_sequences=20, noises=(2, 5, 10), seed=0):
    results = {}
    for noise in noises:
        for exercise in ("squat", "pushup"):
            rng = np.random.default_rng(seed)
            acc = {name: [] for name in FILTERS}
            for _ in range(n_sequences):
                reps = random_reps(exercise, rng, int(rng.integers(4, 8)))
                frames, rep_id = make_sequence(exercise, reps, view="side", noise_px=noise,
                                               facing=int(rng.choice([-1, 1])), seed=int(rng.integers(1 << 30)))
                truth, _ = _angle_profile(reps, FPS, 1.0)
                for name, kw in FILTERS.items():
                    est, reps_found = run_filter(exercise, frames, replace(CommonConfig(), **kw))
                    acc[name].append(metrics(est, truth, rep_id, reps_found))
            results[f"{exercise}/{noise}px"] = {
                name: {k: float(np.nanmean([m[k] for m in ms])) for k in ms[0]} for name, ms in acc.items()}
    return results


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sequences", type=int, default=20)
    ap.add_argument("--noise", type=float, nargs="+", default=[2, 5, 10])
    ap.add_argument("--json")
    args = ap.parse_args()
    res = evaluate(args.sequences, args.noise)
    for key, rows in res.items():
        print(f"\n=== {key} ===")
        print(f"{'шүүлтүүр':28s} {'RMSE°':>7s} {'хоцр.мс':>8s} {'чичир.°':>8s} {'гүн±°':>7s} {'гүн.хазай°':>10s}")
        for name, m in rows.items():
            print(f"{name:28s} {m['rmse']:7.2f} {m['lag_ms']:8.0f} {m['jitter']:8.3f} {m['depth_err']:7.2f} "
                  f"{m['depth_bias']:10.2f}")
    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(res, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
