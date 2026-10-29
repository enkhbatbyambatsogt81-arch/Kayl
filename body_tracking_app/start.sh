#!/usr/bin/env bash
# Дасгалын хэлбэр шалгагчийг macOS / Linux дээр эхлүүлэх.
#
#   bash start.sh                          # цонхтой интерфейс (gui.py)
#   bash start.sh main.py --exercise pushup  # командын мөрийн хувилбар, дурын тохиргоотой
#
# Анх удаа .venv хавтас үүсгэж, сангуудыг суулгана (интернэт хэрэгтэй, хэдэн минут болно).
# Дараагийн удаа шууд нээгдэнэ.
set -eu
cd "$(dirname "$0")"

OS="$(uname -s)"
ARCH="$(uname -m)"

say() { printf '%s\n' "$*"; }

python_ok() {  # Python 3.10 ба түүнээс шинэ
    "$1" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' >/dev/null 2>&1
}

find_python() {
    for cmd in python3.12 python3.13 python3.11 python3.10 python3 python; do
        if command -v "$cmd" >/dev/null 2>&1 && python_ok "$cmd"; then
            printf '%s' "$cmd"
            return 0
        fi
    done
    return 1
}

if [ -e .venv ] && ! .venv/bin/python -c 'import sys' >/dev/null 2>&1; then
    say ".venv ажиллахгүй байна (Python-ийг устгасан эсвэл шинэчилсэн), дахин үүсгэнэ..."
    rm -rf .venv
fi
if [ ! -x .venv/bin/python ]; then
    if ! PY="$(find_python)"; then
        say "Python 3.10 эсвэл шинэ хувилбар олдсонгүй."
        if [ "$OS" = "Darwin" ]; then
            say "https://www.python.org/downloads/ хуудаснаас Python 3.12-ыг суулгаад дахин ажиллуулна уу."
        else
            say "Ubuntu/Debian: sudo apt install python3 python3-venv python3-tk"
            say "Fedora:        sudo dnf install python3 python3-tkinter"
        fi
        exit 1
    fi
    # Intel (x86_64) Mac-д mediapipe зөвхөн Python 3.12 хүртэлх хувилбарт байдаг
    if [ "$OS" = "Darwin" ] && [ "$ARCH" = "x86_64" ] && \
       ! "$PY" -c 'import sys; sys.exit(0 if sys.version_info < (3, 13) else 1)'; then
        say "Intel Mac дээр mediapipe нь Python 3.10–3.12-т л суудаг. Одоо: $("$PY" --version)."
        say "https://www.python.org/downloads/ хуудаснаас Python 3.12-ыг суулгаад дахин ажиллуулна уу."
        exit 1
    fi
    say "[1/2] Виртуал орчин (.venv) үүсгэж байна: $("$PY" --version)"
    if ! "$PY" -m venv .venv; then
        rm -rf .venv
        say "venv үүсгэж чадсангүй. Ubuntu/Debian: sudo apt install python3-venv"
        exit 1
    fi
fi
VPY=.venv/bin/python

if ! "$VPY" -c 'import tkinter' >/dev/null 2>&1; then
    say "tkinter (цонхны сан) алга."
    if [ "$OS" = "Darwin" ]; then
        say "Homebrew-ийн Python бол: brew install python-tk@3.12  (эсвэл python.org-ийн Python ашиглана)"
    else
        say "Ubuntu/Debian: sudo apt install python3-tk    Fedora: sudo dnf install python3-tkinter"
    fi
    exit 1
fi

if ! "$VPY" -c 'import cv2, mediapipe, customtkinter, PIL, numpy' >/dev/null 2>&1; then
    say "[2/2] Сангуудыг суулгаж байна (анх удаа хэдэн минут болно)..."
    "$VPY" -m pip install --upgrade pip >/dev/null 2>&1 || true
    "$VPY" -m pip install -r requirements.txt
fi

# Linux: MediaPipe-д OpenGL (libEGL) сан хэрэгтэй. Байхгүй бол дасгал эхлэхэд алдаа гарна.
if [ "$OS" = "Linux" ]; then
    LDCONFIG="$(command -v ldconfig 2>/dev/null || printf '/sbin/ldconfig')"
    if [ -x "$LDCONFIG" ] && ! "$LDCONFIG" -p 2>/dev/null | grep -q 'libEGL\.so\.1'; then
        say "Анхааруулга: libEGL.so.1 олдсонгүй. Ubuntu/Debian: sudo apt install libegl1 libgl1"
    fi
fi

if [ "$#" -gt 0 ] && [ "${1%.py}" != "$1" ]; then
    exec "$VPY" "$@"
fi
exec "$VPY" gui.py "$@"
