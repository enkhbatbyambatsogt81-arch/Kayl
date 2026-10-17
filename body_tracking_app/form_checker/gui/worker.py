"""Камер + MediaPipe-ийг тусдаа урсгалд (thread) ажиллуулна: цонх гацахгүй.

Tkinter-ийн элементүүдийг зөвхөн үндсэн урсгалаас өөрчилж болдог тул энэ урсгал зөвхөн
өгөгдөл (сүүлийн кадр, дасгалын төлөв) бэлдэж, цонх 15 ms тутам түүнийг уншина.
"""

from __future__ import annotations

import threading
import time

import cv2


class EngineWorker(threading.Thread):
    def __init__(self, engine):
        super().__init__(daemon=True)
        self.engine = engine
        self.target_size = (960, 540)
        self.lock = threading.Lock()
        self.latest = None          # (RGB зураг, EngineFrame)
        self.seq = 0
        self.running = True
        self.opened = False
        self.error = None
        self.ended = False
        self.csv_path = None

    def run(self):
        try:
            self.error = self.engine.open()
            if self.error:
                return
            self.opened = True
            while self.running:
                if self.engine.paused:
                    time.sleep(0.03)
                    continue
                ef = self.engine.step()
                if ef is None:
                    self.ended = True
                    break
                rgb = self._fit(ef.image)
                with self.lock:
                    self.latest = (rgb, ef)
                    self.seq += 1
        except Exception as e:  # камер салсан гэх мэт
            self.error = f"Алдаа гарлаа: {e}"
        finally:
            try:
                self.csv_path = self.engine.close()
            except Exception:
                self.csv_path = None

    def _fit(self, img):
        tw, th = self.target_size
        h, w = img.shape[:2]
        scale = min(tw / w, th / h)
        if abs(scale - 1) > 0.02 and tw > 10 and th > 10:
            img = cv2.resize(img, (max(1, int(w * scale)), max(1, int(h * scale))),
                             interpolation=cv2.INTER_AREA if scale < 1 else cv2.INTER_LINEAR)
        return cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

    def get(self, last_seq):
        with self.lock:
            if self.seq == last_seq:
                return None, last_seq
            return self.latest, self.seq

    def stop(self, timeout=3.0):
        self.running = False
        if self.is_alive():
            self.join(timeout)
