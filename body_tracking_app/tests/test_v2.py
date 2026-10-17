"""2.0 хувилбарын шинэ боломжуудын тест: 1€ шүүлтүүр, шалгуурын түвшин, оноо ба сануулга,
дасгалыг автоматаар таних, идэвхгүй үеийн түр зогсолт, CSV-ийн шинэ баганууд.

Ажиллуулах:  python -m unittest discover -s tests -v
"""

import csv
import json
import os
import sys
import tempfile
import unittest

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from form_checker.config import CommonConfig, WorkoutConfig, exercise_config  # noqa: E402
from form_checker.engine import WorkoutEngine  # noqa: E402
from form_checker.exercises import create_analyzer  # noqa: E402
from form_checker.geometry import EMA, OneEuroFilter  # noqa: E402
from form_checker.history import load_history  # noqa: E402
from form_checker.pose import L_FOOT, R_FOOT  # noqa: E402
from form_checker.recognition import ExerciseRecognizer, WindowEMA, posture_scores  # noqa: E402
from form_checker.session import save_csv  # noqa: E402
from form_checker.settings import load_settings  # noqa: E402
from form_checker.workout import Workout  # noqa: E402
from tools.synthetic import RepSpec, make_sequence  # noqa: E402


def analyze(exercise, reps, level="normal", view="side", modify=None, **kw):
    frames, _ = make_sequence(exercise, reps, view=view, **kw)
    analyzer = create_analyzer(exercise, level)
    feedback = []
    for t, pose in frames:
        if modify is not None and pose is not None:
            modify(pose)
        feedback.append(analyzer.update(pose, t))
    return analyzer, feedback


class OneEuroFilterTest(unittest.TestCase):
    def test_constant_signal_passes_unchanged(self):
        f = OneEuroFilter(1.0, 0.05)
        for k in range(30):
            self.assertAlmostEqual(f.update(120.0, k / 30), 120.0)

    def test_reduces_jitter_more_than_ema_at_rest(self):
        rng = np.random.default_rng(0)
        noisy = 150 + rng.normal(0, 2.0, 300)
        c = CommonConfig()  # аппын анхдагч тохиргоо
        euro, ema = OneEuroFilter(c.one_euro_min_cutoff, c.one_euro_beta, c.one_euro_d_cutoff), EMA(0.5)
        a = [euro.update(x, k / 30) for k, x in enumerate(noisy)][30:]
        b = [ema.update(x) for x in noisy][30:]
        # Хөдөлгөөнгүй үед 1€ нь бага тасалгааны давтамжаар (0.5 Гц) шүүдэг тул чичиргээ хэд дахин бага
        self.assertLess(np.std(np.diff(a)), 0.5 * np.std(np.diff(b)))

    def test_speed_raises_cutoff_and_cuts_lag(self):
        ramp = [180 - 150 * k / 30 for k in range(25)]  # 150°/с хурдтай доошлох хөдөлгөөн
        slow, fast = OneEuroFilter(1.0, 0.0), OneEuroFilter(1.0, 0.05)
        for k, x in enumerate(ramp):
            ys, yf = slow.update(x, k / 30), fast.update(x, k / 30)
        # beta > 0 бол хурдан хөдөлгөөнд жинхэнэ утгад илүү ойр (хоцрогдол бага)
        self.assertLess(abs(yf - ramp[-1]), 0.5 * abs(ys - ramp[-1]))

    def test_uses_timestamps(self):
        # Кадр алгасвал (dt том) шинэ утгад илүү их жин өгнө
        a, b = OneEuroFilter(1.0, 0.0), OneEuroFilter(1.0, 0.0)
        a.update(0.0, 0.0), b.update(0.0, 0.0)
        self.assertGreater(b.update(10.0, 0.5), a.update(10.0, 1 / 30))

    def test_reset_and_nan(self):
        f = OneEuroFilter()
        self.assertIsNone(f.update(float("nan")))
        f.update(5.0)
        f.reset()
        self.assertIsNone(f.value)


class LevelTest(unittest.TestCase):
    def test_level_configs(self):
        self.assertEqual(exercise_config("squat", "easy").depth_angle, 110.0)
        self.assertEqual(exercise_config("squat", "normal").depth_angle, 100.0)
        self.assertEqual(exercise_config("squat", "strict").depth_angle, 90.0)
        self.assertEqual(exercise_config("pushup", "strict").depth_angle, 80.0)
        self.assertEqual(exercise_config("squat", "strict").min_stance_ratio, 1.2)  # Exercise-Correction-ий утга
        self.assertEqual(create_analyzer("pushup", "easy").level, "easy")

    def test_same_rep_judged_by_level(self):
        reps = [RepSpec(95), RepSpec(107)]
        results = {lvl: [r.correct for r in analyze("squat", reps, lvl, seed=3)[0].reps]
                   for lvl in ("easy", "normal", "strict")}
        self.assertEqual(results, {"easy": [True, True], "normal": [True, False], "strict": [False, False]})


