// Ухаалаг дасгалжуулагч — утасны хувилбарын үндсэн хэсэг: хуудсууд ба тэдгээрийн хооронд шилжих.
// Хуудас бүр хаягийн # хэсгээр ялгагдана, тиймээс Android-ын «Буцах» товч өмнөх хуудас руу аваачна.

import * as audio from "./audio.js";
import * as engine from "./engine.js";
import { FIGURES, ICONS } from "./figures.js";
import { EXERCISES, LEVELS, QUERY, applyLevel, clearHistory, loadHistory, saveSettings, settings } from "./store.js";
import { mountWorkout } from "./workout.js";

const screen = document.getElementById("screen");
const tabs = document.getElementById("tabs");
const TABS = [["start", "Эхлэх", ICONS.start], ["settings", "Тохиргоо", ICONS.settings],
              ["history", "Түүх", ICONS.history], ["help", "Заавар", ICONS.help]];
const STEPS = ["welcome", "level", "exercise"];

let workout = null;       // идэвхтэй дасгалын дэлгэц
let lastResult = null;    // {items, record}: дүнгийн хуудсанд
let lastRoute = { name: "", step: "" };
let confirmClear = false;

const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const pct = (x) => `${Math.round(x * 100)}%`;

function applyTheme() {
  document.documentElement.dataset.theme = settings.theme;
  document.querySelector('meta[name="theme-color"]').content = settings.theme === "dark" ? "#141414" : "#ffffff";
  syncBars();
}

/** Android-ын дээд / доод самбарын өнгө: дасгалын дэлгэц (хар) ба харанхуй горимд бараан. */
function syncBars() {
  try {
    window.AndroidApp?.setTheme(settings.theme === "dark" || route().name === "workout");
  } catch { /* хөтөч дээр ажиллаж байгаа үед байхгүй */ }
}

