"""Утасны хувилбарын вэб хэсгийг угсарна: web/ + сангууд + загвар + Python логик -> app/src/main/assets/www/.

    cd android
    npm ci                 # pyodide, @mediapipe/tasks-vision
    python build_web.py    # дараа нь: gradle assembleRelease

Юу хуулагдах вэ:
  web/                          интерфейс (HTML, CSS, JavaScript), вэб / iPhone хувилбарын manifest, дүрс, sw.js
  vendor/pyodide/               Python-ийг WebAssembly дээр ажиллуулагч + numpy
  vendor/mediapipe/             MediaPipe Tasks Vision (биеийн цэг илрүүлэгч)
  models/pose_landmarker_lite.task
  py/app.zip                    form_checker/-ийн шалгах логик (компьютерын хувилбартай нэг код)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import urllib.request
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
APP = os.path.dirname(HERE)                      # body_tracking_app/
OUT = os.path.join(HERE, "app", "src", "main", "assets", "www")
NODE = os.path.join(HERE, "node_modules")
CACHE = os.path.join(HERE, ".cache")

# Утсанд хэрэгтэй Python файлууд. OpenCV, MediaPipe (Python), цонхтой интерфейс хэрэглэдэг файлууд орохгүй.
PY_FILES = [
    "form_checker/__init__.py", "form_checker/config.py", "form_checker/demo.py", "form_checker/geometry.py",
    "form_checker/messages.py", "form_checker/mobile.py", "form_checker/paths.py", "form_checker/pose.py",
    "form_checker/recognition.py", "form_checker/workout.py",
    "form_checker/exercises/__init__.py", "form_checker/exercises/base.py", "form_checker/exercises/pushup.py",
    "form_checker/exercises/squat.py",
    "tools/__init__.py", "tools/synthetic.py",
]
PYODIDE_FILES = ["pyodide.mjs", "pyodide.asm.js", "pyodide.asm.wasm", "python_stdlib.zip", "pyodide-lock.json"]
MEDIAPIPE_FILES = ["vision_bundle.mjs", "wasm/vision_wasm_internal.js", "wasm/vision_wasm_internal.wasm"]


def copy(src, dst):
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copyfile(src, dst)


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def numpy_wheel(pyodide_dir, given=None):
    """numpy-ийн Pyodide хувилбар npm багцад байдаггүй тул Pyodide-ийн CDN-ээс татна (хэш нь lock файлаар шалгагдана)."""
    with open(os.path.join(pyodide_dir, "pyodide-lock.json"), encoding="utf-8") as f:
        lock = json.load(f)
    pkg, version = lock["packages"]["numpy"], lock["info"]["version"]
    path = given or os.path.join(CACHE, pkg["file_name"])
    if not os.path.exists(path):
        url = f"https://cdn.jsdelivr.net/pyodide/v{version}/full/{pkg['file_name']}"
        print(f"[numpy] татаж байна: {url}")
        os.makedirs(CACHE, exist_ok=True)
        urllib.request.urlretrieve(url, path + ".part")
        os.replace(path + ".part", path)
    if sha256(path) != pkg["sha256"]:
        sys.exit(f"numpy-ийн файл эвдэрсэн эсвэл өөр хувилбар байна: {path}")
    return path, pkg["file_name"]


def app_version():
    with open(os.path.join(APP, "form_checker", "__init__.py"), encoding="utf-8") as f:
        for line in f:
            if line.startswith("__version__"):
                return line.split('"')[1]
    sys.exit("form_checker/__init__.py-д __version__ алга")


def write_service_worker(out, version):
    """sw.js (вэб / iPhone хувилбарын service worker)-д хувилбар ба суулгахдаа хадгалах жижиг файлуудын жагсаалтыг бичнэ.
    Хувилбарт файлуудын хэшийг нэмсэн тул аль нэг файл өөрчлөгдөхөд утсан дээрх кэш шинэчлэгдэнэ."""
    web = os.path.join(HERE, "web")
    shell = sorted(os.path.relpath(os.path.join(r, n), web).replace(os.sep, "/")
                   for r, _, names in os.walk(web) for n in names if n != "sw.js")
    shell.append("build.json")
    h = hashlib.sha256()
    for r, dirs, names in os.walk(out):
        dirs.sort()
        for n in sorted(names):
            if n != "sw.js":
                h.update(os.path.relpath(os.path.join(r, n), out).encode())
                h.update(sha256(os.path.join(r, n)).encode())
    path = os.path.join(out, "sw.js")
    with open(path, encoding="utf-8") as f:
        text = f.read()
    text = text.replace("__VERSION__", f"{version}-{h.hexdigest()[:10]}").replace("__SHELL__", json.dumps(shell))
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=OUT, help="гаралтын хавтас")
    ap.add_argument("--numpy-wheel", help="урьдчилан татсан numpy-…-pyodide_…_wasm32.whl (интернэтгүй үед)")
    args = ap.parse_args()
    out = os.path.abspath(args.out)

    pyodide_dir = os.path.join(NODE, "pyodide")
    mediapipe_dir = os.path.join(NODE, "@mediapipe", "tasks-vision")
    for d in (pyodide_dir, mediapipe_dir):
        if not os.path.isdir(d):
            sys.exit(f"{d} алга. Эхлээд android/ хавтсанд `npm ci` ажиллуулна уу.")

    shutil.rmtree(out, ignore_errors=True)
    shutil.copytree(os.path.join(HERE, "web"), out)
    for name in PYODIDE_FILES:
        copy(os.path.join(pyodide_dir, name), os.path.join(out, "vendor", "pyodide", name))
    wheel, wheel_name = numpy_wheel(pyodide_dir, args.numpy_wheel)
    copy(wheel, os.path.join(out, "vendor", "pyodide", wheel_name))
    for name in MEDIAPIPE_FILES:
        copy(os.path.join(mediapipe_dir, name), os.path.join(out, "vendor", "mediapipe", name))
    copy(os.path.join(APP, "models", "pose_landmarker_lite.task"),
         os.path.join(out, "models", "pose_landmarker_lite.task"))

    os.makedirs(os.path.join(out, "py"), exist_ok=True)
    with zipfile.ZipFile(os.path.join(out, "py", "app.zip"), "w", zipfile.ZIP_DEFLATED) as z:
        for name in PY_FILES:
            z.write(os.path.join(APP, name), name)

    version = app_version()
    with open(os.path.join(out, "build.json"), "w", encoding="utf-8") as f:
        json.dump({"version": version}, f)
    write_service_worker(out, version)
    size = sum(os.path.getsize(os.path.join(r, n)) for r, _, names in os.walk(out) for n in names)
    print(f"OK: v{version} -> {out} ({size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