class ScoreAndWarningTest(unittest.TestCase):
    def test_scores(self):
        reps = [RepSpec(80), RepSpec(80, ["squat_lean"]), RepSpec(125, ["squat_shallow"])]
        a, _ = analyze("squat", reps, seed=4)
        scores = [r.score for r in a.reps]
        self.assertEqual(scores[0], 100)
        self.assertEqual(scores[1], 100 - a.SCORE_ISSUE)
        self.assertTrue(55 <= scores[2] <= 85, scores)
        self.assertEqual(a.score_rep(150, False, ["squat_shallow"], []), 100 - a.SCORE_SHALLOW_MAX)

    def test_fast_rep_is_correct_but_warned(self):
        a, fbs = analyze("squat", [RepSpec(80, duration=0.8), RepSpec(80, duration=2.4)], seed=4)
        self.assertEqual([r.correct for r in a.reps], [True, True])
        self.assertEqual([r.warnings for r in a.reps], [["squat_fast"], []])
        self.assertEqual([r.score for r in a.reps], [100 - a.SCORE_WARNING, 100])
        self.assertIn("squat_fast", [f.message for f in fbs])

    def test_narrow_stance_warning_front_view(self):
        def narrow(pose):
            mid = (pose.img[L_FOOT, 0] + pose.img[R_FOOT, 0]) / 2
            for i in (L_FOOT, R_FOOT):
                pose.img[i, 0] = mid + 0.3 * (pose.img[i, 0] - mid)
        a, fbs = analyze("squat", [RepSpec(80), RepSpec(80)], view="front", modify=narrow, seed=5,
                         start_pause=2.0)
        self.assertEqual([r.correct for r in a.reps], [True, True])
        self.assertTrue(all("squat_stance_narrow" in r.warnings for r in a.reps))
        self.assertIn("squat_stance_narrow", [f.message for f in fbs])
        # Хэвийн өргөнтэй бол сануулгагүй
        b, _ = analyze("squat", [RepSpec(80), RepSpec(80)], view="front", seed=5, start_pause=2.0)
        self.assertEqual([r.warnings for r in b.reps], [[], []])

    def test_summary_has_score_and_warnings(self):
        frames, _ = make_sequence("squat", [RepSpec(80, duration=0.8), RepSpec(80)], start_pause=6.0, seed=4)
        w = Workout(create_analyzer("squat"), WorkoutConfig(target_reps=0))
        for t, pose in frames:
            w.update(pose, t)
        s = w.summary()
        self.assertEqual(s["reps"], 2)
        self.assertAlmostEqual(s["avg_score"], 95.0)
        self.assertEqual(s["warnings"], [("squat_fast", 1)])


class RecognitionTest(unittest.TestCase):
    def test_posture_scores(self):
        stand, _ = make_sequence("squat", [RepSpec(85)], seed=1)
        plank, _ = make_sequence("pushup", [RepSpec(85)], seed=1)
        self.assertGreater(posture_scores(stand[0][1])["squat"], 0.9)
        self.assertGreater(posture_scores(plank[0][1])["pushup"], 0.9)
        # Squat-ын доод цэгт ч их бие босоо хэвээр
        deepest = min((p for _, p in stand if p is not None), key=lambda p: p.img[23, 1] - p.img[25, 1])
        self.assertGreater(posture_scores(deepest)["squat"], 0.9)

    def test_window_ema_matches_mlkit_weights(self):
        s = WindowEMA(window=3, alpha=0.5)
        s.update(0.0), s.update(0.0)
        # Жин: шинэ 1, өмнөх 0.5, түүний өмнөх 0.25 -> 1 / 1.75
        self.assertAlmostEqual(s.update(1.0), 1 / 1.75)

    def test_recognizer_needs_stable_posture(self):
        for exercise in ("squat", "pushup"):
            frames, _ = make_sequence(exercise, [RepSpec(85), RepSpec(85)], noise_px=5, seed=2)
            rec = ExerciseRecognizer()
            out = [rec.update(p, t) for t, p in frames]
            first = next(i for i, o in enumerate(out) if o)
            self.assertGreaterEqual(first / 30, rec.hold_seconds)       # шууд биш, тогтвортой болсны дараа
            self.assertEqual({o for o in out if o}, {exercise})          # давталтын үеэр ч солигдохгүй

    def test_hysteresis(self):
        rec = ExerciseRecognizer(hold_seconds=0)
        rec.current = "squat"
        rec.confidence = {"squat": 0.5, "pushup": 0.5}
        # 0.5 нь гарах босго (0.4)-оос дээр тул "squat" хэвээр
        self.assertGreater(rec.confidence["squat"], rec.exit)


class AutoSwitchTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def engine(self, exercise="squat"):
        # open() дуудахгүй: зөвхөн дасгал солих логикийг шалгана
        return WorkoutEngine(exercise=exercise, source="demo", sound=False, log_dir=self.tmp.name,
                             auto_detect=True)

    def test_switches_to_detected_exercise_in_setup(self):
        e = self.engine("squat")
        frames, _ = make_sequence("pushup", [RepSpec(85)], seed=6)
        switched = [e._auto_detect(p, t) for t, p in frames[:40]]
        self.assertIn("pushup", switched)
        self.assertEqual(e.exercise, "pushup")
        self.assertEqual(e._notice, "switched_pushup")

    def test_manual_choice_is_respected(self):
        e = self.engine("squat")
        frames, _ = make_sequence("squat", [RepSpec(85)], seed=6)
        for t, p in frames[:30]:
            e._auto_detect(p, t)          # зогсож байна -> squat
        e.set_exercise("pushup")          # хэрэглэгч гараар push-up сонгов
        e._apply_commands(1.0)
        for t, p in frames[30:60]:
            self.assertIsNone(e._auto_detect(p, t))
        self.assertEqual(e.exercise, "pushup")

    def test_no_switch_mid_set(self):
        e = self.engine("squat")
        w = e.workout
        w.phase = "active"
        w.sets[-1].append(object())       # энэ сетэд давталт хийсэн
        frames, _ = make_sequence("pushup", [RepSpec(85)], seed=6)
        for t, p in frames[:40]:
            self.assertIsNone(e._auto_detect(p, t))
        self.assertEqual(e.exercise, "squat")


class InactivityTest(unittest.TestCase):
    def active_workout(self, cfg):
        frames, _ = make_sequence("squat", [RepSpec(85), RepSpec(85, pause=2.0)], start_pause=6.0, seed=7)
        w = Workout(create_analyzer("squat"), cfg)
        views = [w.update(p, t) for t, p in frames]
        self.assertEqual(views[-1].phase, "active")
        return w, frames, frames[-1][0]

    def test_pause_when_person_leaves(self):
        w, _, t0 = self.active_workout(WorkoutConfig(target_reps=10, away_seconds=5.0))
        reps = len(w.reps)
        views = [w.update(None, t0 + k / 30) for k in range(1, 30 * 6)]
        self.assertEqual(views[-1].phase, "setup")
        self.assertEqual(views[-1].message, "paused_away")
        self.assertEqual(len(w.reps), reps)                     # сетийн явц хадгалагдсан
        self.assertTrue(all(v.phase == "active" for v in views[:30 * 4]))  # 5 секундээс өмнө зогсохгүй

    def test_idle_hint_when_standing_still(self):
        w, frames, t0 = self.active_workout(WorkoutConfig(target_reps=10, idle_seconds=3.0))
        stand = frames[-1][1]
        views = [w.update(stand, t0 + k / 30) for k in range(1, 30 * 5)]
        self.assertEqual(views[-1].message, "idle_hint")
        self.assertEqual(views[-1].phase, "active")


class CsvAndSettingsTest(unittest.TestCase):
    def test_csv_has_score_and_history_reads_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            frames, _ = make_sequence("squat", [RepSpec(80, duration=0.8), RepSpec(80)], start_pause=6.0, seed=4)
            w = Workout(create_analyzer("squat", "strict"), WorkoutConfig(target_reps=0))
            for t, pose in frames:
                w.update(pose, t)
            path = save_csv([w], tmp)
            with open(path, encoding="utf-8-sig") as f:
                rows = list(csv.DictReader(f))
            self.assertEqual([r["level"] for r in rows], ["strict", "strict"])
            self.assertEqual(rows[0]["warnings"], "squat_fast")
            rec = load_history(tmp)[0]
            self.assertAlmostEqual(rec.avg_score, w.summary()["avg_score"])
            self.assertEqual(rec.level, "strict")
            # 1.x хувилбарын лог (score баганагүй) уншигдсаар байна
            old = os.path.join(tmp, "session_20261001_100000.csv")
            with open(old, "w", newline="", encoding="utf-8-sig") as f:
                f.write("exercise,set,rep,correct,issues,min_angle_deg,duration_s\nsquat,1,1,True,,85,2.0\n")
            recs = {r.path: r for r in load_history(tmp)}
            self.assertIsNone(recs[old].avg_score)

    def test_settings_validate_level(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "settings.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump({"level": "hard", "auto_detect": "yes"}, f)
            s = load_settings(path)
            self.assertEqual((s["level"], s["auto_detect"]), ("normal", True))
            with open(path, "w", encoding="utf-8") as f:
                json.dump({"level": "strict", "auto_detect": False}, f)
            s = load_settings(path)
            self.assertEqual((s["level"], s["auto_detect"]), ("strict", False))


if __name__ == "__main__":
    unittest.main()
