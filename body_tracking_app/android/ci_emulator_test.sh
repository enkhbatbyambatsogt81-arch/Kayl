#!/usr/bin/env bash
# GitHub Actions-ийн Android эмулятор дээр APK-г суулгаж, үнэхээр ажиллаж буйг шалгана (release.yml: android-test).
#
#   bash ci_emulator_test.sh <app.apk> [гаралтын хавтас]
#
# Апп ?selftest=1 горимд төлөвөө секунд тутам консолд бичдэг; Android дээр консол logcat-д гардаг тул эндээс уншина.
#   1. Эхлэх хуудас нээгдэж буй эсэх (дэлгэцийн зураг)
#   2. Демо горим: Python логик ачаалагдаж, зохиомол хүний давталтыг тоолж буй эсэх
#   3. Камер: зөвшөөрөл, камер, биеийн цэг илрүүлэгч (процессороор) кадр боловсруулж буй эсэх
#   4. Илрүүлэгч видео картаар: эмуляторт жинхэнэ видео карт байхгүй тул зөвхөн мэдээлэл
# 2 эсвэл 3 амжилтгүй бол алдаа буцаана.
set -u
APK="$1"
OUT="${2:-emulator-out}"
PKG=mn.dasgaljuulagch.app
mkdir -p "$OUT"

adb install -r "$APK" || exit 1
adb shell pm grant "$PKG" android.permission.CAMERA
adb shell dumpsys package com.google.android.webview | grep -m1 versionName || true

launch() {   # $1: am start-ийн нэмэлт аргумент
  adb shell am force-stop "$PKG"
  adb logcat -c
  adb shell "am start -W -n $PKG/.MainActivity $1"
}

status() {   # сүүлийн SELFTEST мөрийн JSON
  adb logcat -d | sed -n 's/.*"SELFTEST \(.*\)", source:.*/\1/p' | tail -1
}

wait_for() {   # $1: Python илэрхийлэл (s = төлөв), $2: хамгийн ихдээ хэдэн секунд
  local deadline=$((SECONDS + $2)) line=""
  while [ $SECONDS -lt $deadline ]; do
    line="$(status)"
    if [ -n "$line" ] && python3 -c "import json, sys; s = json.loads(sys.argv[1]); sys.exit(0 if ($1) else 1)" "$line" 2>/dev/null; then
      echo "$line"
      return 0
    fi
    sleep 3
  done
  echo "$line"
  return 1
}

shot() {   # дэлгэцийн зураг: файлд, мөн жижигрүүлж логт (base64) хэвлэнэ
  adb exec-out screencap -p > "$OUT/$1.png" || return 0
  if command -v convert > /dev/null; then
    echo "B64BEGIN $1"
    convert "$OUT/$1.png" -resize 360x -quality 55 jpg:- | base64 -w 2000
    echo "B64END $1"
  fi
}

console() {   # аппын консол, WebView-ийн мөрүүд (SELFTEST-ээс бусад)
  adb logcat -d > "$OUT/$1.log"
  grep -E "chromium|CONSOLE|cr_|WebView|AndroidRuntime" "$OUT/$1.log" | grep -v SELFTEST | cut -c1-400 | tail -${2:-25}
}

echo "== 1. Эхлэх хуудас"
launch ""
sleep 12
shot 1_welcome
console 1_welcome 10

echo "== 2. Демо горим (камергүй)"
launch "--es open '?selftest=1&demo=1#/workout'"
if wait_for "s['phase'] is not None" 180; then
  echo "Python логик ачаалагдаж, кадр боловсруулж байна"
fi
shot 2_demo_start
demo=1
if wait_for "(s['reps'] or 0) >= 2" 120; then
  demo=0
  echo "OK: демо горимд давталт тоолж байна"
else
  echo "АЛДАА: демо горимд давталт тоологдсонгүй"
fi
shot 2_demo
console 2_demo

# Эмуляторт жинхэнэ видео карт байхгүй (програмаар дуурайдаг) тул илрүүлэгчийг процессороор ажиллуулж шалгана
echo "== 3. Камер (илрүүлэгч процессороор)"
launch "--es open '?selftest=1&demo=0&delegate=cpu#/workout'"
camera=1
if wait_for "s['phase'] is not None" 240; then
  camera=0
  echo "OK: камер нээгдэж, биеийн цэг илрүүлэгч кадр боловсруулж байна"
else
  echo "АЛДАА: камерын горимд кадр боловсруулагдсангүй"
fi
sleep 6
status
shot 3_camera
console 3_camera

echo "== 4. Камер (илрүүлэгч видео картаар; эмуляторт зөвхөн мэдээлэл)"
launch "--es open '?selftest=1&demo=0#/workout'"
wait_for "s['phase'] is not None or s['error']" 150 || echo "Анхаар: видео картаар (эмуляторын програм хангамжийн GL) ачаалагдаж амжсангүй"
shot 4_camera_gpu
console 4_camera_gpu

echo "demo=$demo camera=$camera"
exit $((demo + camera))
