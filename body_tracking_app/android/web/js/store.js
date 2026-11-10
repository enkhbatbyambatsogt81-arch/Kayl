// Тохиргоо ба дасгалын түүх: утсан дээр localStorage-д хадгална.

const SETTINGS_KEY = "ud.settings.v1";
const HISTORY_KEY = "ud.history.v1";

export const DEFAULTS = {
  level: "normal", exercise: "squat", reps: 10, sets: 3, rest: 60, free_mode: false, auto_detect: false,
  sound: true, source: "camera", camera: "user", mirror: true, theme: "light", compute: "auto",
};

// Бэлтгэлийн түвшин: нэр, хэнд, (давталт, сет, амралт), техникийн шалгуур. Компьютерын хувилбарын start.py-тай ижил.
export const LEVELS = {
  easy: { name: "Анхан шат", who: "Дасгалаа дөнгөж эхэлж буй эсвэл бэртлээс сэргэж буй үед.", goal: [8, 2, 60],
          rule: "Уян", angles: "Өвдөг 110°, тохой 100° хүртэл нугарахад тооцогдоно" },
  normal: { name: "Дунд шат", who: "Тогтмол дасгал хийдэг хүмүүст.", goal: [10, 3, 60],
            rule: "Стандарт", angles: "Өвдөг 100°, тохой 90° хүртэл нугарна" },
  strict: { name: "Ахисан шат", who: "Техникээ төгөлдөржүүлэхийг зорьж буй тамирчдад.", goal: [15, 4, 90],
            rule: "Нарийн", angles: "Өвдөг 90°, тохой 80°, нуруу босоо, тайван хэмнэл" },
};

export const EXERCISES = {
  squat: { name: "Суулт", short: "Суулт", sub: "Squat · гүн, нурууны байрлал, өвдөг", joint: "өвдөг" },
  pushup: { name: "Гар дээр суниалт", short: "Суниалт", sub: "Push-up · тохойн өнцөг, биеийн шулуун байдал",
            joint: "тохой" },
};

function read(key, fallback) {
  try {
    const raw = localStorage.getItem(key);
    return raw ? JSON.parse(raw) : fallback;
  } catch {
    return fallback;
  }
}

function write(key, value) {
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch { /* хадгалах зай байхгүй эсвэл хориотой: апп ажилласаар байна */ }
}

function clean(raw) {
  const s = { ...DEFAULTS, ...(raw && typeof raw === "object" ? raw : {}) };
  const num = (v, lo, hi, d) => (Number.isFinite(+v) ? Math.min(hi, Math.max(lo, Math.round(+v))) : d);
  s.level = s.level in LEVELS ? s.level : DEFAULTS.level;
  s.exercise = s.exercise in EXERCISES ? s.exercise : DEFAULTS.exercise;
  s.reps = num(s.reps, 1, 50, DEFAULTS.reps);
  s.sets = num(s.sets, 1, 10, DEFAULTS.sets);
  s.rest = num(s.rest, 10, 300, DEFAULTS.rest);
  s.source = s.source === "demo" ? "demo" : "camera";
  s.camera = s.camera === "environment" ? "environment" : "user";
  s.theme = s.theme === "dark" ? "dark" : "light";
  s.compute = s.compute === "cpu" ? "cpu" : "auto";
  for (const k of ["free_mode", "auto_detect", "sound", "mirror"]) s[k] = !!s[k];
  return s;
}

export const settings = clean(read(SETTINGS_KEY, null));
// Туршилтад (android/ci_emulator_test.sh): ?demo=1 бол камергүй демо горимоор, ?demo=0 бол камераар эхэлнэ
export const QUERY = new URLSearchParams(location.search);
if (QUERY.has("demo")) settings.source = QUERY.get("demo") === "1" ? "demo" : "camera";

export function saveSettings() {
  write(SETTINGS_KEY, settings);
}

/** Түвшин сонгоход шалгуур + давталт, сет, амралт нэг дор тохирно. */
export function applyLevel(level) {
  const [reps, sets, rest] = LEVELS[level].goal;
  Object.assign(settings, { level, reps, sets, rest, free_mode: false });
  saveSettings();
}

export function loadHistory() {
  const list = read(HISTORY_KEY, []);
  return Array.isArray(list) ? list : [];
}

/** items: mobile.summary()-ийн жагсаалт (дасгал бүрээр). Шинэ нь эхэндээ, хамгийн ихдээ 200 бичлэг. */
export function addHistory(items, seconds) {
  if (!items.length) return null;
  const record = { when: new Date().toISOString(), seconds: Math.round(seconds), items };
  write(HISTORY_KEY, [record, ...loadHistory()].slice(0, 200));
  return record;
}

export function clearHistory() {
  write(HISTORY_KEY, []);
}
