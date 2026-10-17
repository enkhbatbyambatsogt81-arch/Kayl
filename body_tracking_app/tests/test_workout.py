"""Дасгалын явц (эхлэх заавар, 3-2-1, сет, амралт), кадрт багтах шалгалт, дуу, дэлгэцийн тест.

Ажиллуулах:  python -m unittest discover -s tests -v
"""

import os
import sys
import tempfile
import unittest
import wave

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from form_checker.audio import SAMPLE_RATE, TONES, SoundPlayer, synth, write_wav  # noqa: E402
from form_checker.config import WorkoutConfig  # noqa: E402
from form_checker.exercises import create_analyzer  # noqa: E402
from form_checker.pose import framing_hint  # noqa: E402
from form_checker.session import PerfMeter  # noqa: E402
from form_checker.ui import Renderer  # noqa: E402
from form_checker.workout import Workout  # noqa: E402
from tools.synthetic import RepSpec, make_sequence, project, squat_skeleton  # noqa: E402


def run_workout(exercise, reps, cfg, start_pause=6.0, frames=None, **kw):
    if frames is None:
        frames, _ = make_sequence(exercise, reps, start_pause=start_pause, **kw)
    w = Workout(create_analyzer(exercise), cfg)
    views = [w.update(pose, t) for t, pose in frames]
    return w, views


def events(views):
    return [e for v in views for e in v.events]


class WorkoutFlowTest(unittest.TestCase):
    def test_setup_countdown_then_counts(self):
        cfg = WorkoutConfig(target_reps=3, sets=1)
        w, views = run_workout("squat", [RepSpec(85), RepSpec(85), RepSpec(120, ["squat_shallow"])], cfg, seed=11)
        phases = [v.phase for v in views]
        # Дараалал: setup -> countdown -> active -> done
        order = [p for i, p in enumerate(phases) if i == 0 or p != phases[i - 1]]
        self.assertEqual(order, ["setup", "countdown", "active", "done"])
        self.assertEqual([r.issues for r in w.reps], [[], [], ["squat_shallow"]])
        ev = events(views)
        self.assertEqual(ev.count("tick"), 3)       # 3-2-1
        self.assertEqual(ev.count("go"), 1)
        self.assertEqual((ev.count("good"), ev.count("bad"), ev.count("done")), (2, 1, 1))
        # "Барь" гэсэн мессеж ба явцын цагираг эхлэх шатанд гарна
        self.assertTrue(any(v.message == "hold_position" and 0 < v.ready_progress < 1 for v in views))

    def test_sets_and_rest(self):
        cfg = WorkoutConfig(target_reps=2, sets=2, rest_seconds=2.0)
        reps = [RepSpec(85), RepSpec(85, pause=8.0), RepSpec(85), RepSpec(120, ["squat_shallow"])]
        w, views = run_workout("squat", reps, cfg, seed=12)
        self.assertEqual([[r.issues for r in s] for s in w.sets], [[[], []], [[], ["squat_shallow"]]])
        self.assertIn("rest", [v.phase for v in views])
        self.assertEqual(events(views).count("set_done"), 1)
        self.assertEqual(views[-1].phase, "done")
        rest_left = [v.rest_left for v in views if v.phase == "rest"]
        self.assertAlmostEqual(rest_left[0], 2.0, delta=0.1)
        self.assertTrue(all(a >= b for a, b in zip(rest_left, rest_left[1:])))  # буурч тоолно

    def test_moving_without_holding_still_does_not_start(self):
        # Эхлэх байрлалд 1 секунд тогтвортой зогсолгүй шууд давтвал тоолол эхлэхгүй
        cfg = WorkoutConfig(target_reps=0)
        w, views = run_workout("squat", [RepSpec(85, pause=0.1)] * 4, cfg, start_pause=0.2, seed=13)
        self.assertEqual(w.reps, [])
        self.assertTrue(all(v.phase == "setup" for v in views))
        self.assertGreater(len(w.analyzer.reps), 0)  # анализатор тоолсон ч дасгалд бүртгэгдээгүй

    def test_person_lost_during_countdown_returns_to_setup(self):
        frames, _ = make_sequence("squat", [], start_pause=2.5, seed=14, dropout_rate=0)
        frames += [(2.5 + k / 30, None) for k in range(40)]
        w, views = run_workout("squat", [], WorkoutConfig(), frames=frames)
        self.assertIn("countdown", [v.phase for v in views])
        self.assertEqual(views[-1].phase, "setup")

    def test_skip_countdown_and_rest(self):
        frames, _ = make_sequence("squat", [], start_pause=3.0, seed=15, dropout_rate=0)
        w = Workout(create_analyzer("squat"), WorkoutConfig())
        phases = []
        for t, pose in frames:
            if phases and phases[-1] == "countdown":
                w.skip()
            phases.append(w.update(pose, t).phase)
        self.assertEqual(phases[-1], "active")
        self.assertLess(phases.count("countdown"), 3)

    def test_skip_in_setup_starts_countdown(self):
        frames, _ = make_sequence("squat", [], start_pause=1.0, seed=19, dropout_rate=0)
        w = Workout(create_analyzer("squat"), WorkoutConfig(ready_seconds=5.0))
        w.update(frames[0][1], frames[0][0])
        w.skip()
        self.assertEqual(w.update(frames[1][1], frames[1][0]).phase, "countdown")

    def test_video_mode_counts_like_analyzer(self):
        reps = [RepSpec(85), RepSpec(120, ["squat_shallow"]), RepSpec(85, ["squat_lean"]), RepSpec(85)]
        cfg = WorkoutConfig(target_reps=0, ready_seconds=0, countdown_seconds=0)
        w, _ = run_workout("squat", reps, cfg, start_pause=1.0, seed=16)
        self.assertEqual([r.issues for r in w.reps], [r.issues for r in reps])

    def test_setup_checklist_shows_what_is_missing(self):
        # 1.4: хүн алга -> хүн бий ч хөл кадраас гарсан -> бүтэн, эхлэх байрлалд -> тоолол
        frames, _ = make_sequence("squat", [], start_pause=2.0, seed=21, dropout_rate=0, noise_px=0)
        cut = frames[1][1]
        cut.img[:, 1] += 0.2 * cut.height  # хөл кадраас гарсан
        w = Workout(create_analyzer("squat"), WorkoutConfig())
        self.assertEqual(w.update(None, 0.0).setup_checks, (False, False, False))
        v = w.update(cut, frames[1][0])
        self.assertEqual(v.setup_checks, (True, False, False))
        self.assertEqual(v.message, "frame_feet")
        views = [w.update(pose, t) for t, pose in frames[2:]]
        self.assertIn((True, True, True), [v.setup_checks for v in views if v.phase == "setup"])
        self.assertIn("countdown", [v.phase for v in views])
        self.assertTrue(all(v.setup_checks is None for v in views if v.phase != "setup"))

    def test_depth_tone_once_per_deep_rep(self):
        # Зорилтот гүнд хүрсэн давталт бүрт нэг «depth» дохио, гүехэн давталтад дохио гарахгүй
        cfg = WorkoutConfig(target_reps=0)
        reps = [RepSpec(85), RepSpec(125, ["squat_shallow"]), RepSpec(85)]
        w, views = run_workout("squat", reps, cfg, seed=22)
        self.assertEqual(len(w.reps), 3)
        self.assertEqual(events(views).count("depth"), 2)
        first = next(i for i, v in enumerate(views) if "depth" in v.events)
        rep_done = next(i for i, v in enumerate(views) if "good" in v.events)
        self.assertLess(first, rep_done)  # давталт дуусахаас өмнө, доод цэг дээр

    def test_summary(self):
        cfg = WorkoutConfig(target_reps=3, sets=1)
        w, _ = run_workout("pushup", [RepSpec(80), RepSpec(80, ["pushup_sag"]), RepSpec(80, ["pushup_sag"])],
                           cfg, seed=17)
        s = w.summary()
        self.assertEqual((s["reps"], s["correct"]), (3, 1))
        self.assertEqual(s["issues"][0], ("pushup_sag", 2))
        self.assertAlmostEqual(s["accuracy"], 1 / 3)


