"""Дэлгэцэнд гарах зөвлөмжийн текстүүд (монгол / англи)."""

MESSAGES = {
    # Ерөнхий
    "no_person":      ("Хүн харагдахгүй байна", "No person detected"),
    "not_visible":    ("Биеэ бүтэн харагдуул (толгойноос хөл хүртэл)", "Show your whole body"),
    "turn_side":      ("Камер руу хажуугаараа эргэж зогс", "Turn sideways to the camera"),
    "get_in_plank":   ("Суниалтын байрлалд ор", "Get into push-up position"),
    "ready":          ("Бэлэн. Эхэл!", "Ready. Start!"),
    "good_rep":       ("Зөв! Сайн байна", "Good rep!"),
    "keep_going":     ("Үргэлжлүүл", "Keep going"),
    "go_down":        ("Доошоо", "Go down"),
    "go_up":          ("Дээшээ", "Go up"),
    "depth_ok":       ("Гүн хангалттай, одоо өндий", "Depth reached, now come up"),
    "squat_stand":    ("Шулуун зогсоод эхэл", "Stand up straight to start"),
    "pushup_arms":    ("Гараа тэнийлгэсэн байрлалаас эхэл", "Start with arms extended"),

    # Камерын өмнө байрлах заавар (биеийн аль хэсэг харагдахгүй байгааг хэлнэ)
    "frame_feet":     ("Хөл харагдахгүй байна. Камераас холдож зогс", "Feet not visible. Step back"),
    "frame_head":     ("Толгой харагдахгүй байна. Камераас холд", "Head not visible. Step back"),
    "frame_side":     ("Дэлгэцийн голд шилж", "Move to the center of the screen"),
    "frame_closer":   ("Хэт хол байна. Камер руу ойрт", "Too far away. Come closer"),
    "hold_position":  ("Сайн байна. Ийм байрлалаа барь...", "Good. Hold this position..."),
    "get_ready":      ("Бэлдээрэй...", "Get ready..."),

    # Сет, амралт
    "set_done":       ("Сет дууслаа! Амар", "Set complete! Rest"),
    "rest":           ("Амралт. Space: алгасах", "Rest. Space: skip"),
    "workout_done":   ("Дасгал дууслаа! Сайн байна", "Workout complete! Well done"),

    # Squat алдаа
    "squat_shallow":    ("Илүү гүн суу (гуя газартай параллель)", "Squat deeper (thighs parallel)"),
    "squat_lean":       ("Цээжээ өргө, их биеэ хэт урагш бүү хазайлга", "Chest up, don't lean forward"),
    "squat_knees_in":   ("Өвдгөө дотогш бүү оруул, гадагш нь түлх", "Push your knees out"),
    "squat_heels":      ("Өсгийгөө газраас бүү салга", "Keep your heels down"),
    "squat_not_up":     ("Бүрэн босоод дараагийнхаа давталтыг хий", "Stand up fully between reps"),
    # Squat сануулга (2.0): давталтыг буруу болгохгүй
    "squat_fast":       ("Зөв! Гэхдээ арай удаан, хяналттай хий", "Good! Now slow down a little"),
    "squat_stance_narrow": ("Хөлөө арай өргөн, мөрний өргөнөөр тавь", "Place your feet shoulder-width apart"),
    "squat_stance_wide":   ("Хөлөө хэт өргөн тавьжээ, арай ойртуул", "Feet too wide, bring them closer"),

    # Push-up алдаа
    "pushup_shallow":   ("Илүү доошоо бууж, тохойгоо 90° хүртэл нугал", "Go lower (elbows to 90°)"),
    "pushup_sag":       ("Бэлхүүсээ бүү унжуул, гэдсээ чангал", "Don't let your hips sag"),
    "pushup_pike":      ("Бөгсөө бүү өргө, биеэ шулуун байлга", "Don't pike your hips up"),
    "pushup_not_up":    ("Гараа бүрэн тэнийлгэ", "Fully extend your arms"),
    "pushup_fast":      ("Зөв! Гэхдээ арай удаан, хяналттай хий", "Good! Now slow down a little"),

    # 2.0: идэвхгүй байдал, дасгал таних
    "paused_away":      ("Түр зогсоолоо. Буцаж ирээд эхлэх байрлалдаа зогсоорой", "Paused. Come back to continue"),
    "idle_hint":        ("Амарч байна уу? Бэлэн болмогц үргэлжлүүлээрэй", "Resting? Continue when ready"),
    "switched_squat":   ("Суулт гэж танилаа", "Detected: squat"),
    "switched_pushup":  ("Суниалт гэж танилаа", "Detected: push-up"),
}

