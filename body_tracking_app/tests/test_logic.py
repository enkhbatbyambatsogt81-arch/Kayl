"""Логикийн автомат тест. Ажиллуулах:  python -m unittest discover -s tests -v"""

import os
import sys
import unittest

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from form_checker.exercises import create_analyzer  # noqa: E402
from form_checker.exercises.base import RepCounter  # noqa: E402
from form_checker.geometry import angle_3pt, angle_from_horizontal, angle_from_vertical  # noqa: E402
from tools.synthetic import RepSpec, make_sequence  # noqa: E402


def run(exercise, reps, view="side", **kw):
    frames, _ = make_sequence(exercise, reps, view=view, **kw)
    analyzer = create_analyzer(exercise)
    feedback = [analyzer.update(pose, t) for t, pose in frames]
    return analyzer, feedback


class GeometryTest(unittest.TestCase):
    def test_right_angle(self):
        self.assertAlmostEqual(angle_3pt((1, 0), (0, 0), (0, 1)), 90.0, places=5)

    def test_straight_line(self):
        self.assertAlmostEqual(angle_3pt((0, 0), (1, 1), (2, 2)), 180.0, places=5)

    def test_3d_angle(self):
        self.assertAlmostEqual(angle_3pt((1, 0, 0), (0, 0, 0), (0, 0, 1)), 90.0, places=5)

    def test_vertical_and_horizontal(self):
        # зургийн y доошоо: (0,0) -> (0,-1) бол яг дээш
        self.assertAlmostEqual(angle_from_vertical((0, 0), (0, -1)), 0.0, places=5)
        self.assertAlmostEqual(angle_from_vertical((0, 0), (1, -1)), 45.0, places=5)
        self.assertAlmostEqual(angle_from_horizontal((0, 0), (5, 0)), 0.0, places=5)


class RepCounterTest(unittest.TestCase):
    def feed(self, angles):
        c = RepCounter(top=160, start=150, depth=100, attempt=140, rebound_rise=30, rebound_drop=15)
        done = []
        for i, a in enumerate(angles):
            r = c.update(a, i / 30)
            if r:
                done.append(r)
        return done

    def test_full_rep(self):
        seq = list(np.linspace(175, 80, 30)) + list(np.linspace(80, 175, 30))
        done = self.feed(seq)
        self.assertEqual(len(done), 1)
        self.assertTrue(done[0]["depth_ok"])

    def test_shallow_rep(self):
        seq = list(np.linspace(175, 120, 30)) + list(np.linspace(120, 175, 30))
        done = self.feed(seq)
        self.assertEqual(len(done), 1)
        self.assertFalse(done[0]["depth_ok"])

    def test_tiny_bend_is_not_a_rep(self):
        seq = list(np.linspace(175, 145, 20)) + list(np.linspace(145, 175, 20))
        self.assertEqual(self.feed(seq), [])

    def test_must_start_from_top(self):
        # Эхлэхдээ доод байрлалд байсан бол эхний өндийлтийг давталт гэж тоолохгүй
        seq = [90] * 10 + list(np.linspace(90, 175, 30))
        self.assertEqual(self.feed(seq), [])

    def test_bounce_without_full_extension(self):
        seq = (list(np.linspace(175, 80, 30)) + list(np.linspace(80, 135, 20))
               + list(np.linspace(135, 80, 20)) + list(np.linspace(80, 175, 30)))
        done = self.feed(seq)
        self.assertEqual(len(done), 2)
        self.assertFalse(done[0]["full_extension"])
        self.assertTrue(done[1]["full_extension"])


class SquatTest(unittest.TestCase):
    def test_side_view(self):
        reps = [RepSpec(85), RepSpec(80), RepSpec(120, ["squat_shallow"]), RepSpec(85, ["squat_lean"]),
                RepSpec(85, ["squat_heels"]), RepSpec(85, ["squat_not_up"], top_angle=138), RepSpec(85)]
        for facing in (1, -1):
            a, _ = run("squat", reps, "side", facing=facing, seed=1)
            self.assertEqual([r.issues for r in a.reps], [r.issues for r in reps])

    def test_front_view(self):
        reps = [RepSpec(85), RepSpec(120, ["squat_shallow"]), RepSpec(85, ["squat_knees_in"])]
        a, fb = run("squat", reps, "front", seed=2)
        self.assertEqual([r.issues for r in a.reps], [r.issues for r in reps])
        self.assertTrue(any(f.view == "front" for f in fb))

    def test_counts_correct_reps(self):
        a, _ = run("squat", [RepSpec(85)] * 5, "side", seed=3)
        self.assertEqual((len(a.reps), a.correct_reps), (5, 5))


class PushupTest(unittest.TestCase):
    def test_side_view(self):
        reps = [RepSpec(80), RepSpec(115, ["pushup_shallow"]), RepSpec(80, ["pushup_sag"]),
                RepSpec(80, ["pushup_pike"]), RepSpec(80, ["pushup_not_up"], top_angle=135), RepSpec(80)]
        a, _ = run("pushup", reps, "side", seed=4)
        self.assertEqual([r.issues for r in a.reps], [r.issues for r in reps])

    def test_front_view_asks_to_turn(self):
        _, fb = run("pushup", [RepSpec(80)], "front", seed=5)
        self.assertIn("turn_side", {f.message for f in fb})


class RobustnessTest(unittest.TestCase):
    def test_missing_person(self):
        a = create_analyzer("squat")
        fb = a.update(None, 0.0)
        self.assertEqual(fb.message, "no_person")

    def test_noise_and_dropouts(self):
        reps = [RepSpec(85)] * 6 + [RepSpec(120, ["squat_shallow"])] * 2
        a, _ = run("squat", reps, "side", noise_px=6, outlier_rate=0.05, dropout_rate=0.03, seed=6)
        self.assertEqual(len(a.reps), len(reps))


if __name__ == "__main__":
    unittest.main()
