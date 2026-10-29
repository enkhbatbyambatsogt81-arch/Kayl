"""Вэбкамераар дасгалын хэлбэрийг бодит хугацаанд шалгах апп.

Ажиллуулах:
    python main.py                      # вэбкамер, squat, 3 сет x 10 давталт
    python main.py --exercise pushup    # push-up
    python main.py --reps 15 --sets 2   # өөр зорилго
    python main.py --reps 0             # чөлөөт горим (зорилго, амралтгүй)
    python main.py --source video.mp4   # бичлэг файл дээр
    python main.py --model full         # илүү нарийвчлалтай (удаан) загвар
    python main.py --source demo        # камергүй үзүүлэн
    python main.py --level strict       # шалгуурын түвшин: easy / normal / strict (2.0)
    python main.py --auto               # дасгалыг биеийн байрлалаар автоматаар таних (2.0)
    python gui.py                       # цонхтой интерфейс (товчлуур, цэс, түүх)

Товчлуур: 1 = squat, 2 = push-up, Space = тоолол/амралтыг алгасах, S = дуу асаах/унтраах,
          E = дасгалыг дуусгаж дүн харах, R = шинээр эхлэх, M = толин дүрс, Q/Esc = гарах
"""

import argparse
import sys

import cv2

from form_checker import safe_console
from form_checker.engine import WorkoutEngine
from form_checker.session import print_summary

WINDOW = "Body Tracking - Form Checker"


def parse_args():
    ap = argparse.ArgumentParser(description="Squat / push-up хэлбэр шалгагч")
    ap.add_argument("--exercise", choices=["squat", "pushup"], default="squat")
    ap.add_argument("--source", default="0",
                    help="камерын дугаар (0, 1, ...), видео файлын зам, эсвэл demo (камергүй үзүүлэн)")
    ap.add_argument("--model", choices=["lite", "full", "heavy"], default="lite",
                    help="lite = хурдан, full = илүү нарийн, heavy = хамгийн нарийн/удаан")
    ap.add_argument("--reps", type=int, default=None,
                    help="нэг сетийн давталтын тоо (камер: 10, видео: 0). 0 = чөлөөт горим")
    ap.add_argument("--sets", type=int, default=3, help="сетийн тоо")
    ap.add_argument("--rest", type=float, default=60, help="сет хоорондын амралт, секунд")
    ap.add_argument("--level", choices=["easy", "normal", "strict"], default="normal",
                    help="шалгуурын түвшин: easy = зөөлөн, normal = энгийн, strict = хатуу")
    ap.add_argument("--auto", action="store_true",
                    help="дасгалыг (squat / push-up) биеийн байрлалаар автоматаар таних")
    ap.add_argument("--mute", action="store_true", help="дуут дохиог унтраах")
    ap.add_argument("--width", type=int, default=1280)
    ap.add_argument("--height", type=int, default=720)
    ap.add_argument("--lang", choices=["mn", "en"], default="mn")
    ap.add_argument("--no-mirror", action="store_true", help="вэбкамерын дүрсийг толин эргүүлэхгүй")
    ap.add_argument("--save", help="үр дүнг видео болгон хадгалах (жишээ: out.mp4)")
    ap.add_argument("--no-display", action="store_true", help="цонх нээхгүй (тест/benchmark-д)")
    return ap.parse_args()


def main():
    args = parse_args()
    kind = "demo" if args.source == "demo" else ("camera" if args.source.isdigit() else "video")
    engine = WorkoutEngine(
        exercise=args.exercise, source=args.source, model=args.model, lang=args.lang,
        workout_cfg=WorkoutEngine.default_config(kind, args.reps, args.sets, args.rest),
        mirror=False if args.no_mirror else None, sound=not args.mute and not args.no_display,
        width=args.width, height=args.height, show_help=not args.no_display,
        realtime=kind == "demo" and not args.no_display, level=args.level, auto_detect=args.auto)
    error = engine.open()
    if error:
        print(error)
        return 1

    writer = None
    if not args.no_display:
        cv2.namedWindow(WINDOW, cv2.WINDOW_NORMAL)
    max_frames = 30 * 60 if kind == "demo" and args.no_display else None  # демо төгсгөлгүй

    while max_frames is None or engine.frame_idx < max_frames:
        ef = engine.step()
        if ef is None:
            break
        if "good" in ef.wv.events or "bad" in ef.wv.events:
            workout = engine.workout
            r = workout.sets[-1][-1]
            status = "ЗӨВ" if r.correct else "АЛДААТАЙ: " + ", ".join(r.issues)
            set_txt = f"сет {ef.wv.set_index}, " if engine.cfg.target_reps > 0 else ""
            print(f"[{ef.exercise}] {set_txt}#{len(workout.sets[-1])}: {status} "
                  f"(хамгийн бага өнцөг {r.min_angle:.0f}°, {r.duration:.1f} с)")

        if args.save:
            if writer is None:
                h, w = ef.image.shape[:2]
                writer = cv2.VideoWriter(args.save, cv2.VideoWriter_fourcc(*"mp4v"), engine.fps, (w, h))
            writer.write(ef.image)

        if args.no_display:
            continue
        cv2.imshow(WINDOW, ef.image)
        key = cv2.waitKey(1) & 0xFF
        if key in (ord("q"), 27):
            break
        if key in (ord("1"), ord("2")):
            engine.set_exercise("squat" if key == ord("1") else "pushup")
        elif key == ord(" "):
            engine.skip()
        elif key == ord("s"):
            engine.toggle_sound()
        elif key == ord("e"):
            engine.finish()
        elif key == ord("r"):
            engine.reset()
        elif key == ord("m"):
            engine.toggle_mirror()
        # Цонхыг X товчоор хаасан бол гарна (хаагдсан цонхонд -1 буцаана)
        if cv2.getWindowProperty(WINDOW, cv2.WND_PROP_AUTOSIZE) < 0:
            break

    if writer is not None:
        writer.release()
    cv2.destroyAllWindows()
    path = engine.close()
    print_summary(engine.workouts.values(), engine.perf, engine.renderer.lang)
    if path:
        print(f"Давталт бүрийн дүнг хадгаллаа: {path}")
    return 0


if __name__ == "__main__":
    safe_console()
    sys.exit(main())
