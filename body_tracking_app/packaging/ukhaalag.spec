# -*- mode: python ; coding: utf-8 -*-
# «Ухаалаг дасгалжуулагч»-ийг Python суулгахгүйгээр ажилладаг бэлэн файл болгон угсрах (PyInstaller).
#
#   python -m pip install -r requirements.txt pyinstaller
#   python -m PyInstaller packaging/ukhaalag.spec --noconfirm
#
# Үр дүн: dist/UkhaalagDasgaljuulagch/ (Windows, Linux) эсвэл dist/UkhaalagDasgaljuulagch.app (macOS).
# Файл бүр зөвхөн угсарсан үйлдлийн системдээ ажиллана. Гурван системийн файлыг
# .github/workflows/release.yml автоматаар угсарч GitHub Releases-д байршуулна.
import os
import sys

from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs, collect_submodules

ROOT = os.path.dirname(SPECPATH)  # noqa: F821  (PyInstaller өгнө)
sys.path.insert(0, ROOT)
from form_checker import __version__  # noqa: E402

NAME = "UkhaalagDasgaljuulagch"
TITLE = "Ухаалаг дасгалжуулагч"


def make_icons():
    """Аппын цонхны дүрсийг (хар дөрвөлжин дээр squat) .ico / .icns болгоно."""
    try:
        from form_checker.gui.app import app_icon
    except Exception as e:  # noqa: BLE001
        print(f"[icon] алгаслаа: {e}")
        return None
    out = os.path.join(workpath, "icon")  # noqa: F821
    os.makedirs(out, exist_ok=True)
    img = app_icon(1024)
    if sys.platform == "win32":
        path = os.path.join(out, "app.ico")
        img.save(path, sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    elif sys.platform == "darwin":
        path = os.path.join(out, "app.icns")
        img.save(path)
    else:
        return None
    return path


datas = [
    (os.path.join(ROOT, "models", "pose_landmarker_lite.task"), "models"),
    (os.path.join(ROOT, "models", "pose_landmarker_full.task"), "models"),
    (os.path.join(ROOT, "sounds"), "sounds"),
]
datas += collect_data_files("customtkinter")
binaries = collect_dynamic_libs("mediapipe")
hiddenimports = (
    ["tools", "tools.synthetic", "PIL._tkinter_finder", "mediapipe.tasks.c"]
    + collect_submodules("mediapipe.tasks.python", filter=lambda m: ".test" not in m)
)

a = Analysis(  # noqa: F821
    [os.path.join(ROOT, "gui.py")],
    pathex=[ROOT],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    excludes=["pytest", "IPython", "jupyter", "notebook", "pandas", "scipy", "torch", "tensorflow", "jax"],
    noarchive=False,
)
pyz = PYZ(a.pure)  # noqa: F821
icon = make_icons()
exe = EXE(  # noqa: F821
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=NAME,
    console=False,
    icon=icon,
    upx=False,
)
coll = COLLECT(exe, a.binaries, a.datas, name=NAME, upx=False)  # noqa: F821

if sys.platform == "darwin":
    app = BUNDLE(  # noqa: F821
        coll,
        name=f"{NAME}.app",
        icon=icon,
        bundle_identifier="mn.kayl.ukhaalagdasgaljuulagch",
        version=__version__,
        info_plist={
            "CFBundleDisplayName": TITLE,
            "CFBundleName": TITLE,
            "CFBundleShortVersionString": __version__,
            "NSCameraUsageDescription": "Дасгалын хөдөлгөөнийг бодит хугацаанд шалгахын тулд камер ашиглана.",
            "NSHighResolutionCapable": True,
            "LSMinimumSystemVersion": "11.0",
        },
    )
