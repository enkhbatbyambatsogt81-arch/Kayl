"""Хөдөлгүүр (демо эх үүсвэр), түүх, тохиргоо ба цонхтой интерфейсийн тест.

Ажиллуулах:  python -m unittest discover -s tests -v
GUI тест нь tkinter, customtkinter ба дэлгэц байхгүй үед автоматаар алгасагдана.
"""

import json
import os
import sys
import tempfile
import time
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from form_checker.config import WorkoutConfig  # noqa: E402
from form_checker.engine import WorkoutEngine  # noqa: E402
from form_checker.history import compare_with_history, load_history  # noqa: E402
from form_checker.settings import DEFAULTS, load_settings, save_settings  # noqa: E402


def run_until(engine, cond, max_frames=4000):
    ef = None
    for _ in range(max_frames):
        ef = engine.step()
        if ef is None or cond(ef):
            return ef
    return ef


class EngineDemoTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def make(self, cfg=None, exercise="squat", **kw):
        engine = WorkoutEngine(exercise=exercise, source="demo", workout_cfg=cfg, sound=False,
                               log_dir=self.tmp.name, **kw)
        self.assertEqual(engine.kind, "demo")
        self.assertIsNone(engine.open())
        return engine

    def test_demo_workout_counts_sets_and_saves_csv(self):
        engine = self.make(WorkoutConfig(target_reps=4, sets=2, rest_seconds=3))
        ef = run_until(engine, lambda ef: ef.wv.phase == "done")
        self.assertEqual(ef.wv.phase, "done")
        self.assertEqual([len(s) for s in engine.workout.sets], [4, 4])
        summary = engine.workout.summary()
        self.assertEqual(summary["reps"], 8)
        # Демо дасгалд алдаатай давталт холилдсон
        self.assertLess(summary["correct"], 8)
        self.assertGreater(summary["correct"], 0)
        self.assertEqual(ef.image.shape, (720, 1280, 3))

        path = engine.close()
        self.assertTrue(path and os.path.dirname(path) == self.tmp.name)
        records = load_history(self.tmp.name)
        self.assertEqual(len(records), 1)
        self.assertEqual((records[0].exercise, records[0].reps, records[0].sets), ("squat", 8, 2))
        self.assertEqual(records[0].correct, summary["correct"])

    def test_pushup_demo_counts(self):
        engine = self.make(WorkoutConfig(target_reps=5, sets=1), exercise="pushup")
        ef = run_until(engine, lambda ef: ef.wv.phase == "done")
        self.assertEqual(ef.wv.phase, "done")
        self.assertEqual(len(engine.workout.reps), 5)
        engine.close()

    def test_commands_skip_switch_finish(self):
        engine = self.make(WorkoutConfig(target_reps=10, sets=3, ready_seconds=60))
        ef = run_until(engine, lambda ef: ef.wv.fb.main_angle is not None, 30)
        self.assertEqual(ef.wv.phase, "setup")
        engine.skip()                       # нэг Space -> зөвхөн тоолол руу
        self.assertEqual(engine.step().wv.phase, "countdown")
        engine.skip()
        self.assertEqual(engine.step().wv.phase, "active")

        engine.set_exercise("pushup")
        ef = engine.step()
        self.assertEqual((engine.exercise, ef.exercise), ("pushup", "pushup"))
        self.assertEqual(engine.workouts["squat"].phase, "setup")  # нөгөө дасгал түр зогссон

        engine.finish()
        self.assertEqual(engine.step().wv.phase, "done")
        self.assertIsNone(engine.close())   # давталт хийгээгүй бол CSV хадгалахгүй
        self.assertEqual(os.listdir(self.tmp.name), [])

    def test_hud_off_keeps_frame_size(self):
        engine = self.make(hud=False)
        ef = engine.step()
        self.assertEqual(ef.image.shape, (720, 1280, 3))
        engine.close()

    def test_missing_video_reports_error(self):
        engine = WorkoutEngine(source=os.path.join(self.tmp.name, "missing.mp4"), sound=False,
                               log_dir=self.tmp.name)
        self.assertEqual(engine.kind, "video")
        err = engine.open()
        self.assertIn("нээж чадсангүй", err)
        self.assertIsNone(engine.close())

    def test_default_configs(self):
        video = WorkoutEngine.default_config("video")
        self.assertEqual((video.target_reps, video.ready_seconds, video.countdown_seconds), (0, 0, 0))
        cam = WorkoutEngine.default_config("camera", 12, 2, 30.0)
        self.assertEqual((cam.target_reps, cam.sets, cam.rest_seconds), (12, 2, 30.0))


class HistoryTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def write(self, name, text):
        with open(os.path.join(self.tmp.name, name), "w", encoding="utf-8-sig") as f:
            f.write(text)

    def test_reads_v1_and_v11_logs_newest_first(self):
        # 1.0 хувилбарын лог ("set" баганагүй)
        self.write("session_20261001_090000.csv",
                   "exercise,rep,correct,issues,min_angle_deg,duration_s\n"
                   "pushup,1,True,,85.0,1.5\npushup,2,False,pushup_sag,88.0,1.7\n")
        # 1.1+ лог: хоёр дасгал нэг файлд
        self.write("session_20261008_101500.csv",
                   "exercise,set,rep,correct,issues,min_angle_deg,duration_s\n"
                   "squat,1,1,True,,84.0,2.0\n"
                   "squat,1,2,False,squat_shallow;squat_lean,120.0,2.2\n"
                   "squat,2,1,False,squat_shallow,118.0,bad\n"
                   "pushup,1,1,True,,80.0,1.4\n")
        self.write("session_broken.csv", "\x00\x01 not a csv")
        self.write("notes.txt", "ignored")

        records = load_history(self.tmp.name)
        recent = [r for r in records if r.when.day == 8]
        self.assertEqual(sorted(r.exercise for r in recent), ["pushup", "squat"])
        squat = next(r for r in recent if r.exercise == "squat")
        self.assertEqual((squat.reps, squat.correct, squat.sets), (3, 1, 2))
        self.assertEqual(squat.issues["squat_shallow"], 2)
        self.assertAlmostEqual(squat.avg_duration, 2.1)  # "bad" утгыг алгасна
        self.assertAlmostEqual(squat.accuracy, 1 / 3)

        old = next(r for r in records if r.when.day == 1)
        self.assertEqual((old.exercise, old.reps, old.correct, old.sets), ("pushup", 2, 1, 1))
        # Шинэ нь эхэндээ (эвдэрсэн файл файлын өөрчлөгдсөн цагаар хамгийн сүүлд эрэмбэлэгдэж болно)
        dated = [r for r in records if r.when.year == 2026 and r.when.month == 10 and r.when.day in (1, 8)]
        self.assertEqual(dated[-1].when.day, 1)

    def test_missing_folder_is_empty(self):
        self.assertEqual(load_history(os.path.join(self.tmp.name, "nope")), [])

    def test_compare_with_previous_session(self):
        rows = lambda ex, flags: "".join(f"{ex},1,{i},{f},,90,1.5\n" for i, f in enumerate(flags, 1))  # noqa: E731
        head = "exercise,set,rep,correct,issues,min_angle_deg,duration_s\n"
        self.write("session_20261001_090000.csv", head + rows("squat", [True] * 4 + [False] * 6))  # 40%
        self.write("session_20261003_090000.csv", head + rows("squat", [True] * 6 + [False] * 4)
                   + rows("pushup", [True] * 2))                                                    # 60%
        self.write("session_20261005_090000.csv", head + rows("squat", [True] * 7 + [False] * 1))  # одоогийн
        records = load_history(self.tmp.name)
        current = os.path.join(self.tmp.name, "session_20261005_090000.csv")
        c = compare_with_history(records, "squat", 8, 7, exclude_path=current)
        self.assertEqual(c["previous"].when.day, 3)          # одоогийн файлыг хасаж, өмнөхийг нь авна
        self.assertAlmostEqual(c["best_accuracy"], 0.6)
        self.assertTrue(c["new_best"])                       # 87.5% > 60%
        c = compare_with_history(records, "squat", 10, 5, exclude_path=current)
        self.assertFalse(c["new_best"])
        first = compare_with_history(records, "pushup", 3, 3,
                                     exclude_path=os.path.join(self.tmp.name, "session_20261003_090000.csv"))
        self.assertIsNone(first["previous"])                 # анхны push-up
        self.assertFalse(first["new_best"])


class SettingsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = os.path.join(self.tmp.name, "settings.json")

    def test_missing_file_gives_defaults(self):
        self.assertEqual(load_settings(self.path), DEFAULTS)

    def test_round_trip(self):
        s = dict(DEFAULTS, exercise="pushup", reps=15, sets=4, rest=90, source="demo", appearance="light",
                 free_mode=True, video_path="C:/Видео/squat.mp4")
        self.assertTrue(save_settings(s, self.path))
        self.assertEqual(load_settings(self.path), s)

    def test_invalid_values_fall_back(self):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump({"reps": -3, "sets": True, "rest": "60", "exercise": "lunge", "model": "heavy",
                       "sound": 1, "camera_index": 42, "unknown": 5, "appearance": "light"}, f)
        s = load_settings(self.path)
        for key in ("reps", "sets", "rest", "exercise", "model", "sound", "camera_index"):
            self.assertEqual(s[key], DEFAULTS[key], key)
        self.assertEqual(s["appearance"], "light")
        self.assertNotIn("unknown", s)

    def test_corrupt_file(self):
        for text in ("{not json", "[1, 2, 3]", ""):
            with open(self.path, "w", encoding="utf-8") as f:
                f.write(text)
            self.assertEqual(load_settings(self.path), DEFAULTS)


def _gui_available():
    try:
        import customtkinter  # noqa: F401
        import tkinter
    except ImportError:
        return False
    if sys.platform.startswith("linux") and not os.environ.get("DISPLAY"):
        return False
    try:
        root = tkinter.Tk()
        root.destroy()
    except tkinter.TclError:
        return False
    return True


