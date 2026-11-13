## Татаж аваад шууд ажиллуулах

Python суулгах шаардлагагүй. Доорх **Assets** хэсгээс системдээ тохирох файлыг татна уу.

| Систем | Файл |
|---|---|
| Windows 10 / 11 (64-bit) | `UkhaalagDasgaljuulagch-…-windows-x64.zip` |
| macOS, Apple Silicon (M1–M4) | `UkhaalagDasgaljuulagch-…-macos-apple-silicon.zip` |
| macOS, Intel | `UkhaalagDasgaljuulagch-…-macos-intel.zip` (байхгүй бол эх кодоос `bash start.sh`) |
| Linux x86_64 | `UkhaalagDasgaljuulagch-…-linux-x64.tar.gz` |
| **Android утас** (7.0+) | `UkhaalagDasgaljuulagch-…-android.apk` |
| **iPhone / iPad** (iOS 16.4+) | файл хэрэггүй: Safari-аар <https://enkhbatbyambatsogt81-arch.github.io/Kayl/> нээнэ |

**Windows:** ZIP-ээ задлаад `UkhaalagDasgaljuulagch.exe`-г давхар товшино. «Windows protected your PC» гарвал
**More info → Run anyway** дарна.

**macOS:** ZIP-ээ задлаад `UkhaalagDasgaljuulagch.app`-ийг Applications руу чирээд нээнэ. «Apple could not verify»
гарвал **System Settings → Privacy & Security → Open Anyway** дарна. Камерын зөвшөөрөлд **Allow** дарна.

**Linux:** `tar -xzf UkhaalagDasgaljuulagch-*-linux-x64.tar.gz` хийгээд хавтас доторх `UkhaalagDasgaljuulagch`-ийг
ажиллуулна. OpenGL сан хэрэгтэй бол `sudo apt install libegl1 libgl1`.

**Android:** APK файлыг утсаараа татаж нээнэ. «Энэ эх сурвалжаас апп суулгахыг хориглосон» гэвэл
**Тохиргоо → Энэ эх сурвалжаас зөвшөөрөх**-ийг асаагаад **Суулгах** дарна (Play Protect анхааруулбал
**Дэлгэрэнгүй → Ямар ч байсан суулгах**). Нээгээд камерын зөвшөөрөлд **Апп ашиглах үед** дарна. Интернэт
шаардахгүй. Нээгдэхгүй бол Play Store-оос «Android System WebView»-ээ шинэчилнэ.
[Дэлгэрэнгүй](https://github.com/enkhbatbyambatsogt81-arch/Kayl/blob/main/body_tracking_app/android/README.md)

**iPhone:** Safari-аар <https://enkhbatbyambatsogt81-arch.github.io/Kayl/> нээгээд доод талын **Хуваалцах** (□↑) → **Нүүр дэлгэцэнд нэмэх** (Add to Home Screen)
дарна. Нүүр дэлгэц дээр гарсан дүрсээр нь нээж, камерын зөвшөөрөлд **Зөвшөөрөх** (Allow) дарна. Анх нээхэд ~38 МБ
татагдана, дараа нь интернэтгүй ажиллана.

Апп тоон гарын үсэггүй тул систем анх нээхэд нэг удаа анхааруулга өгдөг. Компьютерын файл бүр задалсны дараа
ойролцоогоор 450–500 МБ эзэлнэ. Юу шинэ болсныг [CHANGELOG](https://github.com/enkhbatbyambatsogt81-arch/Kayl/blob/main/body_tracking_app/CHANGELOG.md)-оос харна уу.
