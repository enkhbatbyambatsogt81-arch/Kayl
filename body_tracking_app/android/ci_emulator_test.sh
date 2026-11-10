#!/usr/bin/env bash
# GitHub Actions-ийн Android эмулятор дээр APK-г суулгаж, үнэхээр ажиллаж буйг шалгана (release.yml: android-test).
#
#   bash ci_emulator_test.sh <app.apk> [гаралтын хавтас]
#
# Апп ?selftest=1 горимд төлөвөө секунд тутам консолд бичдэг; Android дээр консол logcat-д гардаг тул эндээс уншина.
#   1. Эхлэх хуудас нээгдэж буй эсэх (дэлгэцийн зураг)
#   2. Демо горим: Python логик ачаалагдаж, зохиомол хүний давталтыг тоолж буй эсэх  <- амжилтгүй бол алдаа буцаана
#   3. Камер: зөвшөөрөл, камер, биеийн цэг илрүүлэгч ачаалагдаж, кадр боловсруулж буй эсэх (эмуляторын камер, GPU
#      тогтворгүй байж болох тул зөвхөн мэдээлэл)
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

shot() {
  adb exec-out screencap -p > "$OUT/$1.png" || true
}

echo "== 1. Эхлэх хуудас"
launch ""
sleep 12
shot 1_welcome
adb logcat -d > "$OUT/1_welcome.log"

echo "== 2. Демо горим (камергүй)"
launch "--es open '?selftest=1&demo=1#/workout'"
if wait_for "s['phase'] is not None" 150; then
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
adb logcat -d > "$OUT/2_demo.log"

echo "== 3. Камер"
launch "--es open '?selftest=1&demo=0#/workout'"
if wait_for "s['phase'] is not None or s['error'] or 'error' in (s['state'] or {}).get('panel', '')" 150; then
  echo "Камерын горимын төлөв дээр хэвлэгдлээ"
else
  echo "Анхаар: камерын горимд кадр боловсруулагдсангүй"
fi
sleep 5
status
shot 3_camera
adb logcat -d > "$OUT/3_camera.log"

grep -h "SELFTEST" "$OUT"/*.log | sed -n 's/.*"SELFTEST \(.*\)", source:.*/\1/p' | tail -3
exit $demo
