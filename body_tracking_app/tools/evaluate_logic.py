"""Давталт тоолох ба алдаа илрүүлэх логикийн нарийвчлалыг синтетик өгөгдөл дээр хэмжинэ.

Ажиллуулах:  python tools/evaluate_logic.py [--sequences 40] [--json out.json]

Шуугианы түвшин бүрээр (пикселээр) олон санамсаргүй дараалал үүсгэж:
  * давталтын тоо зөв таарсан эсэх
  * давталт бүрийг "зөв / алдаатай" гэж зөв ангилсан эсэх
  * алдааны төрөл бүрийн precision / recall
-ийг тооцоолно.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from form_checker.exercises import create_analyzer  # noqa: E402
from tools.synthetic import RepSpec, make_sequence  # noqa: E402

SCENARIOS = {
    # (дасгал, харагдац): боломжит алдаанууд
    ("squat", "side"): ["squat_lean", "squat_heels"],
    ("squat", "front"): ["squat_knees_in", "squat_lean"],
    ("pushup", "side"): ["pushup_sag", "pushup_pike"],
}
GOOD_RANGE = {"squat": (65, 95), "pushup": (62, 85)}
SHALLOW_RANGE = {"squat": (108, 135), "pushup": (100, 124)}
# Урдаас харахад 130°-аас бага нугалалтыг л давталт гэж тооцдог (config.front_attempt_angle)
SHALLOW_RANGE_FRONT = (108, 125)


def random_reps(exercise, view, rng, n_reps):
    reps = []
    for _ in range(n_reps):
        r = rng.random()
        kw = dict(duration=rng.uniform(1.4, 3.5), pause=rng.uniform(0.2, 1.2))
        after_not_up = bool(reps) and reps[-1].issues[:1] == [f"{exercise}_not_up"]
        if after_not_up and 0.45 <= r < 0.68:
            # Бүрэн босоогүй давталтын дараах гүехэн давталт нь бодит байдалд тусдаа давталт
            # гэж ялгагдахгүй (өмнөх дээд цэгээс доош бууж чадахгүй) тул зөв давталтаар солино.
            r = 0.0
        if r < 0.45:
            reps.append(RepSpec(rng.uniform(*GOOD_RANGE[exercise]), [], **kw))
        elif r < 0.6:
            lo, hi = SHALLOW_RANGE_FRONT if view == "front" else SHALLOW_RANGE[exercise]
            reps.append(RepSpec(rng.uniform(lo, hi), [f"{exercise}_shallow"], **kw))
        elif r < 0.68:
            reps.append(RepSpec(rng.uniform(*GOOD_RANGE[exercise]), [f"{exercise}_not_up"],
                                top_angle=rng.uniform(128, 142), **kw))
        else:
            issue = rng.choice(SCENARIOS[(exercise, view)])
            reps.append(RepSpec(rng.uniform(*GOOD_RANGE[exercise]), [str(issue)], **kw))
    # "бүрэн босоогүй" давталтын дараа заавал нэг давталт байх ёстой (дараагийн доошлох хөдөлгөөн)
    if reps[-1].issues and reps[-1].issues[0].endswith("not_up"):
        reps.append(RepSpec(rng.uniform(*GOOD_RANGE[exercise]), []))
    return reps


def evaluate(noise_px, n_sequences, seed=0):
    rng = np.random.default_rng(seed)
    stats = defaultdict(lambda: defaultdict(float))
    for (exercise, view) in SCENARIOS:
        key = f"{exercise}/{view}"
        s = stats[key]
        issue_tp, issue_fp, issue_fn = defaultdict(int), defaultdict(int), defaultdict(int)
        for k in range(n_sequences):
            reps = random_reps(exercise, view, rng, int(rng.integers(5, 11)))
            frames, _ = make_sequence(exercise, reps, view=view, noise_px=noise_px,
                                      facing=int(rng.choice([-1, 1])), seed=int(rng.integers(1 << 30)))
            analyzer = create_analyzer(exercise)
            for t, pose in frames:
                analyzer.update(pose, t)
            got = analyzer.reps
            s["sequences"] += 1
            s["true_reps"] += len(reps)
            s["counted_reps"] += len(got)
            s["exact_count"] += int(len(got) == len(reps))
            s["abs_count_error"] += abs(len(got) - len(reps))
            if len(got) != len(reps):
                continue
            for truth, pred in zip(reps, got):
                s["matched"] += 1
                s["correct_class"] += int((not truth.issues) == pred.correct)
                tset, pset = set(truth.issues), set(pred.issues)
                for i in tset | pset:
                    if i in tset and i in pset:
                        issue_tp[i] += 1
                    elif i in pset:
                        issue_fp[i] += 1
                    else:
                        issue_fn[i] += 1
        s["issues"] = {i: {"precision": issue_tp[i] / max(1, issue_tp[i] + issue_fp[i]),
                           "recall": issue_tp[i] / max(1, issue_tp[i] + issue_fn[i]),
                           "support": issue_tp[i] + issue_fn[i]}
                       for i in sorted(set(issue_tp) | set(issue_fp) | set(issue_fn))}
    out = {}
    for key, s in stats.items():
        out[key] = {
            "sequences": int(s["sequences"]),
            "true_reps": int(s["true_reps"]),
            "counted_reps": int(s["counted_reps"]),
            "count_exact_rate": s["exact_count"] / s["sequences"],
            "mean_abs_count_error": s["abs_count_error"] / s["sequences"],
            "classification_accuracy": s["correct_class"] / max(1, s["matched"]),
            "issues": s["issues"],
        }
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sequences", type=int, default=40)
    ap.add_argument("--noise", type=float, nargs="+", default=[2, 5, 10])
    ap.add_argument("--json")
    args = ap.parse_args()

    results = {}
    for noise in args.noise:
        res = evaluate(noise, args.sequences)
        results[str(noise)] = res
        print(f"\n=== Шуугиан σ = {noise} px (1280x720 кадр) ===")
        for key, r in res.items():
            print(f"{key:14s} давталт {r['counted_reps']}/{r['true_reps']}, "
                  f"тоо яг таарсан {r['count_exact_rate']*100:.0f}%, "
                  f"ангилал зөв {r['classification_accuracy']*100:.1f}%")
            for issue, m in r["issues"].items():
                print(f"    {issue:16s} precision {m['precision']:.2f}  recall {m['recall']:.2f}  (n={m['support']})")
    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
