"""Дуут дохио: давталт зөв/алдаатай, 3-2-1 тоолол, сет дууссан.

Дасгал хийж байхдаа хүн дэлгэц рүү байнга харж чаддаггүй (ялангуяа push-up хийхэд),
тиймээс гол үйл явдлыг дуугаар давхар мэдэгдэнэ. Нэмэлт сан шаардахгүй:
дууг numpy-гаар WAV файл болгон үүсгээд үйлдлийн системийн тоглуулагчаар тоглуулна
(Windows: winsound, macOS: afplay, Linux: paplay/aplay). Тоглуулах боломжгүй бол чимээгүй ажиллана.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import wave

import numpy as np

SAMPLE_RATE = 22050

# Үйл явдал бүрийн аялгуу: [(давтамж Гц, үргэлжлэх секунд), ...]. 0 Гц = чимээгүй завсар.
TONES = {
    "tick":     [(880, 0.09)],
    "go":       [(1320, 0.28)],
    "depth":    [(1568, 0.05)],                                 # богино өндөр «бип» = зорилтот гүнд хүрлээ
    "good":     [(660, 0.08), (0, 0.02), (990, 0.14)],          # өсөх 2 ая = зөв
    "bad":      [(330, 0.12), (0, 0.04), (247, 0.20)],          # буух намхан 2 ая = алдаатай
    "set_done": [(523, 0.12), (659, 0.12), (784, 0.26)],
    "done":     [(523, 0.12), (659, 0.12), (784, 0.12), (1047, 0.40)],
}

SOUND_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "sounds")


def synth(notes, volume=0.35):
    """Аялгууг 16-битийн PCM дохио болгоно (товшилтгүй байлгахын тулд эхэлж/төгсөхдөө зөөлрүүлнэ)."""
    parts = []
    for freq, dur in notes:
        n = int(SAMPLE_RATE * dur)
        tt = np.arange(n) / SAMPLE_RATE
        if freq <= 0:
            parts.append(np.zeros(n))
            continue
        tone = np.sin(2 * np.pi * freq * tt) + 0.25 * np.sin(4 * np.pi * freq * tt)
        fade = min(n // 4, int(0.01 * SAMPLE_RATE))
        env = np.ones(n)
        env[:fade] = np.linspace(0, 1, fade)
        env[n - fade:] = np.linspace(1, 0, fade)
        parts.append(tone * env / 1.25)
    data = np.concatenate(parts) * volume
    return (np.clip(data, -1, 1) * 32767).astype(np.int16)


def write_wav(path, samples):
    with wave.open(path, "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(SAMPLE_RATE)
        f.writeframes(samples.tobytes())


class SoundPlayer:
    def __init__(self, enabled=True, folder=SOUND_DIR):
        self.enabled = enabled
        self.paths = {}
        self._backend = self._find_backend()
        if self._backend is None:
            self.enabled = False
            return
        for folder_try in (folder, os.path.join(tempfile.gettempdir(), "body_tracking_sounds")):
            try:
                os.makedirs(folder_try, exist_ok=True)
                for name, notes in TONES.items():
                    path = os.path.join(folder_try, f"{name}.wav")
                    if not os.path.exists(path):
                        write_wav(path, synth(notes))
                    self.paths[name] = path
                break
            except OSError:
                self.paths = {}
        if not self.paths:
            self.enabled = False

    @staticmethod
    def _find_backend():
        if sys.platform.startswith("win"):
            try:
                import winsound
                return ("winsound", winsound)
            except ImportError:
                return None
        for cmd in (["afplay"], ["paplay"], ["aplay", "-q"]):
            if shutil.which(cmd[0]):
                return ("cmd", cmd)
        return None

    @property
    def available(self):
        return bool(self.paths)

    def toggle(self):
        if self.available:
            self.enabled = not self.enabled
        return self.enabled

    def play(self, name):
        """Дууг арын горимд (async) тоглуулна: видео боловсруулалтыг зогсоохгүй."""
        if not self.enabled or name not in self.paths:
            return
        kind, backend = self._backend
        try:
            if kind == "winsound":
                backend.PlaySound(self.paths[name],
                                  backend.SND_FILENAME | backend.SND_ASYNC | backend.SND_NODEFAULT)
            else:
                subprocess.Popen(backend + [self.paths[name]], stdout=subprocess.DEVNULL,
                                 stderr=subprocess.DEVNULL)
        except Exception:
            self.enabled = False  # дуу тоглуулж чадахгүй бол цааш оролдохгүй

    def play_events(self, events):
        # Нэг кадрт хэд хэдэн үйл явдал байвал хамгийн чухлыг нь тоглуулна
        for name in ("done", "set_done", "bad", "good", "go", "depth", "tick"):
            if name in events:
                self.play(name)
                return
