# Ашигласан нээлттэй эх, санаа (2.0 хувилбар)

2.0 хувилбарыг хийхдээ ижил төстэй нээлттэй эхийн төслүүдийг судалж, манайхаас илүү шийдсэн
хэсгүүдийг нь өөрийн кодонд оруулсан. **Бусдын кодыг шууд хуулаагүй**: санаа, алгоритм, босго утгыг
авч, өөрийн бүтэцд тааруулан дахин бичсэн. Тиймээс эдгээр лицензийн "кодыг хамт түгээх" нөхцөл
манай кодонд хамаарахгүй ч эх сурвалжийг доор бүрэн дурдав.

| Төсөл | Лиценз | Бид юу авсан | Манай код |
|---|---|---|---|
| **1€ filter** — G. Casiez, N. Roussel, D. Vogel, *"1 € Filter: A Simple Speed-Based Low-Pass Filter for Noisy Input in Interactive Systems"*, CHI 2012, [doi:10.1145/2207676.2208639](https://doi.org/10.1145/2207676.2208639). Лавлах код: [github.com/casiez/OneEuroFilter](https://github.com/casiez/OneEuroFilter) | BSD-3-Clause (Inria) | Хурдаас хамаарч тасалгааны давтамжаа өөрчилдөг шүүлтүүрийн алгоритм | `form_checker/geometry.py` → `OneEuroFilter` (өгүүллийн томьёогоор бичсэн) |
| **AI Fitness Trainer: Squats Analysis** — LearnOpenCV (BigVision LLC), [learnopencv.com/ai-fitness-trainer-using-mediapipe](https://learnopencv.com/ai-fitness-trainer-using-mediapipe/), код: [spmallick/learnopencv/AI-Fitness-Trainer-Using-MediaPipe-Analyzing-Squats](https://github.com/spmallick/learnopencv/tree/master/AI-Fitness-Trainer-Using-MediaPipe-Analyzing-Squats) | Лиценз заагаагүй | 1) **Beginner / Pro** гэх хоёр түвшний босго → манай *Зөөлөн / Энгийн / Хатуу* шалгуур; 2) **идэвхгүй байдлын таймер** (15 с); 3) алдааг **ноцтой / зөөлөн** гэж ангилах санаа; 4) үений өнцгийг **нумаар** харуулах | `config.py` → `LEVEL_OVERRIDES`, `workout.py` → түр зогсолт ба сануулга, `exercises/base.py` → оноо, `ui.py` → `draw_angle_arc`. Лиценз заагаагүй тул кодоос нь нэг ч мөр аваагүй |
| **Pose classification** — Google ML Kit / MediaPipe, [developers.google.com/ml-kit/vision/pose-detection/classifying-poses](https://developers.google.com/ml-kit/vision/pose-detection/classifying-poses), [googlesamples/mlkit](https://github.com/googlesamples/mlkit) (`EMASmoothing.java`, `RepetitionCounter.java`) | Apache-2.0 | Ангиллын итгэлийг **10 кадрын цонхон дээр EMA (alpha 0.2)**-аар тэгшитгэх, **орох / гарах хоёр босго** (6/10 ба 4/10) | `form_checker/recognition.py` → `WindowEMA`, `ExerciseRecognizer` (k-NN-ийн оронд энгийн геометр дүрэм) |
| **Exercise-Correction** — Ngô Hồng Quốc Bảo, [github.com/NgoQuocBao1010/Exercise-Correction](https://github.com/NgoQuocBao1010/Exercise-Correction) | MIT | Squat-ын **хөлийн байрлал**: хөлийн хурууны зай / мөрний өргөн ∈ [1.2, 2.8] | `exercises/squat.py` → `squat_stance_narrow/wide`, `config.py` → `min/max_stance_ratio` |
| **Pose Trainer** — Steven Chen, Richard Yang, [github.com/stevenzchen/pose-trainer](https://github.com/stevenzchen/pose-trainer) | GPL-3.0 | Зөвхөн судалсан (мэргэжлийн хүний бичлэгтэй DTW-ээр харьцуулах арга). GPL тул ямар ч код аваагүй; мэргэжлийн бичлэг шаарддаг тул одоогоор хэрэгжүүлээгүй | — |

Бусад:
- **MediaPipe Pose Landmarker** (Google, Apache-2.0) — биеийн 33 цэг илрүүлэх загвар (1.0 хувилбараас).
- **CustomTkinter** (Tom Schimansky, MIT) — цонхтой интерфейс (1.2 хувилбараас).
