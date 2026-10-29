@echo off
chcp 65001 >nul
rem Дасгалын хэлбэр шалгагчийг Windows дээр эхлүүлэх (давхар товшоод эсвэл терминалаас).
rem   start_windows.bat                          - цонхтой интерфейс (gui.py)
rem   start_windows.bat main.py --exercise pushup  - командын мөрийн хувилбар
rem Анх удаа .venv хавтас үүсгэж, сангуудыг суулгана (интернэт хэрэгтэй, хэдэн минут болно).
setlocal
cd /d "%~dp0"
set "VPY=.venv\Scripts\python.exe"
if not exist "%VPY%" goto make_venv
"%VPY%" -c "import sys" >nul 2>&1
if not errorlevel 1 goto have_venv
rem Python-ийг устгасан, шинэчилсэн гэх мэтээр .venv ажиллахаа больсон бол дахин үүсгэнэ
echo .venv ажиллахгүй байна, дахин үүсгэнэ...
rmdir /s /q .venv

:make_venv
rem Python 3.10+ (64-bit) хайх: эхлээд py launcher, дараа нь python
set "CHECK=import sys, struct; sys.exit(0 if sys.version_info >= (3, 10) and struct.calcsize('P') == 8 else 1)"
set "PY="
for %%V in (3.12 3.13 3.11 3.10) do (
    if not defined PY (
        py -%%V -c "%CHECK%" >nul 2>&1 && set "PY=py -%%V"
    )
)
if not defined PY (
    python -c "%CHECK%" >nul 2>&1 && set "PY=python"
)
if not defined PY goto no_python

echo [1/2] Виртуал орчин (.venv) үүсгэж байна...
%PY% -m venv .venv
if errorlevel 1 goto venv_failed

:have_venv
"%VPY%" -c "import tkinter" >nul 2>&1
if errorlevel 1 goto no_tk
"%VPY%" -c "import cv2, mediapipe, customtkinter, PIL, numpy" >nul 2>&1
if not errorlevel 1 goto run
echo [2/2] Сангуудыг суулгаж байна (анх удаа хэдэн минут болно)...
"%VPY%" -m pip install --upgrade pip >nul 2>&1
"%VPY%" -m pip install -r requirements.txt
if errorlevel 1 goto pip_failed

:run
if /i "%~x1"==".py" (
    "%VPY%" %*
) else (
    "%VPY%" gui.py %*
)
if errorlevel 1 pause
exit /b

:no_python
echo Python 3.10 эсвэл шинэ (64-bit) хувилбар олдсонгүй.
echo https://www.python.org/downloads/ хуудаснаас Python 3.12-ыг суулгана уу.
echo Суулгахдаа "Add python.exe to PATH"-ийг заавал чагтална. Дараа нь энэ файлыг дахин ажиллуулна.
pause
exit /b 1

:venv_failed
echo .venv үүсгэж чадсангүй. Хавтсанд бичих эрх байгаа эсэхийг шалгана уу.
if exist .venv rmdir /s /q .venv
pause
exit /b 1

:no_tk
echo tkinter (цонхны сан) алга. Python-ийг python.org-оос дахин суулгахдаа "tcl/tk and IDLE"-г чагтална уу.
pause
exit /b 1

:pip_failed
echo Сангуудыг суулгаж чадсангүй. Интернэт холболтоо шалгаад дахин ажиллуулна уу.
pause
exit /b 1
