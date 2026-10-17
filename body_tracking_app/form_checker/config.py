"""Бүх босго утга (threshold) нэг дор.

Утгуудыг өөрчилж аппын "хатуу/зөөлөн" байдлыг тохируулж болно.
Өнцгүүд градусаар.
"""

from dataclasses import dataclass


@dataclass
class CommonConfig:
    # Landmark-ийн visibility үүнээс бага бол "харагдахгүй байна" гэж үзнэ.
    min_visibility: float = 0.5
    # Өнцгийг тэгшитгэх EMA коэффициент (0..1). Их байх тусам хурдан, бага байх тусам жигд.
    smoothing_alpha: float = 0.5
    # Медиан шүүлтүүрийн цонх (кадр). Нэг кадрын гэнэтийн алдааг арилгана.
    median_window: int = 5
    # Өнцгийн шүүлтүүр: "one_euro" (2.0, хурдаас хамаарах 1€ шүүлтүүр) эсвэл "ema" (1.x хувилбар).
    # 1€: удаан хөдөлгөөнд min_cutoff (Гц) -> чичиргээ бага; хурдан үед cutoff = min_cutoff + beta·|°/с|.
    # Утгыг tools/evaluate_filters.py, evaluate_logic.py-аар 25 хослол туршиж сонгосон: beta их байвал
    # хоцрогдол багасах ч их шуугиантай үед шуугиан "нэвтэрч" давталт илүү тоолдог.
    filter_kind: str = "one_euro"
    one_euro_min_cutoff: float = 0.5
    one_euro_beta: float = 0.02
    one_euro_d_cutoff: float = 1.0
    # Хэлбэрийн алдааг давталтад бүртгэхийн өмнө дараалан хэдэн кадр харагдах ёстой вэ.
    issue_min_frames: int = 3
    # Мөр хоорондын өргөн / их биеийн урт харьцаа үүнээс их бол "урдаас" харж байна гэж үзнэ.
    front_view_ratio: float = 0.45
    # Давталтын үр дүнгийн мессежийг дэлгэцэнд хэдэн секунд харуулах вэ.
    result_message_seconds: float = 2.0
    # Биеийг энэ хугацаанаас удаан алдвал эхэлсэн давталтыг цуцална.
    lost_reset_seconds: float = 1.0
    # Үүнээс богино хугацаагаар хүн алдагдвал (нэг хоёр кадр) өмнөх дүнг үргэлжлүүлэн харуулна.
    glitch_seconds: float = 0.3
    # "Байрлалд ороогүй" нөхцөл дараалан хэдэн кадр үргэлжилбэл тоолуурыг зогсоох вэ.
    gate_min_frames: int = 8


@dataclass
class SquatConfig:
    # Өвдөгний өнцөг (хонго-өвдөг-шагай).
    top_angle: float = 160.0        # үүнээс их = бүрэн босоо
    start_angle: float = 150.0      # үүнээс бага болмогц давталт эхэлнэ
    depth_angle: float = 100.0      # үүнээс бага = хангалттай гүн суусан
    attempt_angle: float = 140.0    # үүнээс бага болоод буцвал "гүехэн" давталт гэж тооцно
    # Урдаас харахад бага зэргийн нугалалт зурган дээр бараг мэдэгдэхгүй тул (шуугиантай)
    # дээд/эхлэх босгыг зөөлрүүлнэ. Гүний босго (depth_angle) хэвээр.
    front_top_angle: float = 150.0
    front_start_angle: float = 138.0
    front_attempt_angle: float = 130.0
    # Их бие (мөр-хонго) босоо тэнхлэгээс хэдэн градусаас их хазайвал алдаа.
    max_torso_lean: float = 50.0
    # Урдаас харахад өвдөгний зай / шагайн зай үүнээс бага бол өвдөг дотогш орсон.
    min_knee_ankle_ratio: float = 0.80
    # Өсгий өргөгдсөн эсэх: өсгий дээшилсэн зай / шилбэний урт.
    max_heel_lift_ratio: float = 0.12
    # Хурдан буцаж эргэх үеийн "бүрэн босоогүй" дүрэм: доод цэгээс хэдэн градус өндийгөөд
    # дахин хэдэн градус буувал шинэ давталт гэж үзэх вэ.
    rebound_rise: float = 30.0
    rebound_drop: float = 15.0
    # Хэмнэл: давталт (доош + дээш) үүнээс богино хугацаанд хийгдвэл "хэт хурдан" гэж сануулна.
    # Хугацааг эхлэх босгоос (start_angle) дээд босго (top_angle) хүртэл хэмжинэ, тиймээс жинхэнэ
    # хөдөлгөөний ~70% орчим: 2 секундын давталт ≈ 1.4 с гэж хэмжигдэнэ.
    min_rep_seconds: float = 1.0
    # Хөлийн байрлал (урдаас): хөлийн хурууны зай / мөрний өргөн. NgoQuocBao1010/Exercise-Correction
    # (MIT) төслийн [1.2, 2.8] мужаас авав. Тэр утгыг "strict" түвшинд яг хэрэглэнэ; "normal" түвшинд
    # доод хязгаарыг 0.9 болгож зөөлрүүлсэн (хонгоны өргөнөөр зогсохыг алдаа гэж үзэхгүйн тулд).
    min_stance_ratio: float = 0.9
    max_stance_ratio: float = 2.8


