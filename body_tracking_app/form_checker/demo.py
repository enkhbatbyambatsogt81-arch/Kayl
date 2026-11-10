"""Демо (камергүй үзүүлэн)-ийн хөдөлгөөний дараалал: зөв ба алдаатай давталт холилдсон синтетик хүн.

Компьютерын хувилбар (engine.DemoSource) ба утасны хувилбар (mobile.MobileSession) хоёул үүнийг ашиглана.
OpenCV шаардахгүй.
"""

from __future__ import annotations

# (хамгийн бага өнцөг, алдаа[, дээд өнцөг[, хугацаа с]])
DEMO_SCRIPTS = {
    "squat": [(85, []), (82, []), (120, ["squat_shallow"]), (85, []), (82, ["squat_lean"]), (85, [], 175, 1.0),
              (84, ["squat_heels"]), (85, []), (85, ["squat_not_up"], 138), (84, [])],
    "pushup": [(80, []), (80, ["pushup_sag"]), (82, []), (115, ["pushup_shallow"]), (80, []),
               (80, ["pushup_pike"]), (82, []), (80, [])],
}

DEMO_LIFT = 0.12   # кадрын өндрийн хувь
DEMO_FLOOR = 0.92  # синтетик газар кадрын өндрийн хэдэн хувьд байдаг (tools/synthetic.project)


def demo_frames(exercise, seed=0, rounds=4):
    """[(t, Pose)] жагсаалт: 30 кадр/сек, эхэндээ 5 секунд зогсоно (бэлтгэл, 3-2-1 тоолол)."""
    from tools.synthetic import RepSpec, make_sequence  # зөвхөн демод хэрэгтэй

    reps = []
    for _ in range(rounds):
        for item in DEMO_SCRIPTS[exercise]:
            top = item[2] if len(item) > 2 else 175.0
            duration = item[3] if len(item) > 3 else 2.2   # 1.0 с = хэт хурдан (2.0-ийн сануулга)
            reps.append(RepSpec(item[0], list(item[1]), duration=duration, pause=0.9, top_angle=top))
    frames, _ = make_sequence(exercise, reps, view="side", noise_px=1.5, outlier_rate=0.0,
                              dropout_rate=0.0, seed=seed, start_pause=5.0)
    # Синтетик газар кадрын 92%-д байдаг; доод мессежийн мөрөнд дарагдахгүйн тулд дээш зөөнө.
    for _, pose in frames:
        pose.img[:, 1] -= DEMO_LIFT * pose.height
    return frames
