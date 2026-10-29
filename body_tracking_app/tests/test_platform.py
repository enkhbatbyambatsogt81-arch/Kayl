"""2.1: Windows / macOS / Linux дээр ажиллахад нөлөөлдөг хэсгүүдийн тест.

Камерын backend, кирилл замтай загвар, «Хэмжээ» тохиргоо, томруулалт солигдоход нуусан элемент гарч ирэхгүй байх.
Ажиллуулах:  python -m unittest discover -s tests -v
"""

import os
import shutil
import sys
import tempfile
import time
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import cv2  # noqa: E402
import numpy as np  # noqa: E402

from form_checker import camera, pose  # noqa: E402
from form_checker.settings import DEFAULTS, load_settings  # noqa: E402
from test_app import _gui_available  # noqa: E402


class CameraTest(unittest.TestCase):
    def test_each_platform_has_backends_and_help(self):
        for key in ("win", "mac", "linux"):
            self.assertTrue(camera.BACKENDS[key])
            self.assertTrue(camera.CAMERA_HELP[key])
        apis = camera.backends()
        self.assertEqual(apis[-1], cv2.CAP_ANY)    # эцэст нь OpenCV өөрөө сонгоно
        self.assertTrue(all(isinstance(a, int) for a in apis))

    def test_missing_camera_returns_none(self):
        level = cv2.utils.logging.getLogLevel()
        cv2.utils.logging.setLogLevel(cv2.utils.logging.LOG_LEVEL_SILENT)
        self.addCleanup(cv2.utils.logging.setLogLevel, level)
        self.assertIsNone(camera.open_camera(42, warmup=0.1))

    def test_find_cameras_restores_opencv_log_level(self):
        before = cv2.utils.logging.getLogLevel()
        with mock.patch.object(camera, "open_camera", side_effect=lambda i, warmup: None):
            self.assertEqual(camera.find_cameras(max_index=3), [])
        self.assertEqual(cv2.utils.logging.getLogLevel(), before)


class ModelPathTest(unittest.TestCase):
    def test_model_loads_from_folder_with_cyrillic_name(self):
        """Windows-д MediaPipe кирилл замтай файлыг нээж чаддаггүй байсан тул загварыг санах ойгоор өгнө."""
        src = os.path.join(pose.MODELS_DIR, "pose_landmarker_lite.task")
        if not os.path.exists(src):
            self.skipTest("models/pose_landmarker_lite.task алга")
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        folder = os.path.join(tmp, "Хүн компьютерын харилцаа")
        os.makedirs(folder)
        shutil.copy(src, folder)
        with mock.patch.object(pose, "MODELS_DIR", folder):
            with pose.PoseEstimator("lite") as est:
                self.assertIsNone(est.process(np.zeros((240, 320, 3), np.uint8), 0))  # хоосон кадрт хүн алга


class ScaleSettingTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.path = os.path.join(tmp.name, "settings.json")

    def load(self, text):
        with open(self.path, "w", encoding="utf-8") as f:
            f.write(text)
        return load_settings(self.path)

    def test_scale_values(self):
        self.assertEqual(DEFAULTS["ui_scale"], 1.0)
        self.assertEqual(self.load('{"ui_scale": 1.25}')["ui_scale"], 1.25)
        s = self.load('{"ui_scale": 2}')                 # бүхэл тоо ч хүчинтэй
        self.assertEqual(s["ui_scale"], 2.0)
        self.assertIsInstance(s["ui_scale"], float)
        for bad in ('9', '0.1', '"big"', 'true', 'NaN'):
            self.assertEqual(self.load('{"ui_scale": %s}' % bad)["ui_scale"], 1.0, bad)