# Дасгалын дүнгийн дэлгэцэд гарах дэлгэрэнгүй зөвлөмж (алдааг хэрхэн засах вэ)
TIPS = {
    "squat_shallow":  "Гуяа газартай параллель болтол суу. Хөлөө мөрнөөс арай өргөн тавьж, хөлийн хурууг бага зэрэг "
                      "гадагш эргүүлбэл гүн суухад хялбар болно.",
    "squat_lean":     "Цээжээ дээш, харцаа урагш чиглүүл. Сандал дээр суух гэж байгаа мэт бөгсөө хойш түлхэж, "
                      "их биеэ аль болох босоо барь.",
    "squat_knees_in": "Өвдгөө хөлийн хурууны чиглэлд гадагш түлх. Хэцүү бол илүү удаан, бага гүнтэй хийж эхэл.",
    "squat_heels":    "Жингээ өсгий болон бүтэн улан дээрээ хуваарил. Шагай хөшүүн бол хөлөө арай өргөн тавь.",
    "squat_not_up":   "Давталт бүрийн дараа өвдөг, хонгоо бүрэн тэнийлгэж шулуун зогсоод дараагийнхаа давталтыг эхэл.",
    "pushup_shallow": "Цээжээ шал руу ойртуулж, тохойгоо 90° хүртэл нугал. Хэцүү бол өвдөг дээрээ тулж хийж болно.",
    "pushup_sag":     "Гэдэс, бөгсөө чангалж, толгойноос өсгий хүртэл биеэ нэг шулуун шугам болго.",
    "pushup_pike":    "Бөгсөө доошлуулж, мөр, хонго, өсгий нэг шугамд байхаар бай.",
    "pushup_not_up":  "Давталт бүрийн дээд цэгт гараа бүрэн тэнийлгэ.",
    "squat_fast":     "Доошоо 2 орчим секунд, дээшээ 1 секунд гэсэн хэмнэлээр хий. Удаан, хяналттай хөдөлгөөн "
                      "булчинг илүү ажиллуулж, гэмтлээс сэргийлнэ.",
    "squat_stance_narrow": "Хөлөө мөрний өргөнөөр (эсвэл арай өргөн) тавьж, хурууг бага зэрэг гадагш эргүүл.",
    "squat_stance_wide":   "Хэт өргөн зогсвол өвдөг, хонгонд ачаалал ихэснэ. Мөрнөөс арай өргөн байхад хангалттай.",
    "pushup_fast":    "Доошоо 2 орчим секунд, дээшээ 1 секунд гэсэн хэмнэлээр хий.",
}

# Сануулгын товч гарчиг (дүн, түүхийн хуудсанд). Дэлгэцийн мессеж нь "Зөв! Гэхдээ ..." хэлбэртэй тул
# жагсаалтад гарчиг болгоход тохиромжгүй.
WARNING_TITLES = {
    "squat_fast": "Хэт хурдан давталт",
    "pushup_fast": "Хэт хурдан давталт",
    "squat_stance_narrow": "Хөлийн байрлал хэт нарийн",
    "squat_stance_wide": "Хөлийн байрлал хэт өргөн",
}

EXERCISE_NAMES = {
    "squat": ("Суулт (Squat)", "Squat"),
    "pushup": ("Гар дээр суниалт (Push-up)", "Push-up"),
}

STATE_NAMES = {
    "top":    ("Дээд байрлал", "Top"),
    "down":   ("Бууж байна", "Going down"),
    "bottom": ("Доод цэг", "Bottom"),
    "up":     ("Өндийж байна", "Going up"),
    "idle":   ("Хүлээж байна", "Waiting"),
}


def t(key, lang="mn", table=MESSAGES):
    mn, en = table.get(key, (key, key))
    return mn if lang == "mn" else en