@dataclass
class PushupConfig:
    # Тохойн өнцөг (мөр-тохой-бугуй).
    top_angle: float = 155.0
    start_angle: float = 145.0
    depth_angle: float = 90.0
    attempt_angle: float = 130.0
    # Бие шулуун байх: мөр-хонго-шагайн өнцөг үүнээс их байх ёстой.
    min_body_line: float = 160.0
    # Суниалтын байрлал: мөр-шагайн шугам хэвтээ тэнхлэгээс хэдэн градусаас бага хазайх ёстой.
    max_body_tilt: float = 40.0
    rebound_rise: float = 30.0
    rebound_drop: float = 15.0
    min_rep_seconds: float = 0.8


@dataclass
class WorkoutConfig:
    # Нэг сетэд хийх давталтын тоо. 0 = чөлөөт горим (зорилго, сет, амралтгүй).
    target_reps: int = 10
    sets: int = 3
    rest_seconds: float = 60.0
    # Эхлэх байрлалдаа хэдэн секунд тогтвортой байвал тоолол (3-2-1) эхлэх вэ.
    ready_seconds: float = 1.0
    countdown_seconds: float = 3.0
    # Тоолол явж байхад хүн энэ хугацаанаас удаан алдагдвал эхлэх шат руу буцна.
    lost_seconds: float = 0.7
    # Эхлэхийн өмнө бие кадрын хамгийн багадаа хэдэн хувийг эзлэх ёстой вэ (хэт хол байвал ойртуулна).
    min_body_size: float = 0.30
    # Идэвхгүй байдал (2.0, LearnOpenCV AI Fitness Trainer-ийн INACTIVE_THRESH = 15 с санаагаар):
    # сетийн дунд хүн away_seconds-ээс удаан алга болбол сетийг түр зогсоож эхлэх шат руу буцаана;
    # харагдаж байгаа ч idle_seconds хөдөлгөөнгүй байвал "амарч байна уу?" гэж сануулна.
    away_seconds: float = 5.0
    idle_seconds: float = 15.0


# Шалгуурын түвшин. Санааг LearnOpenCV-ийн "AI Fitness Trainer" (beginner / pro горимууд)-аас авсан:
# https://learnopencv.com/ai-fitness-trainer-using-mediapipe/ - тэнд pro горимд гүний босго 70°->80°,
# шилбэний хазайлт 45°->30° болж чангардаг. Манай өнцгүүд өөр (үений дотоод өнцөг) тул утгуудыг
# өөрсдийн синтетик туршилтаар тохируулав. "normal" = 1.x хувилбарын утгууд.
LEVELS = ("easy", "normal", "strict")
LEVEL_OVERRIDES = {
    "squat": {
        "easy":   dict(depth_angle=110.0, max_torso_lean=55.0, min_knee_ankle_ratio=0.75,
                       max_heel_lift_ratio=0.15, min_rep_seconds=0.7, min_stance_ratio=0.75),
        "normal": {},
        "strict": dict(depth_angle=90.0, max_torso_lean=45.0, min_knee_ankle_ratio=0.85,
                       max_heel_lift_ratio=0.09, min_rep_seconds=1.2, min_stance_ratio=1.2),
    },
    "pushup": {
        "easy":   dict(depth_angle=100.0, min_body_line=155.0, min_rep_seconds=0.5),
        "normal": {},
        "strict": dict(depth_angle=80.0, min_body_line=165.0, min_rep_seconds=1.0),
    },
}


def exercise_config(name, level="normal"):
    from dataclasses import replace
    base = SquatConfig() if name == "squat" else PushupConfig()
    return replace(base, **LEVEL_OVERRIDES[name].get(level, {}))
