"""Өмнөх дасгалуудын түүх: logs/session_*.csv файлуудыг уншиж нэгтгэнэ."""

from __future__ import annotations

import csv
import glob
import os
import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime

from .session import LOG_DIR


@dataclass
class SessionRecord:
    when: datetime
    exercise: str
    reps: int
    correct: int
    sets: int
    issues: Counter = field(default_factory=Counter)
    avg_duration: float = 0.0
    path: str = ""
    avg_score: float | None = None   # 2.0-оос өмнөх логт оноо байхгүй
    level: str = "normal"

    @property
    def accuracy(self):
        return self.correct / self.reps if self.reps else 0.0


def _parse_time(path):
    m = re.search(r"session_(\d{8}_\d{6})", os.path.basename(path))
    if m:
        return datetime.strptime(m.group(1), "%Y%m%d_%H%M%S")
    return datetime.fromtimestamp(os.path.getmtime(path))


def _float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def load_history(folder=LOG_DIR) -> list[SessionRecord]:
    """Шинэ нь эхэндээ байхаар эрэмбэлсэн жагсаалт. Нэг файлд хоёр дасгал байвал тус тусдаа мөр болно."""
    records = []
    for path in glob.glob(os.path.join(folder, "session_*.csv")):
        try:
            with open(path, newline="", encoding="utf-8-sig") as f:
                rows = list(csv.DictReader(f))
        except (OSError, csv.Error, UnicodeDecodeError):
            continue
        by_ex = {}
        for row in rows:
            by_ex.setdefault(row.get("exercise", "?"), []).append(row)
        when = _parse_time(path)
        for ex, ex_rows in by_ex.items():
            correct = sum(r.get("correct") in ("True", "1", "true") for r in ex_rows)
            issues = Counter(i for r in ex_rows for i in (r.get("issues") or "").split(";") if i)
            durations = [d for d in (_float(r.get("duration_s")) for r in ex_rows) if d is not None]
            sets = len({r.get("set", "1") for r in ex_rows})  # 1.0 хувилбарын логт "set" багана байхгүй
            avg = sum(durations) / len(durations) if durations else 0.0
            scores = [v for v in (_float(r.get("score")) for r in ex_rows) if v is not None]
            level = next((r.get("level") for r in ex_rows if r.get("level")), "normal")
            records.append(SessionRecord(when=when, exercise=ex, reps=len(ex_rows), correct=correct, sets=sets,
                                         issues=issues, avg_duration=avg, path=path,
                                         avg_score=sum(scores) / len(scores) if scores else None, level=level))
    records.sort(key=lambda r: r.when, reverse=True)
    return records


def compare_with_history(records, exercise, reps, correct, exclude_path=None, min_reps=3):
    """Дөнгөж хийсэн дасгалыг өмнөхтэй нь харьцуулна (дүнгийн хуудсанд урам өгөх зорилготой).

    records: load_history()-ийн үр дүн (шинэ нь эхэндээ). exclude_path: одоогийн дасгалын CSV (түүхэнд
    аль хэдийн бичигдсэн байдаг тул хасна). Буцаах dict: previous (SessionRecord эсвэл None),
    best_accuracy (өмнөх дасгалуудын, min_reps-ээс цөөн давталттайг тооцохгүй), best_correct,
    new_best (нарийвчлал эсвэл зөв давталтын тоогоор өмнөх бүх дасгалаас давсан эсэх).
    """
    skip = os.path.abspath(exclude_path) if exclude_path else None
    past = [r for r in records if r.exercise == exercise and (skip is None or os.path.abspath(r.path) != skip)]
    counted = [r for r in past if r.reps >= min_reps]
    best_acc = max((r.accuracy for r in counted), default=None)
    best_correct = max((r.correct for r in past), default=None)
    accuracy = correct / reps if reps else 0.0
    acc_best = reps >= min_reps and best_acc is not None and accuracy > best_acc
    new_best = bool(past) and (acc_best or correct > best_correct)
    return {"previous": past[0] if past else None, "best_accuracy": best_acc, "best_correct": best_correct,
            "new_best": new_best}
