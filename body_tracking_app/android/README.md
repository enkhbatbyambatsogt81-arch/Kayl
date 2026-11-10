# Ухаалаг дасгалжуулагч — Android хувилбар

Утсан дээр ажилладаг APK. Бэлэн файлыг <https://github.com/enkhbatbyambatsogt81-arch/Kayl/releases/latest>
хуудасны **Assets** хэсгээс (`UkhaalagDasgaljuulagch-…-android.apk`) татна.

## Суулгах

1. APK файлыг утсаараа татна (эсвэл компьютерээс утас руугаа хуулна).
2. Файлыг нээхэд «Аюулгүй байдлын үүднээс энэ эх сурвалжаас апп суулгахыг хориглосон» гэвэл **Тохиргоо →
   Энэ эх сурвалжаас зөвшөөрөх** (Allow from this source)-ийг асаагаад буцаж **Суулгах** дарна.
   «Play Protect» анхааруулбал **Дэлгэрэнгүй → Ямар ч байсан суулгах** (More details → Install anyway).
3. Аппыг нээж, камерын зөвшөөрөлд **Апп ашиглах үед** (While using the app) дарна.

Android 7.0 ба түүнээс дээш. Интернэт шаардахгүй: видео утаснаас гардаггүй, хаашаа ч илгээгддэггүй. Анх нээхэд
шалгах логик ачаалагдтал хэдэн секунд болно. Апп нээгдэхгүй, эсвэл хоосон дэлгэц гарвал Play Store-оос
**Android System WebView** болон **Chrome**-оо шинэчилнэ.

Утсаа ширээ, тавиур эсвэл хананд налуулж тавиад 2–3 метр холдож, бүтэн биеэ харагдуулна. Суниалтад утсаа хэвтээ
байрлалаар тавибал амар. Камергүйгээр үзэх бол **Тохиргоо → Эх үүсвэр → Демо**.

## Хэрхэн ажилладаг вэ

```
камер ──> MediaPipe Pose Landmarker (JavaScript, утасны видео карт) ──> 33 цэг
      ──> form_checker/mobile.py (Python, Pyodide дээр) ──> тоолуур, зөвлөмж, оноо ──> дэлгэц, дуу
```

- **Шалгах логик нь компьютерын хувилбартай нэг код.** `form_checker/exercises/`, `workout.py`, `recognition.py`
  зэрэг Python файлууд өөрчлөлтгүйгээр утсан дээр [Pyodide](https://pyodide.org) (WebAssembly дээрх Python)-оор
  ажиллана. Тиймээс суулт, суниалтын дүрэм, босго, оноо компьютер дээрхтэй яг ижил; дүрмийг нэг газар засахад
  хоёр хувилбарт хоёуланд нь орно. `tests/test_mobile.py` нь утасны хөдөлгүүр компьютерынхтай кадр бүрээр ижил
  үр дүн гаргаж буйг шалгадаг.
- **Интерфейс** нь `web/` доторх HTML / CSS / JavaScript (сан ашиглаагүй). Камер, биеийн цэг илрүүлэлт
  ([MediaPipe Tasks Vision](https://ai.google.dev/edge/mediapipe/solutions/vision/pose_landmarker/web_js)), зураглал,
  дуут дохио (WebAudio) энд байна. Тохиргоо, түүх утсанд (localStorage) хадгалагдана.
- **Android бүрхүүл** (`app/src/main/java/…/MainActivity.java`) нь энэ хуудсыг WebView-д нээж, камерын зөвшөөрөл
  асууж, дэлгэцийг асаалттай байлгана. Апп доторх файлаас бусад бүх сүлжээний хүсэлтийг хаадаг.

| Хавтас / файл | Юу вэ |
|---|---|
| `web/` | Интерфейс: `js/app.js` (хуудсууд), `js/workout.js` (дасгалын дэлгэц), `js/engine.js` (Pyodide, MediaPipe, камер), `js/draw.js`, `js/audio.js`, `js/store.js` |
| `build_web.py` | `web/` + Pyodide + MediaPipe + загвар + Python логикийг `app/src/main/assets/www/` руу угсарна |
| `app/` | Android төсөл (Gradle): `MainActivity.java`, дүрс, `AndroidManifest.xml` |
| `make_icons.py` | Аппын дүрсийг зурна |
| `ci_emulator_test.sh` | GitHub Actions дээр APK-г Android эмуляторт суулгаж ажиллуулж шалгана |
| `sideload.keystore` | APK-д гарын үсэг зурах түлхүүр (доор тайлбартай) |

## Өөрөө угсрах

GitHub Actions автоматаар угсардаг ([`release.yml`](../../.github/workflows/release.yml)-ийн `android` ажил).
Өөрийн компьютер дээр: Node.js 18+, Python 3.10+, JDK 17, Gradle 8.9+, Android SDK (platform 34) хэрэгтэй.

```bash
cd body_tracking_app/android
npm ci                      # pyodide, @mediapipe/tasks-vision
python build_web.py         # -> app/src/main/assets/www/  (numpy-г Pyodide-ийн CDN-ээс нэг удаа татна)
gradle assembleRelease      # -> app/build/outputs/apk/release/app-release.apk
```

Интерфейсийг утасгүйгээр хөтөч дээр үзэх: `python build_web.py` хийсний дараа
`python -m http.server 8765 -d app/src/main/assets/www` → <http://127.0.0.1:8765>. Хөтчийн хөгжүүлэгчийн
хэрэгслээр утасны хэмжээг сонгоно. `?delegate=cpu` нэмбэл илрүүлэгч процессороор ажиллана.

Утсан дээрх аппыг шалгах: утсаа USB-ээр холбоод компьютерын Chrome-д `chrome://inspect` нээвэл аппын консол,
алдааг харж болно.

## Гарын үсгийн түлхүүр

Android нь шинэ хувилбарыг хуучных нь дээр (тохиргоо, түүхээ алдалгүй) суулгахын тулд хоёулаа **ижил түлхүүрээр**
гарын үсэг зурагдсан байхыг шаарддаг. Апп Play Store-оор биш, APK файлаар тардаг тул түлхүүрийг
(`sideload.keystore`, нууц үг нь `app/build.gradle`-д) репод хадгалсан: хэн ч, GitHub Actions ч ижил APK угсарч
чадна. Энэ нь түлхүүр нууц биш гэсэн үг тул APK-г зөвхөн энэ репогийн Releases хуудаснаас татна уу. Play Store-д
гаргах болбол шинэ, нууц түлхүүр үүсгэж, `applicationId`-г солино.