class FramingTest(unittest.TestCase):
    def pose(self):
        P = squat_skeleton(175, [], 0.0)
        return project(P, "front", noise_px=0, rng=np.random.default_rng(0))

    def test_whole_body_visible(self):
        self.assertIsNone(framing_hint(self.pose(), min_size=0.3))

    def test_feet_cut_off(self):
        p = self.pose()
        p.img[:, 1] += 0.2 * p.height
        self.assertEqual(framing_hint(p), "frame_feet")

    def test_head_cut_off(self):
        p = self.pose()
        p.img[:, 1] -= 0.3 * p.height
        self.assertEqual(framing_hint(p), "frame_head")

    def test_body_outside_side(self):
        p = self.pose()
        p.img[:, 0] -= 0.55 * p.width
        self.assertEqual(framing_hint(p), "frame_side")

    def test_too_far(self):
        p = self.pose()
        center = p.img[:, :2].mean(axis=0)
        p.img[:, :2] = center + (p.img[:, :2] - center) * 0.3
        self.assertEqual(framing_hint(p, min_size=0.3), "frame_closer")
        self.assertIsNone(framing_hint(p))


class AudioTest(unittest.TestCase):
    def test_synth_length_and_range(self):
        for name, notes in TONES.items():
            x = synth(notes)
            self.assertEqual(x.dtype, np.int16)
            self.assertAlmostEqual(len(x) / SAMPLE_RATE, sum(d for _, d in notes), delta=0.01)
            self.assertLess(np.abs(x).max(), 32767 * 0.5)

    def test_wav_file(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "x.wav")
            write_wav(path, synth(TONES["good"]))
            with wave.open(path) as f:
                self.assertEqual((f.getnchannels(), f.getframerate()), (1, SAMPLE_RATE))

    def test_muted_player_is_silent(self):
        p = SoundPlayer(enabled=False)
        p.play_events(["good", "tick"])  # алдаа гарахгүй
        self.assertFalse(p.enabled)


class RenderSmokeTest(unittest.TestCase):
    def test_all_phases_render(self):
        cfg = WorkoutConfig(target_reps=2, sets=2, rest_seconds=1.0)
        reps = [RepSpec(85), RepSpec(120, ["squat_shallow"], pause=6.0), RepSpec(85), RepSpec(85)]
        frames, _ = make_sequence("squat", reps, start_pause=6.0, seed=18)
        w = Workout(create_analyzer("squat"), cfg)
        r = Renderer("mn")
        perf = PerfMeter()
        seen = set()
        for t, pose in frames:
            wv = w.update(pose, t)
            if wv.phase in seen and not wv.events:
                continue
            seen.add(wv.phase)
            frame = np.zeros((720, 1280, 3), np.uint8)
            out = r.render(frame, pose, wv, w.analyzer.counter, perf.current(), sound_on=True,
                           summary=w.summary(), sets=[s for s in w.sets if s])
            self.assertEqual(out.shape, (720, 1280, 3))
        self.assertEqual(seen, {"setup", "countdown", "active", "rest", "done"})


if __name__ == "__main__":
    unittest.main()
