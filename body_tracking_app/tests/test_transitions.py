"""3.1: хуудас хооронд зөөлөн шилжих.

Шинэ хуудас хуучныхаа доор зурагдаж бэлэн болоод нэг дор солигдоно (хагас зурагдсан хуудас харагдахгүй),
дараа нь хэдэн пикселээс зөөлөн гулсаж байрандаа сууна. Зүүн цэсийг нуудаггүй, давхаргаар л солино.
Ажиллуулах:  python -m unittest discover -s tests -v
"""

import os
import sys
import tempfile
import time
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from form_checker.gui.transitions import ease_out  # noqa: E402
from form_checker.settings import DEFAULTS  # noqa: E402
from test_app import _gui_available  # noqa: E402


class EaseTest(unittest.TestCase):
    def test_ease_out_starts_fast_and_lands_softly(self):
        self.assertEqual((ease_out(0.0), ease_out(1.0)), (0.0, 1.0))
        self.assertGreater(ease_out(0.25), 0.5)          # эхэндээ хурдан
        self.assertLess(ease_out(1.0) - ease_out(0.9), 0.01)   # төгсгөлдөө аажим


def _frame(page):
    return getattr(page, "_parent_frame", page)


def _stack(parent):
    """Давхарлалтын дараалал: хамгийн доод нь эхэнд (Tk-ийн winfo children)."""
    return [str(w) for w in parent.winfo_children()]


@unittest.skipUnless(_gui_available(), "tkinter/customtkinter эсвэл дэлгэц байхгүй")
class PageTransitionTest(unittest.TestCase):
    def setUp(self):
        from form_checker.gui import app as appmod

        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        settings = dict(DEFAULTS, source="camera", sound=False, onboarded=True)
        patches = [mock.patch.object(appmod, "load_settings", lambda: dict(settings)),
                   mock.patch.object(appmod, "save_settings", lambda s: True)]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)
        self.app = appmod.App(log_dir=tmp.name)
        self.addCleanup(self.app.on_close)
        self.pump(0.5)

    def pump(self, seconds, until=lambda: False):
        end = time.time() + seconds
        while time.time() < end and not until():
            self.app.update()
            time.sleep(0.01)

    def settle(self):
        app = self.app
        self.pump(2, lambda: (app._transition is None or app._transition.done)
                  and (app.pages["start"]._slide is None or app.pages["start"]._slide.done))

    def placed(self):
        return {k for k, p in self.app.pages.items() if _frame(p).winfo_manager()}

    def test_new_page_is_drawn_underneath_then_swapped_in_and_slides_to_place(self):
        app = self.app
        app.show("home")
        self.settle()
        self.assertEqual(self.placed(), {"home"})
        home, hist = app.pages["home"], app.pages["history"]
        app.show("history")
        # шилжилтийн эхэнд: шинэ хуудас байрласан ч хуучных нь дээр нь хэвээр
        self.assertEqual(self.placed(), {"home", "history"})
        stack = _stack(app.content_area)
        self.assertLess(stack.index(str(_frame(hist))), stack.index(str(home)))
        self.assertEqual(app.current, "history")
        self.settle()
        self.assertEqual(self.placed(), {"history"})
        info = _frame(hist).place_info()
        self.assertEqual((int(float(info["x"])), int(float(info["y"]))), (0, 0))   # байрандаа суусан
        self.assertEqual(float(info["relwidth"]), 1.0)

    def test_slide_moves_the_page_from_below(self):
        from form_checker.gui.transitions import Transition, place_fill

        app = self.app
        page = app.pages["help"]
        place_fill(page)
        tr = Transition(app, page, lambda: None, dy=16, prepare_ms=0, slide_ms=5000)
        self.pump(0.15)
        y = int(float(_frame(page).place_info()["y"]))
        self.assertTrue(0 < y <= 16, y)                    # хөдөлж байна
        tr.finish()
        self.assertEqual(int(float(_frame(page).place_info()["y"])), 0)
        self.assertTrue(tr.done and tr.revealed)

    def test_rapid_clicks_end_on_the_last_page(self):
        app = self.app
        app.show("home")
        for name in ("history", "help", "history", "help"):
            app.show(name)
        self.settle()
        self.assertEqual(app.current, "help")
        self.assertEqual(self.placed(), {"help"})

    def test_sidebar_stays_put_and_full_pages_cover_it(self):
        app = self.app
        self.assertEqual(app.current, "start")
        stack = _stack(app)
        self.assertGreater(stack.index(str(app.full)), stack.index(str(app.sidebar)))
        self.assertGreater(stack.index(str(app.full)), stack.index(str(app.content)))
        self.assertLess(stack.index(str(app.full)), stack.index(str(app.onboarding)))  # танилцуулга дээр нь
        sidebar_w = app.sidebar.winfo_width()
        app.show("home")
        self.settle()
        stack = _stack(app)
        self.assertLess(stack.index(str(app.full)), stack.index(str(app.sidebar)))
        self.assertEqual(app.sidebar.winfo_manager(), "grid")   # цэс хэзээ ч нуугдаагүй
        self.assertEqual(app.sidebar.winfo_width(), sidebar_w)
        app.show("start")
        self.settle()
        self.assertEqual(self.placed(), {"start"})
        self.assertGreater(_stack(app).index(str(app.full)), _stack(app).index(str(app.sidebar)))

    def test_start_steps_slide_forward_and_back(self):
        app, flow = self.app, self.app.pages["start"]
        steps = lambda: {k for k, f in flow.frames.items() if f.winfo_manager()}  # noqa: E731
        self.assertEqual(steps(), {"welcome"})
        flow.next()
        self.assertEqual(flow.step, "level")
        self.assertEqual(steps(), {"welcome", "level"})    # бэлтгэж байна
        self.settle()
        self.assertEqual(steps(), {"level"})
        self.assertEqual(flow.back_btn.winfo_manager(), "grid")
        self.assertEqual(flow.next_btn.cget("text"), "Үргэлжлүүлэх  →")
        flow.next()
        flow.back()                                        # хурдан дарсан ч зөв алхам дээр зогсоно
        self.settle()
        self.assertEqual((flow.step, steps()), ("level", {"level"}))
        flow.back()
        self.settle()
        self.assertEqual(steps(), {"welcome"})
        self.assertFalse(flow.back_btn.winfo_manager())
        self.assertEqual(int(float(flow.frames["welcome"].place_info()["x"])), 0)
        app.show("home")
        app.show("start")                                  # «Эхлэх»: урсгал эхний алхмаасаа
        self.settle()
        self.assertEqual((flow.step, steps()), ("welcome", {"welcome"}))


if __name__ == "__main__":
    unittest.main()