@unittest.skipUnless(_gui_available(), "tkinter/customtkinter эсвэл дэлгэц байхгүй")
class GuiScaleTest(unittest.TestCase):
    def setUp(self):
        import customtkinter as ctk

        from form_checker.gui import app as appmod

        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        settings = dict(DEFAULTS, source="camera", sound=False, onboarded=True)
        self.saved = {}
        patches = [mock.patch.object(appmod, "load_settings", lambda: dict(settings)),
                   mock.patch.object(appmod, "save_settings", lambda s: self.saved.update(s) or True)]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)
        self.addCleanup(ctk.set_widget_scaling, 1.0)
        self.app = appmod.App(log_dir=tmp.name)
        self.addCleanup(self.app.on_close)
        self.pump(0.5)

    def pump(self, seconds, until=lambda: False):
        end = time.time() + seconds
        while time.time() < end and not until():
            self.app.update()
            time.sleep(0.01)

    def test_hidden_widgets_stay_hidden_after_rescale(self):
        app, home = self.app, self.app.pages["home"]
        for name in ("history", "help", "home"):
            app.show(name)
            self.pump(0.2)
        for source in ("demo", "video", "camera"):
            app.settings["source"] = source
            home._refresh_labels()
        app._on_scale("125%")
        self.pump(0.5)
        self.assertEqual(self.saved.get("ui_scale"), 1.25)
        managed = {k: bool(getattr(p, "_parent_frame", p).winfo_manager()) for k, p in app.pages.items()}
        self.assertEqual(managed, {"home": True, "workout": False, "summary": False, "history": False,
                                   "help": False})
        self.assertFalse(home.demo_lbl.winfo_manager())
        self.assertFalse(home.video_btn.winfo_manager())
        self.assertEqual(home.cam.winfo_manager(), "grid")
        app.show("history")                                  # дахин харуулахад шинэ хэмжээгээр байрлана
        self.pump(0.2)
        self.assertEqual(app.pages["history"]._parent_frame.winfo_manager(), "grid")

    def test_charts_follow_scale(self):
        page = self.app.pages["workout"]
        self.assertEqual(page.trace.s, 1.0)
        self.app._on_scale("150%")
        self.pump(0.3)
        self.assertAlmostEqual(page.trace.s, 1.5)
        self.assertEqual(int(page.trace.cget("height")), round(page.trace.base_height * 1.5))
        self.assertEqual(page.trace.f(12)[1], -18)          # фонт пикселээр, томруулалттай

    def test_camera_scan_fills_menu(self):
        from form_checker.gui import pages

        home = self.app.pages["home"]
        with mock.patch.object(pages, "find_cameras", return_value=[0, 2]):
            home.scan_cameras()
            self.assertTrue(home.scanning)
            self.app.start_workout()                         # хайж байх үед камер зэрэг нээхгүй
            self.assertEqual(self.app.current, "home")
            self.assertIn("хүлээнэ үү", home.notice.cget("text"))
            self.pump(5, lambda: not home.scanning)
        self.assertEqual(home.cam.cget("values"), ["0", "2"])
        self.assertIn("0, 2", home.cam_status.cget("text"))
        self.assertEqual(home.start_btn.cget("state"), "normal")
        self.assertEqual(home.notice.cget("text"), pages.KEY_HINT)  # сануулга арилна

    def test_rep_flash(self):
        from form_checker.gui.theme import GOOD

        page = self.app.pages["workout"]
        page._flash(GOOD)
        self.assertEqual(page.rep_card.cget("border_width"), 3)
        self.pump(1.0)
        self.assertEqual(page.rep_card.cget("border_width"), 1)

    def test_summary_line_follows_choices(self):
        home = self.app.pages["home"]
        home._on_preset("Дунд")
        self.assertIn("3 сет × 10 давталт", home.summary_lbl.cget("text"))
        home.free.select()
        home._on_free()
        self.assertIn("чөлөөт горим", home.summary_lbl.cget("text"))
        self.assertEqual(home.reps.cget("state"), "disabled")
        self.assertTrue(home.goal_note.winfo_manager())     # яагаад идэвхгүй болсныг хэлнэ


if __name__ == "__main__":
    unittest.main()