@unittest.skipUnless(_gui_available(), "tkinter/customtkinter эсвэл дэлгэц байхгүй")
class GuiSmokeTest(unittest.TestCase):
    """Демо горимоор: нүүр -> дасгал -> дүн -> түүх -> заавар хуудсуудыг нээгээд алдаагүй ажиллахыг шалгана."""

    def test_demo_session_through_pages(self):
        from form_checker.gui import app as appmod

        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        saved = {}
        settings = dict(DEFAULTS, source="demo", reps=3, sets=1, rest=15, sound=False)
        orig_load, orig_save = appmod.load_settings, appmod.save_settings
        appmod.load_settings = lambda: dict(settings)
        appmod.save_settings = lambda s: saved.update(s) or True
        self.addCleanup(setattr, appmod, "load_settings", orig_load)
        self.addCleanup(setattr, appmod, "save_settings", orig_save)

        app = appmod.App(log_dir=tmp.name)
        try:
            def pump(seconds, until=lambda: False):
                end = time.time() + seconds
                while time.time() < end and not until():
                    app.update()
                    time.sleep(0.01)

            pump(0.6, lambda: app.onboarding.visible)
            self.assertTrue(app.onboarding.visible)                  # анх нээхэд танилцуулга гарна
            for _ in range(3):
                app.onboarding.next()
            self.assertFalse(app.onboarding.visible)
            self.assertTrue(saved.get("onboarded"))
            self.assertEqual(app.current, "home")
            home = app.pages["home"]
            home._on_preset("Эхлэгч")
            self.assertEqual((app.settings["reps"], app.settings["sets"]), (8, 2))
            home._on_reps(3)                                         # гараар өөрчилбөл «Өөрөө»
            home._on_sets("1")
            self.assertEqual(home.preset.get(), "Өөрөө")
            home._on_level("Хатуу")                                  # 2.0: шалгуурын түвшин
            self.assertEqual(app.settings["level"], "strict")
            self.assertIn("90°", home.level_lbl.cget("text"))
            home._on_level("Энгийн")
            app.start_workout()
            self.assertEqual(app.current, "workout")
            self.assertEqual(saved.get("source"), "demo")
            page = app.pages["workout"]
            pump(10, lambda: page._last_ef is not None and page._last_ef.wv.phase == "active")
            self.assertIsNotNone(page._last_ef, "демо кадр ирсэнгүй")
            pump(8, lambda: page._last_ef.wv.total_reps >= 1)
            self.assertGreater(len(page.trace.points), 30)           # хөдөлгөөний график шинэчлэгдэж байна
            self.assertEqual(len(page.trace.marks), page._last_ef.wv.total_reps)
            self.assertTrue(page.time_lbl.cget("text").startswith("Хугацаа"))
            self.assertTrue(page.score_lbl.cget("text").startswith("Оноо: "))   # 2.0: давталтын оноо
            self.assertEqual(page.engine.level, "normal")
            app.toggle_fullscreen()
            self.assertTrue(app.fullscreen)
            app.toggle_fullscreen(False)
            page.request_leave()                                     # давталт хийсэн тул шууд гарахгүй, асууна
            self.assertTrue(page.confirm.visible)
            self.assertTrue(page.engine.paused)
            self.assertEqual(app.current, "workout")
            page.confirm_continue()
            self.assertFalse(page.confirm.visible)
            self.assertFalse(page.engine.paused)
            page.finish()
            pump(5, lambda: app.current == "summary")
            self.assertEqual(app.current, "summary")
            self.assertIn("Сүүлд ", app.progress_lbl.cget("text"))   # хажуу цэсний «Таны явц»
            app.show("history")
            pump(0.3)
            hist = app.pages["history"]
            hist.filter.set("Push-up")
            hist.refresh()
            self.assertIn("алга", hist.empty.cget("text"))           # push-up хийгээгүй
            hist.filter.set("Squat")
            hist.refresh()
            self.assertEqual(hist.t_sessions.value.cget("text"), "1")
            app.show("help")
            pump(0.3)
        finally:
            app.on_close()

    def test_angle_trace_marks_each_rep_at_its_deepest_point(self):
        import math
        import tkinter

        from form_checker.gui.widgets import AngleTrace

        class Rep:
            def __init__(self, correct):
                self.correct = correct

        root = tkinter.Tk()
        try:
            trace = AngleTrace(root, width=600)
            trace.pack()
            trace.reset(100)
            # Ижил гүнтэй хоёр давталт: 1.5 с ба 4.5 с-д хамгийн гүн (85°), 3.0 ба 6.0 с-д бүртгэгдэнэ
            for k in range(0, 241):
                t = k / 30
                a = 130 + 45 * math.cos(2 * math.pi * t / 3.0)
                rep = Rep(k == 90) if k in (90, 180) else None
                trace.push(t, a if k != 50 else None, rep, rep_no=1 if k == 90 else 2)
            times = [round(m[0], 1) for m in trace.marks]
            self.assertEqual(times, [1.5, 4.5])
            self.assertEqual([m[2] for m in trace.marks], [True, False])
            trace.push(1.0, 120)  # цаг ухарвал (видео дахин эхэлбэл) цэвэрлэнэ
            self.assertEqual(len(trace.points), 1)
            self.assertEqual(len(trace.marks), 0)
        finally:
            root.destroy()


if __name__ == "__main__":
    unittest.main()