function route() {
  const [name = "start", step = ""] = location.hash.replace(/^#\/?/, "").split("/");
  const known = ["start", "workout", "summary", "settings", "history", "help"];
  return { name: known.includes(name) ? name : "start", step: STEPS.includes(step) ? step : "welcome" };
}

function go(hash, replace = false) {
  if (replace) location.replace(hash);
  else location.hash = hash;
}

const themeToggle = () => `<button class="theme-toggle" data-act="theme" aria-label="Цайвар / харанхуй горим">
  <span class="knob">${settings.theme === "dark" ? ICONS.moon : ICONS.sun}</span></button>`;

// ---- Хуудсууд -----------------------------------------------------------------------------------------------------
function startPage(step) {
  const index = STEPS.indexOf(step);
  const top = step === "welcome"
    ? `<div class="brand">Ухаалаг дасгалжуулагч</div><div class="grow"></div>`
    : `<button class="btn ghost small" data-act="back">${ICONS.back} Буцах</button>
       <div class="grow"><div class="steps"><div class="bars">${[0, 1, 2].map((i) =>
         `<i class="${i < index ? "on" : ""}"></i>`).join("")}</div><span>Алхам ${index} / 3</span></div></div>`;
  let body = "", note = "", button = `Үргэлжлүүлэх ${ICONS.next}`;
  if (step === "welcome") {
    button = `Эхлэх ${ICONS.next}`;
    body = `<div class="welcome">
      <div><div class="label">Тавтай морилно уу</div>
        <h1>Дасгал бүрээ<br>зөв техникээр</h1>
        <p class="sub">Камер таны хөдөлгөөнийг бодит хугацаанд шинжилж, давталтыг тоолж, техникийн алдааг тэр даруй
        сануулна.</p></div>
      <div class="pic inset">${FIGURES.squat}</div></div>`;
  } else if (step === "level") {
    note = "Түвшнээ «Тохиргоо»-ноос хүссэн үедээ өөрчилж болно.";
    body = `<h2 class="title">Бэлтгэлийн түвшингээ сонгоно уу</h2>
      <p class="sub">Түвшин нь давталт, сетийн тоо болон техникийн шалгуурын нарийвчлалыг тодорхойлно.</p>
      <div class="choices">${Object.entries(LEVELS).map(([key, lv]) => `
        <button class="choice ${settings.level === key ? "on" : ""}" data-act="level" data-key="${key}">
          <span class="mark">✓</span>
          <h3>${lv.name}${key === "normal" ? '<span class="pill">Зөвлөмж</span>' : ""}</h3>
          <p class="who">${lv.who}</p>
          <div class="facts"><span>Сет × давталт <b>${lv.goal[1]} × ${lv.goal[0]}</b></span>
            <span>Амралт <b>${lv.goal[2]} сек</b></span><span>Шалгуур <b>${lv.rule}</b></span></div>
          <p class="angles">${lv.angles}</p>
        </button>`).join("")}</div>`;
  } else {
    note = settings.source === "demo" ? "Демо горим: камергүйгээр зохиомол хүн дасгал хийнэ."
                                      : "Утсаа тогтвортой тавиад, бүтэн биеэ харагдахаар зогсоорой.";
    body = `<h2 class="title">Дасгалаа сонгоно уу</h2>
      <p class="sub">Дасгалын явцад ч өөрчлөх боломжтой.</p>
      <div class="choices">${Object.entries(EXERCISES).map(([key, ex]) => `
        <button class="choice exercise ${settings.exercise === key ? "on" : ""}" data-act="exercise" data-key="${key}">
          <span class="mark">✓</span>
          <span class="pic inset">${FIGURES[key]}</span>
          <span><h3>${ex.name}</h3><p class="desc">${ex.sub}</p></span>
        </button>`).join("")}</div>`;
  }
  return `<div class="topbar">${top}${themeToggle()}</div>${body}
    <div class="footer">${note ? `<p class="note">${note}</p>` : ""}
      <button class="btn primary big" data-act="next">${button}</button></div>`;
}

const seg = (name, value, options) => `<div class="seg">${options.map(([key, label]) =>
  `<button class="${String(value) === String(key) ? "on" : ""}" data-act="set" data-name="${name}" data-value="${key}">
     ${label}</button>`).join("")}</div>`;
const toggle = (name, on) => `<button class="switch ${on ? "on" : ""}" data-act="toggle" data-name="${name}"
  role="switch" aria-checked="${on}"></button>`;
const stepper = (name, value, unit = "") => `<div class="stepper">
  <button data-act="step" data-name="${name}" data-dir="-1" aria-label="Хасах">−</button>
  <output>${value}${unit}</output>
  <button data-act="step" data-name="${name}" data-dir="1" aria-label="Нэмэх">+</button></div>`;

function settingsPage() {
  const s = settings;
  const goalOff = s.free_mode ? "off" : "";
  const camOff = s.source === "demo" ? "off" : "";
  return `<div class="topbar"><div><h2 class="title">Тохиргоо</h2></div><div class="grow"></div>${themeToggle()}</div>
    <div class="group"><span class="label">ДАСГАЛ</span><div class="rows">
      <div class="row col"><div class="name">Дасгал</div>
        ${seg("exercise", s.exercise, Object.entries(EXERCISES).map(([k, e]) => [k, e.name]))}</div>
      <div class="row col"><div class="name">Түвшин<small>${LEVELS[s.level].angles}</small></div>
        ${seg("level", s.level, Object.entries(LEVELS).map(([k, l]) => [k, l.name]))}</div>
      <div class="row"><div class="name">Дасгалыг автоматаар таних<small>Зогсож байвал суулт, планк байрлалд
        орвол суниалт гэж өөрөө солино</small></div>${toggle("auto_detect", s.auto_detect)}</div>
    </div></div>
    <div class="group"><span class="label">ЗОРИЛГО</span><div class="rows">
      <div class="row"><div class="name">Чөлөөт горим<small>Зорилго, сет, амралтгүй: зөвхөн тоолж шалгана</small></div>
        ${toggle("free_mode", s.free_mode)}</div>
      <div class="row ${goalOff}"><div class="name">Нэг сетэд</div>${stepper("reps", s.reps, " давталт")}</div>
      <div class="row ${goalOff}"><div class="name">Сетийн тоо</div>${stepper("sets", s.sets)}</div>
      <div class="row ${goalOff}"><div class="name">Сет хоорондын амралт</div>${stepper("rest", s.rest, " сек")}</div>
    </div></div>
    <div class="group"><span class="label">КАМЕР БА ДУУ</span><div class="rows">
      <div class="row col"><div class="name">Эх үүсвэр<small>Демо: камергүйгээр зохиомол хүн зөв ба алдаатай
        давталт хийж буйг үзүүлнэ</small></div>
        ${seg("source", s.source, [["camera", "Камер"], ["demo", "Демо (камергүй)"]])}</div>
      <div class="row col ${camOff}"><div class="name">Камер</div>
        ${seg("camera", s.camera, [["user", "Урд (дэлгэц талын)"], ["environment", "Ар"]])}</div>
      <div class="row ${camOff}"><div class="name">Толин дүрс<small>Урд камерын дүрсийг толь шиг харуулна</small></div>
        ${toggle("mirror", s.mirror)}</div>
      <div class="row"><div class="name">Дуут дохио<small>Тоолол, зөв / алдаатай давталт, сет дуусах</small></div>
        ${toggle("sound", s.sound)}</div>
      <div class="row col ${camOff}"><div class="name">Тооцоолол<small>${engine.state.gpuFailed
        ? "Өмнөх удаа видео картаар ажиллаж чадаагүй тул «Процессор» руу шилжсэн."
        : "Авто: видео картаар (хурдан). Араг яс буруу зурагдах эсвэл гацах үед «Процессор»-ыг сонгоно"}</small></div>
        ${seg("compute", s.compute, [["auto", "Авто"], ["cpu", "Процессор"]])}</div>
    </div></div>
    <div class="footer"><button class="btn primary big" data-act="workout">Эхлэх ${ICONS.start}</button></div>
    <p class="version">Ухаалаг дасгалжуулагч · v${engine.state.info ? engine.state.info.version : "…"} · Android</p>`;
}

function summaryCard(s) {
  const all = s.correct === s.reps;
  const fixes = [...s.issues, ...s.warnings];
  return `<div class="section">
    <h3>${esc(s.name)} · ${LEVELS[s.level] ? LEVELS[s.level].name : ""}</h3>
    <div class="stats">
      <div class="stat inset"><b>${s.correct}/${s.reps}</b><span>зөв давталт</span></div>
      <div class="stat inset"><b>${pct(s.accuracy)}</b><span>нарийвчлал</span></div>
      <div class="stat inset"><b>${Math.round(s.avg_score)}</b><span>дундаж оноо</span></div>
    </div>
    <div class="banner ${all ? "good" : "warn"}">${all ? "Бүх давталт зөв. Сайн байна!"
      : `${s.reps - s.correct} давталтад засах зүйл байна.`}</div>
    <div class="card" style="margin-top:12px">
      <span class="label">ДАВТАЛТ БҮРИЙН ОНОО</span>
      <div class="dots">${s.rep_scores.map((score, i) =>
        `<i class="${s.rep_correct[i] ? "" : "bad"}">${score}</i>`).join("")}</div>
      <p class="sub" style="font-size:13px">${s.sets.length > 1 ? s.sets.map(([n, c], i) =>
        `Сет ${i + 1}: ${c}/${n}`).join(" · ") + " · " : ""}Дундаж ${s.avg_duration.toFixed(1)} с / давталт</p>
    </div>
    ${fixes.length ? `<div class="card" style="margin-top:12px"><span class="label">ЗАСАХ ЗҮЙЛС</span>
      <div style="margin-top:8px">${fixes.map((f) => `<div class="issue">
        <h4>${esc(f.title)}<span>${f.count} удаа</span></h4>${f.tip ? `<p>${esc(f.tip)}</p>` : ""}</div>`).join("")}
      </div></div>` : ""}
  </div>`;
}

function summaryPage() {
  return `<div class="topbar"><div><h2 class="title">Дасгалын дүн</h2></div><div class="grow"></div>${themeToggle()}</div>
    ${lastResult.items.map(summaryCard).join("")}
    <div class="footer">
      <button class="btn primary big" data-act="workout">Дахин хийх</button>
      <button class="btn big" data-act="home">Эхлэл рүү</button></div>`;
}

function historyPage() {
  const records = loadHistory();
  const week = records.filter((r) => Date.now() - new Date(r.when).getTime() < 7 * 86400e3);
  const sum = (list, key) => list.reduce((n, r) => n + r.items.reduce((m, it) => m + it[key], 0), 0);
  const reps = sum(week, "reps"), correct = sum(week, "correct");
  const date = (iso) => {
    const d = new Date(iso);
    const two = (n) => String(n).padStart(2, "0");
    return `${d.getFullYear()}.${two(d.getMonth() + 1)}.${two(d.getDate())} ${two(d.getHours())}:${two(d.getMinutes())}`;
  };
  const rows = records.flatMap((r) => r.items.map((it) => `<div class="record">
    <div class="what"><b>${esc(it.name)}</b>
      <small>${date(r.when)} · ${it.correct}/${it.reps} зөв · оноо ${Math.round(it.avg_score)}</small></div>
    <div class="acc">${pct(it.accuracy)}</div></div>`));
  return `<div class="topbar"><div><h2 class="title">Түүх</h2></div><div class="grow"></div>${themeToggle()}</div>
    <div class="stats">
      <div class="stat inset"><b>${week.length}</b><span>дасгал (7 хоног)</span></div>
      <div class="stat inset"><b>${reps}</b><span>давталт</span></div>
      <div class="stat inset"><b>${reps ? pct(correct / reps) : "–"}</b><span>нарийвчлал</span></div>
    </div>
    ${rows.length ? `<div class="section"><h3>Өмнөх дасгалууд</h3><div class="rows">${rows.join("")}</div></div>
      <div class="footer"><button class="btn" data-act="clear">${confirmClear ? "Дахин дарж баталгаажуулна уу"
        : "Түүхийг арилгах"}</button></div>`
      : '<p class="empty">Одоогоор дасгал алга.<br>Эхний дасгалаа хийгээд энд дүнгээ хараарай.</p>'}`;
}

const HELP = [
  ["Утсаа хэрхэн байрлуулах вэ", [
    "Утсаа ширээ, тавиур эсвэл хананд налуулж тогтвортой тавина. Гартаа барьж болохгүй.",
    "Утаснаас 2–3 метр зайд зогсож, толгойноос хөл хүртэл бүтэн харагдана.",
    "Суулт: хажуугаараа зогсвол хамгийн нарийн (гүн, их бие, өсгий). Урдаасаа зогсвол өвдөг дотогш орохыг шалгана.",
    "Гар дээр суниалт: заавал хажуугаараа. Утсаа шалнаас 30–60 см өндөрт, хэвтээ байрлалаар тавибал биеэ бүтэн багтаахад амар.",
    "Гэрэлтэй, ар тал энгийн байвал илүү тогтвортой ажиллана.",
  ]],
  ["Дасгал хэрхэн явагддаг вэ", [
    "Бэлтгэл: дэлгэцийн голд шалгах жагсаалт гарна. Бүгд ✓ болоод 1 секунд хөдөлгөөнгүй байхад 3-2-1 тоолол эхэлнэ.",
    "Дасгал: давталт бүрийн дараа дуу гарна (өсөх ая = зөв, буух ая = алдаатай). Зорилтот гүнд хүрэхэд богино «бип» гарна.",
    "Сет дуусахад амралтын цаг явна. «Алгасах» дарж дараагийн сетээ шууд эхлүүлж болно.",
    "Давталт бүр 0–100 оноо авна: алдаа бүр −20, бүрэн босоогүй −15, гүехэн −15…−45, сануулга (хэт хурдан, хөлийн байрлал) −10.",
    "Сетийн дундуур кадраас 5 секундээс удаан гарвал дасгал түр зогсоно; буцаж ирээд эхлэх байрлалдаа зогсоход үргэлжилнэ.",
  ]],
  ["Товчлуурууд", [
    "✕ : дасгалаас гарах (давталт хийсэн бол дүнгээ харах эсэхийг асууна).",
    "Суулт / Суниалт : дасгалаа солих. ⟳ : урд / ар камер солих. Чанга яригч : дуу асаах / унтраах.",
    "Түр зогсоох, Алгасах (тоолол эсвэл амралтыг), Дуусгах (дүнгээ харах).",
  ]],
  ["Асуудал гарвал", [
    "Камер нээгдэхгүй бол: утасны Тохиргоо → Апп → Ухаалаг дасгалжуулагч → Зөвшөөрөл → Камер-ыг зөвшөөрнө.",
    "Тоолол эхлэхгүй бол шалгах жагсаалтын шар «›» мөрийг харна (жишээ нь «Бүтэн бие кадрт багтсан» бол холдоно).",
    "Удаан ажиллаж байвал бусад аппыг хааж, утсаа цэнэглэгчээс салгалгүй ашиглана. Дэлгэцийн баруун дээд буланд хурд (FPS) харагдана.",
    "Камергүйгээр үзэх бол Тохиргоо → Эх үүсвэр → Демо.",
    "Апп интернэтгүй ажиллана: видео утаснаас гардаггүй, хаашаа ч илгээгддэггүй.",
  ]],
];

function helpPage() {
  return `<div class="topbar"><div><h2 class="title">Заавар</h2></div><div class="grow"></div>${themeToggle()}</div>
    ${HELP.map(([title, lines]) => `<div class="card help" style="margin-top:12px"><h3>${title}</h3>
      <ul>${lines.map((l) => `<li>${l}</li>`).join("")}</ul></div>`).join("")}
    <p class="version">Шалгах логик нь компьютерын хувилбартай нэг код · MediaPipe Pose</p>`;
}

// ---- Зурах --------------------------------------------------------------------------------------------------------
function renderTabs(name) {
  tabs.classList.toggle("hidden", name === "workout");
  const active = name === "summary" ? "start" : name;
  tabs.innerHTML = TABS.map(([key, label, icon]) =>
    `<button class="${key === active ? "on" : ""}" data-tab="${key}">${icon}<span>${label}</span></button>`).join("");
}

function pageHtml(r) {
  if (r.name === "start") return startPage(r.step);
  if (r.name === "settings") return settingsPage();
  if (r.name === "summary") return summaryPage();
  if (r.name === "history") return historyPage();
  return helpPage();
}

/** animate=false: ижил хуудсыг шинэчлэх (сонголт солигдох) үед гүйлгэсэн байрлалыг хадгална. */
function render(animate = true) {
  const r = route();
  if (workout && r.name !== "workout") {   // «Буцах» товчоор дасгалаас гарсан
    const result = workout.abandon();
    workout = null;
    if (result) {
      lastResult = result;
      go("#/summary", true);
      return;
    }
  }
  if (r.name === "summary" && !lastResult) {
    go("#/start", true);
    return;
  }
  renderTabs(r.name);
  syncBars();
  if (r.name === "workout") {
    if (!workout) {
      screen.innerHTML = "";
      workout = mountWorkout(screen, { onExit: onWorkoutExit });
      window.__workout = workout;
    }
    lastRoute = r;
    return;
  }
  const old = screen.querySelector(".page");
  const scroll = old && !animate ? old.scrollTop : 0;
  let cls = "page";
  if (!animate) cls += " still";
  else if (r.name === "start" && lastRoute.name === "start" && r.step !== lastRoute.step) {
    cls += STEPS.indexOf(r.step) > STEPS.indexOf(lastRoute.step) ? " from-right" : " from-left";
  }
  screen.innerHTML = `<div class="${cls}" ${animate ? "" : 'style="animation:none"'}>${pageHtml(r)}</div>`;
  if (scroll) screen.querySelector(".page").scrollTop = scroll;
  lastRoute = r;
}

function onWorkoutExit({ items, record, to }) {
  workout = null;
  if (to === "workout") {   // камер нээгдээгүй -> демо
    render();
    return;
  }
  if (to === "summary" && items.length) {
    lastResult = { items, record };
    go("#/summary", true);
  } else {
    go("#/start", true);
  }
}

// ---- Үйлдлүүд -----------------------------------------------------------------------------------------------------
const LIMITS = { reps: [1, 50, 1], sets: [1, 10, 1], rest: [15, 180, 15] };

const actions = {
  theme() {
    settings.theme = settings.theme === "dark" ? "light" : "dark";
    saveSettings();
    applyTheme();
    render(false);
  },
  next() {
    const { step } = route();
    if (step === "exercise") {
      go("#/workout");
      return;
    }
    if (step === "level") applyLevel(settings.level);   // сонгосон түвшний зорилгыг хэрэглэнэ
    go("#/start/" + STEPS[STEPS.indexOf(step) + 1]);
  },
  back: () => history.back(),
  level(el) {
    applyLevel(el.dataset.key);
    render(false);
  },
  exercise(el) {
    settings.exercise = el.dataset.key;
    saveSettings();
    render(false);
  },
  set(el) {
    const { name, value } = el.dataset;
    if (name === "level") applyLevel(value);
    else settings[name] = value;
    if (name === "compute") engine.resetVision();
    saveSettings();
    render(false);
  },
  toggle(el) {
    settings[el.dataset.name] = !settings[el.dataset.name];
    saveSettings();
    render(false);
  },
  step(el) {
    const [lo, hi, by] = LIMITS[el.dataset.name];
    settings[el.dataset.name] = Math.min(hi, Math.max(lo, settings[el.dataset.name] + by * +el.dataset.dir));
    saveSettings();
    render(false);
  },
  workout: () => go("#/workout", route().name === "summary"),
  home: () => go("#/start"),
  clear() {
    if (confirmClear) clearHistory();
    confirmClear = !confirmClear;
    render(false);
  },
};

screen.addEventListener("click", (e) => {
  audio.unlock();
  if (workout) return;   // дасгалын дэлгэц өөрөө зохицуулна
  const el = e.target.closest("[data-act]");
  if (!el || !actions[el.dataset.act]) return;
  if (el.dataset.act !== "clear") confirmClear = false;
  actions[el.dataset.act](el);
});

tabs.addEventListener("click", (e) => {
  audio.unlock();
  const el = e.target.closest("[data-tab]");
  if (el) go("#/" + el.dataset.tab);
});

window.addEventListener("hashchange", () => {
  confirmClear = false;
  render();
});

engine.onChange(() => {
  if (route().name === "settings") render(false);   // хувилбарын дугаар ачаалагдсаны дараа гарна
});

applyTheme();
render();

// Өөрийгөө шалгах горим (?selftest=1): төлөвөө секунд тутам консолд бичнэ. Android дээр консол logcat-д гардаг тул
// GitHub Actions эмулятор дээр апп үнэхээр ачаалагдаж, давталт тоолж буйг эндээс шалгана.
if (QUERY.get("selftest") === "1") {
  setInterval(() => {
    const v = workout && workout.view;
    console.log("SELFTEST " + JSON.stringify({
      route: route().name, python: engine.state.python, vision: engine.state.vision, delegate: engine.state.delegate,
      stage: engine.state.stage, error: engine.state.error, phase: v ? v.phase : null, reps: v ? v.total_reps : null,
      message: v ? v.message_key : null, state: workout ? workout.state : null,
      perf: document.querySelector(".perf")?.textContent || "", panel: document.querySelector(".w-center")?.innerText || "",
    }));
  }, 1000);
}
// Шалгах логик ба илрүүлэгчийг урьдчилан ачаална: хэрэглэгч түвшин, дасгалаа сонгох хооронд бэлэн болно
setTimeout(() => {
  engine.loadPython().catch(() => {});
  if (settings.source !== "demo") engine.loadVision().catch(() => {});
}, 400);
