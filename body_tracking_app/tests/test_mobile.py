"""3.2: утасны (Android) хувилбарын хөдөлгүүр (form_checker/mobile.py).

Утсан дээр энэ код Pyodide-оор ажиллана. Энд компьютерын Python-оор: OpenCV-гүй уншигддаг, компьютерын
хөдөлгүүртэй (engine.WorkoutEngine) яг ижил тоолдог, гаралт нь JSON болдог эсэхийг шалгана.
Ажиллуулах:  python -m unittest discover -s tests -v
"""

import json
import os
import subprocess
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from form_checker import mobile  # noqa: E402
from form_checker.demo import demo_frames  # noqa: E402
from form_checker.mobile import MobileSession  # noqa: E402


def run_demo(session, seconds, fps=30):
    views = []
    for i in range(int(seconds * fps)):
        views.append(session.demo_frame(i / fps))
    return views


class MobileSessionTest(unittest.TestCase):
    def test_imports_without_opencv_and_mediapipe(self):
        code = ("import sys; sys.modules['cv2'] = None; sys.modules['mediapipe'] = None; "
                "import form_checker.mobile as m; s = m.MobileSession(demo=True); "
                "print(s.demo_frame(0.0)['phase'])")
        out = subprocess.run([sys.executable, "-c", code], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(out.stdout.strip(), "setup", out.stderr)

    def test_demo_counts_the_same_as_the_desktop_engine(self):
        from form_checker.engine import WorkoutEngine

        for exercise in ("squat", "pushup"):
            engine = WorkoutEngine(exercise=exercise, source="demo", sound=False, hud=False)
            self.assertIsNone(engine.open())
            session = MobileSession(exercise=exercise, demo=True)
            for i in range(30 * 40):
                ef = engine.step()
                view = session.demo_frame(i / 30)
                self.assertEqual((view["phase"], view["message_key"], view["total_reps"], view["total_correct"]),
                                 (ef.wv.phase, ef.wv.message, ef.wv.total_reps, ef.wv.total_correct), (exercise, i))
                self.assertEqual(view["events"], ef.wv.events)
            engine.close()
            self.assertGreaterEqual(view["total_reps"], 8)
            self.assertLess(view["total_correct"], view["total_reps"])     # демод алдаатай давталт бий

    def test_views_are_strict_json(self):
        session = MobileSession(demo=True)
        for view in run_demo(session, 12):
            text = json.dumps(view, allow_nan=False)                    # NaN байвал JavaScript унана
        view = json.loads(text)
        self.assertEqual(view["phase"], "active")
        self.assertEqual(len(view["pose"]["points"]), 33)
        self.assertEqual(view["angle_joint"], 25)                          # зүүн өвдөг (камер талын)
        self.assertEqual(view["depth_target"], 100.0)
        self.assertIsInstance(view["message"], str)
        empty = session.frame(None, 640, 480, 12.1)                        # хүн алга: тоо биш утгууд None
        json.dumps(empty, allow_nan=False)

    def test_camera_frames_as_flat_numbers(self):
        """JavaScript 33 × (x, y, z, visibility) дараалсан 132 тоо өгнө."""
        frames = demo_frames("squat")
        a, b = MobileSession(demo=True), MobileSession()
        for i in range(30 * 20):
            pose = frames[i][1]
            flat = [float(v) for row, vis in zip(pose.img, pose.vis) for v in (*row, vis)]
            va, vb = a.demo_frame(i / 30), b.frame(flat, pose.width, pose.height, i / 30)
            self.assertEqual((va["phase"], va["total_reps"], va["angle"]), (vb["phase"], vb["total_reps"], vb["angle"]))
        self.assertGreaterEqual(vb["total_reps"], 4)
        self.assertNotIn("pose", vb)

    def test_level_goal_and_free_mode(self):
        s = MobileSession(level="strict", reps=5, sets=2, rest=30)
        self.assertEqual((s.cfg.target_reps, s.cfg.sets, s.cfg.rest_seconds), (5, 2, 30.0))
        self.assertEqual(s.workout.analyzer.counter.depth, 90.0)
        self.assertEqual(MobileSession(free_mode=True, reps=10).cfg.target_reps, 0)
        self.assertEqual(MobileSession(level="???").level, "normal")

    def test_set_rest_skip_and_summary(self):
        session = MobileSession(demo=True, reps=3, sets=2, rest=60)
        phases, t = [], 0.0
        while t < 90 and (not phases or phases[-1] != "done"):
            view = session.demo_frame(t)
            if view["phase"] == "rest":
                self.assertIsNotNone(view["rest_left"])
                session.skip()                                             # амралтыг алгасна
            if not phases or phases[-1] != view["phase"]:
                phases.append(view["phase"])
            t += 1 / 30
        self.assertEqual(phases, ["setup", "countdown", "active", "rest", "setup", "countdown", "active", "done"])
        (s,) = session.summary()
        self.assertEqual((s["exercise"], s["reps"], s["sets"][0][0], len(s["rep_scores"])), ("squat", 6, 3, 6))
        self.assertTrue(s["issues"] and s["issues"][0]["tip"])             # алдаа бүрт засах зөвлөмж
        json.dumps(session.summary(), allow_nan=False)

    def test_switch_exercise_and_finish(self):
        session = MobileSession(demo=True)
        run_demo(session, 3)
        session.set_exercise("pushup")
        view = session.demo_frame(3.1)
        self.assertEqual((view["exercise"], view["phase"]), ("pushup", "setup"))
        session.finish()
        self.assertEqual(session.demo_frame(3.2)["phase"], "done")
        self.assertEqual(session.summary(), [])                            # давталт хийгээгүй

    def test_javascript_entry_points(self):
        info = json.loads(mobile.info())
        self.assertIn([11, 13], [list(pair) for pair in info["skeleton"]])
        self.assertEqual(info["messages"]["good_rep"], "Зөв! Сайн байна")
        started = json.loads(mobile.start(json.dumps({"exercise": "pushup", "demo": True, "reps": 2, "sets": 1})))
        self.assertEqual(started, {"exercise": "pushup", "level": "normal", "demo": True})
        view = json.loads(mobile.demo_frame(0.0))
        self.assertEqual(view["exercise"], "pushup")
        for i in range(30):                                                # хүн 1 секунд алга
            view = json.loads(mobile.frame(None, 640, 480, 0.1 + i / 30))
        self.assertEqual((view["message_key"], view["checks"]), ("no_person", [False, False, False]))
        mobile.command("exercise", "squat")
        mobile.command("skip")
        mobile.command("finish")
        self.assertEqual(json.loads(mobile.demo_frame(1.2))["phase"], "done")
        self.assertEqual(json.loads(mobile.summary()), [])


if __name__ == "__main__":
    unittest.main()
