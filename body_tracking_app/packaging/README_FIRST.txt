Ухаалаг дасгалжуулагч: эхлүүлэх заавар
=====================================

Python суулгах шаардлагагүй. Вэбкамер байхгүй бол аппын «Тохиргоо» хуудасны «Демо (камергүй)» горимоор туршина.

WINDOWS 10 / 11
  1. ZIP файлаа баруун товшоод «Extract All...» (Бүгдийг задлах) дарна.
  2. Задарсан хавтас доторх UkhaalagDasgaljuulagch.exe-г давхар товшино.
  3. «Windows protected your PC» гарвал «More info» -> «Run anyway» дарна.
     (Апп тоон гарын үсэггүй тул Windows ингэж асуудаг. Нэг л удаа асууна.)
  4. Камер нээгдэхгүй бол: Settings -> Privacy & security -> Camera хэсэгт
     «Camera access» ба «Let desktop apps access your camera»-г асаана.

macOS (11 ба түүнээс шинэ)
  1. ZIP файлаа давхар товшиж задлаад UkhaalagDasgaljuulagch.app-ийг Applications хавтас руу чирнэ.
  2. Аппыг давхар товшино. «Apple could not verify...» гэж гарвал «Done» дарна.
  3. System Settings -> Privacy & Security хэсгийн доод талд «Open Anyway» дараад дахин нээнэ.
     (macOS 14 ба өмнөх хувилбарт: аппыг баруун товшоод «Open» -> «Open».)
  4. Камер ашиглах зөвшөөрөл асуухад «Allow» дарна.
  Terminal-аар нэг дор: xattr -dr com.apple.quarantine /Applications/UkhaalagDasgaljuulagch.app

LINUX (x86_64, Ubuntu 22.04+, Debian 12+, Fedora 38+)
  1. tar -xzf UkhaalagDasgaljuulagch-*-linux-x64.tar.gz
  2. ./UkhaalagDasgaljuulagch-*-linux-x64/UkhaalagDasgaljuulagch
  OpenGL сан алга гэж гарвал: sudo apt install libegl1 libgl1 (Fedora: sudo dnf install mesa-libEGL mesa-libGL)

Тохиргоо ба дасгалын түүх хадгалагдах газар:
  Windows: %APPDATA%\UkhaalagDasgaljuulagch
  macOS:   ~/Library/Application Support/UkhaalagDasgaljuulagch
  Linux:   ~/.local/share/UkhaalagDasgaljuulagch

Дэлгэрэнгүй: https://github.com/enkhbatbyambatsogt81-arch/Kayl
