// Дасгалын дэлгэц: камер (эсвэл демо) -> биеийн цэг -> Python логик -> зураг, тоолуур, зөвлөмж, дуу.

import * as audio from "./audio.js";
import { drawDemoBackground, drawFrameBorder, drawReadyRing, drawSkeleton, drawVideo, fitCanvas,
         placeRect } from "./draw.js";
import * as engine from "./engine.js";
import { ICONS } from "./figures.js";
import { EXERCISES, addHistory, saveSettings, settings } from "./store.js";

const PHASES = { setup: "Бэлтгэл", countdown: "Эхлэх гэж байна", active: "Дасгал", rest: "Амралт", done: "Дууссан" };
// Бэлтгэлийн шалгах жагсаалт (компьютерын хувилбарын overlays.py-тай ижил)
const CHECKS = {
  squat: ["Камер таныг харж байна", "Бүтэн бие кадрт багтсан", "Шулуун зогссон", "1 секунд хөдөлгөөнгүй байх"],
  pushup: ["Камер таныг харж байна", "Хажуугаараа, бүтэн бие харагдаж байна", "Гараа тэнийлгэсэн (планк)",
           "1 секунд хөдөлгөөнгүй байх"],
};
// Компьютерын мессежид товчлуурын нэр ордог тул утсанд өөрөөр хэлнэ
const MESSAGE_OVERRIDES = { rest: "Амралт. «Алгасах» дарж дараагийн сетээ эхлүүлж болно" };

const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

/**
 * root: дэлгэцийн элемент. onExit({items, record, to}): дасгал дуусахад. items = дасгал бүрийн дүн (хоосон байж болно),
 * to = "summary" | "start".
 */
export function mountWorkout(root, { onExit }) {
  const demo = settings.source === "demo";
  root.innerHTML = `
    <section class="workout">
      <video playsinline muted></video>
      <canvas></canvas>
      <div class="w-top" data-ref="top">
        <button class="icon-btn glass" data-act="leave" aria-label="Гарах">${ICONS.close}</button>
        <div class="seg" data-ref="exseg">
          ${Object.entries(EXERCISES).map(([k, e]) => `<button data-ex="${k}">${e.short}</button>`).join("")}
        </div>
        <button class="icon-btn glass ${demo ? "hide" : ""}" data-act="flip" aria-label="Камер солих">${ICONS.flip}</button>
        <button class="icon-btn glass" data-act="sound" aria-label="Дуу"></button>
      </div>
      <div class="w-count glass" data-ref="count">
        <div class="num"><span data-ref="num">0</span><small data-ref="target"></small></div>
        <div class="set" data-ref="set"></div>
        <div class="rep-dots" data-ref="dots"></div>
      </div>
      <div class="w-side">
        <div class="phase setup" data-ref="phase">${PHASES.setup}</div>
        <div class="score glass hide" data-ref="score"></div>
        <div class="score glass ${demo ? "" : "hide"}">Демо</div>
        <div class="perf" data-ref="perf"></div>
      </div>
      <div class="w-center" data-ref="center"></div>
      <div class="w-bottom" data-ref="bottom">
        <div class="panel glass hide" data-ref="checks"></div>
        <div class="depth glass hide" data-ref="depth">
          <span data-ref="depthText"></span>
          <div class="track"><div class="fill" data-ref="depthFill"></div></div>
        </div>
        <div class="msg glass info" data-ref="msg">Бэлтгэж байна…</div>
        <div class="w-controls">
          <button class="btn" data-act="pause">Түр зогсоох</button>
          <button class="btn" data-act="skip">Алгасах</button>
          <button class="btn primary" data-act="finish">Дуусгах</button>
        </div>
      </div>
    </section>`;

  const el = root.firstElementChild;
  const video = el.querySelector("video");
  const canvas = el.querySelector("canvas");
  const ctx = canvas.getContext("2d");
  const ref = {};
  for (const node of el.querySelectorAll("[data-ref]")) ref[node.dataset.ref] = node;
  const soundBtn = el.querySelector('[data-act="sound"]');
  const pauseBtn = el.querySelector('[data-act="pause"]');

  let alive = true, started = false, running = false, paused = false, exited = false;
  let t0 = 0, pausedAt = 0, pausedTotal = 0, doneTimer = null, wakeLock = null;
  let view = null, lastPoints = null, panelKey = "", flashTimer = null;
  let frames = 0, poseMsSum = 0, perfAt = 0;
  const shown = {};   // дэлгэцэнд байгаа утгууд: өөрчлөгдсөн үед л DOM-д бичнэ
  const wide = matchMedia("(orientation: landscape) and (max-height: 520px)");
  let inset = null;   // мэдээллийн самбарууд дэлгэцийн захаас хэр зай эзэлж буй (CSS пиксел)

  const now = () => performance.now();
  const clock = () => (now() - t0 - pausedTotal - (paused ? now() - pausedAt : 0)) / 1000;
  const mirror = () => !demo && settings.camera === "user" && settings.mirror;

  function set(name, value, apply) {
    if (shown[name] !== value) {
      shown[name] = value;
      apply(value);
    }
  }

  function panel(key, html) {
    if (panelKey !== key) {
      panelKey = key;
      ref.center.innerHTML = html;
    }
  }

  /** Зургийг самбаруудад дарагдуулахгүй байрлуулахын тулд тэдгээрийн хэмжээг авна (дэлгэц эргэхэд дахин). */
  function measure() {
    const box = el.getBoundingClientRect();
    const top = ref.top.getBoundingClientRect().bottom - box.top + 6;
    if (wide.matches) {
      inset = { top, bottom: 0, left: 0, right: box.right - ref.bottom.getBoundingClientRect().left + 8 };
    } else {
      inset = { top: demo ? ref.count.getBoundingClientRect().bottom - box.top + 6 : top, left: 0, right: 0,
                bottom: box.bottom - ref.msg.getBoundingClientRect().top + 8 };
    }
  }

  function updateSoundButton() {
    soundBtn.innerHTML = settings.sound ? ICONS.sound : ICONS.mute;
    soundBtn.classList.toggle("off", !settings.sound);
  }

  function showExercise(name) {
    for (const b of ref.exseg.children) b.classList.toggle("on", b.dataset.ex === name);
  }

  // ---- Эхлүүлэх ---------------------------------------------------------------------------------------------------
  async function boot() {
    updateSoundButton();
    showExercise(settings.exercise);
    panel("loading", `<div class="panel glass"><div class="spinner"></div>
      <p style="text-align:center">Ачаалж байна… Анх нээхэд хэдэн секунд болно.</p></div>`);
    try {
      await Promise.all([engine.loadPython(), demo ? null : engine.loadVision()]);
    } catch {
      if (alive) failure(engine.state.error || "Ачаалахад алдаа гарлаа.", false);
      return;
    }
    if (!alive) return;
    if (!demo && !(await startCamera())) return;
    engine.py.start({
      exercise: settings.exercise, level: settings.level, reps: settings.reps, sets: settings.sets,
      rest: settings.rest, free_mode: settings.free_mode, auto_detect: settings.auto_detect, demo,
    });
    t0 = now();
    started = running = true;
    panel("", "");
    try {
      wakeLock = await navigator.wakeLock?.request("screen");   // дасгалын үед дэлгэц унтрахгүй
    } catch { /* зөвшөөрөгдөөгүй бол Android талын FLAG_KEEP_SCREEN_ON хангалттай */ }
    schedule();
  }

  async function startCamera() {
    try {
      await engine.openCamera(video, settings.camera);
      return true;
    } catch (e) {
      if (alive) failure(engine.CAMERA_ERRORS[e && e.name] || `Камер нээгдсэнгүй: ${e && e.message ? e.message : e}`, true);
      return false;
    }
  }

  function failure(message, camera) {
    running = false;
    ref.msg.textContent = "Эхлүүлж чадсангүй";
    ref.msg.className = "msg glass warn";
    panel("error:" + message, `<div class="panel glass"><h3>${camera ? "Камер нээгдсэнгүй" : "Алдаа гарлаа"}</h3>
      <p>${esc(message)}</p>
      ${camera ? "" : `<p style="margin-top:8px;font-size:13px">Давтагдвал Play Store-оос «Android System WebView»
        болон «Chrome»-оо шинэчлээд дахин оролдоно уу.</p>`}
      <div class="actions">
        <button class="btn primary" data-act="retry">Дахин оролдох</button>
        ${camera ? '<button class="btn" data-act="demo">Демо үзэх (камергүй)</button>' : ""}
        <button class="btn" data-act="home">Эхлэл рүү</button>
      </div></div>`);
  }

  // ---- Кадр бүрт --------------------------------------------------------------------------------------------------
  function schedule() {
    if (!alive || !running) return;
    if (!demo && video.requestVideoFrameCallback) video.requestVideoFrameCallback(tick);
    else requestAnimationFrame(tick);
  }

  function tick() {
    if (!alive || !running) return;
    if (!paused) {
      try {
        step();
      } catch (e) {
        console.error(e);
        if (!demo && engine.state.delegate === "GPU") {   // видео картын алдаа: процессороор үргэлжлүүлнэ
          recover(e);
        } else {
          failure("Дасгалын явцад алдаа гарлаа: " + (e && e.message ? e.message : e), false);
        }
        return;
      }
    }
    schedule();
  }

  async function recover(error) {
    running = false;
    try {
      if (!(await engine.useCpu())) throw error;
    } catch (e) {
      if (alive) failure("Дасгалын явцад алдаа гарлаа: " + (e && e.message ? e.message : e), false);
      return;
    }
    if (!alive) return;
    settings.compute = "cpu";   // дараагийн удаа шууд процессороор
    saveSettings();
    running = true;
    schedule();
  }

  function step() {
    const t = clock();
    if (demo) {
      view = engine.py.demoFrame(t);
      lastPoints = null;
    } else {
      const w = video.videoWidth, h = video.videoHeight;
      if (!w || !h) return;
      const t1 = now();
      lastPoints = engine.detect(video, w, h);
      poseMsSum += now() - t1;
      view = engine.py.frame(lastPoints, w, h, t);
    }
    frames += 1;
    draw();
    hud();
    if (settings.sound) audio.playEvents(view.events);
    if (view.phase === "done" && doneTimer === null) {
      doneTimer = setTimeout(() => finish("summary"), 1200);   // төгсгөлийн дууг сонсгоод дүн рүү
    }
  }

  function draw() {
    const k = fitCanvas(canvas);
    const src = demo ? view.pose : { width: video.videoWidth, height: video.videoHeight };
    if (!src || !src.width) return;
    if (!inset) measure();
    const pad = { top: inset.top * k, bottom: inset.bottom * k, left: inset.left * k, right: inset.right * k };
    const rect = placeRect(canvas.width, canvas.height, src.width, src.height, pad, demo ? view.pose.focus : null);
    let get = null;
    if (demo) {
      drawDemoBackground(ctx, rect, view.pose.floor);
      get = (i) => view.pose.points[i];
    } else {
      drawVideo(ctx, video, rect, mirror());
      if (lastPoints) get = (i) => [lastPoints[i * 4], lastPoints[i * 4 + 1], lastPoints[i * 4 + 3]];
    }
    if (get) drawSkeleton(ctx, get, rect, mirror(), view, engine.state.info.skeleton, k);
    if (view.phase === "setup") {
      const ready = view.message_key === "hold_position";
      drawFrameBorder(ctx, rect, ready, k);
      if (ready) drawReadyRing(ctx, rect, view.ready_progress || 0, k);
    }
  }

  function hud() {
    const v = view;
    const done = v.set_reps.length;
    set("num", v.target ? done : v.total_reps, (x) => { ref.num.textContent = x; });
    set("target", v.target ? ` / ${v.target}` : "", (x) => { ref.target.textContent = x; });
    set("set", v.target ? `Сет ${v.set_index} / ${v.sets_total}` : "Чөлөөт горим", (x) => { ref.set.textContent = x; });
    const dots = v.target && v.target <= 20
      ? Array.from({ length: v.target }, (_, i) => (i < done ? (v.set_reps[i].correct ? "g" : "b") : "o")).join("")
      : "";
    set("dots", dots, (x) => {
      ref.dots.innerHTML = [...x].map((c) => `<i class="${c === "g" ? "good" : c === "b" ? "bad" : ""}"></i>`).join("");
    });
    set("phase", v.phase, (x) => {
      ref.phase.textContent = PHASES[x] || x;
      ref.phase.className = "phase " + x;
    });
    set("exercise", v.exercise, (x) => {
      showExercise(x);
      if (settings.exercise !== x) {   // автоматаар танигдаж солигдсон
        settings.exercise = x;
        saveSettings();
      }
    });
    const score = v.last_rep ? `Оноо: ${v.last_rep.score}` : "";
    set("score", score, (x) => {
      ref.score.textContent = x;
      ref.score.classList.toggle("hide", !x);
    });
    set("msg", (MESSAGE_OVERRIDES[v.message_key] || v.message) + "|" + v.level, () => {
      ref.msg.textContent = MESSAGE_OVERRIDES[v.message_key] || v.message;
      ref.msg.className = "msg glass " + v.level;
    });

    // Гүний заалт: дээд байрлалаас зорилтот гүн хүртэл хэдэн хувь буусан
    if (v.phase === "active" && v.angle != null && v.depth_target != null && v.top_angle != null) {
      const angle = Math.min(v.angle, v.depth_angle ?? v.angle);
      const frac = Math.max(0, Math.min(1, (v.top_angle - angle) / (v.top_angle - v.depth_target)));
      const joint = EXERCISES[v.exercise].joint;
      set("depthText", `Гүн: ${joint} ${Math.round(v.angle)}°  (зорилт ≤ ${Math.round(v.depth_target)}°)`,
          (x) => { ref.depthText.textContent = x; });
      set("depthFill", Math.round(frac * 100), (x) => {
        ref.depthFill.style.width = x + "%";
        ref.depthFill.classList.toggle("ok", x >= 100);
      });
      set("depthShow", true, () => ref.depth.classList.remove("hide"));
    } else {
      set("depthShow", false, () => ref.depth.classList.add("hide"));
    }

    if (v.new_rep && v.last_rep) {
      ref.count.classList.remove("flash-good", "flash-bad");
      ref.count.classList.add(v.last_rep.correct ? "flash-good" : "flash-bad");
      clearTimeout(flashTimer);
      flashTimer = setTimeout(() => ref.count.classList.remove("flash-good", "flash-bad"), 450);
    }
    centerPanel(v);

    const t = now();
    if (t - perfAt > 1000) {
      const fps = (frames * 1000) / (t - perfAt);
      ref.perf.textContent = demo ? `${fps.toFixed(0)} FPS`
        : `${fps.toFixed(0)} FPS · pose ${(poseMsSum / Math.max(frames, 1)).toFixed(0)} ms · ${engine.state.delegate}`;
      frames = 0;
      poseMsSum = 0;
      perfAt = t;
    }
  }

  function centerPanel(v) {
    // Бэлтгэлийн шалгах жагсаалт: биеийг халхлахгүйн тулд голд биш, доод самбарын дээр
    const items = v.phase === "setup" && v.checks ? [...v.checks, (v.ready_progress || 0) >= 1] : null;
    set("checks", items ? v.exercise + items.join() : "", (x) => {
      ref.checks.classList.toggle("hide", !x);
      if (!x) return;
      const next = items.indexOf(false);
      ref.checks.innerHTML = `<ul class="checks">${CHECKS[v.exercise].map((label, i) =>
        `<li class="${items[i] ? "ok" : i === next ? "next" : ""}"><b>${items[i] ? "✓" : i === next ? "›" : ""}</b>
         ${label}</li>`).join("")}</ul>`;
    });
    if (items) {
      panel("", "");
    } else if (v.phase === "countdown" && v.countdown != null) {
      panel("count:" + v.countdown, `<div class="count-ring glass">${v.countdown}</div>`);
    } else if (v.phase === "rest") {
      const left = Math.ceil(v.rest_left || 0);
      panel("rest:" + left, `<div class="panel glass" style="text-align:center"><h3>Амралт</h3>
        <div class="rest-clock">${Math.floor(left / 60)}:${String(left % 60).padStart(2, "0")}</div>
        <p>Дараагийн сет: ${v.set_index + 1} / ${v.sets_total}</p>
        <div class="actions"><button class="btn primary" data-act="skip">Алгасах</button></div></div>`);
    } else {
      panel("", "");
    }
  }

  // ---- Удирдлага --------------------------------------------------------------------------------------------------
  function setPaused(value, panelHtml) {
    if (!running) return;
    if (value && !paused) {
      pausedAt = now();
      paused = true;
    } else if (!value && paused) {
      pausedTotal += now() - pausedAt;
      paused = false;
    }
    if (paused) {
      panelKey = "paused";
      ref.center.innerHTML = panelHtml || `<div class="panel glass" style="text-align:center"><h3>Түр зогссон</h3>
        <div class="actions"><button class="btn primary" data-act="resume">Үргэлжлүүлэх</button></div></div>`;
    } else {
      panel("", "");
    }
    pauseBtn.textContent = paused ? "Үргэлжлүүлэх" : "Түр зогсоох";
  }

  function repsDone() {
    return started ? engine.py.summary().reduce((n, s) => n + s.reps, 0) : 0;
  }

  /** Дасгалыг дуусгана: дүнг түүхэнд хадгалаад дэлгэцээс гарна. */
  function finish(to) {
    if (exited) return;
    exited = true;
    let items = [], record = null;
    if (started) {
      items = engine.py.summary();
      record = addHistory(items, clock());
    }
    destroy();
    onExit({ items, record, to: items.length && to === "summary" ? "summary" : "start" });
  }

  function leave() {
    const n = repsDone();
    if (!n) {
      finish("start");
      return;
    }
    setPaused(true, `<div class="panel glass"><h3>Дасгалаас гарах уу?</h3>
      <p>Та ${n} давталт хийсэн. Үр дүн хадгалагдана.</p>
      <div class="actions">
        <button class="btn primary" data-act="summary">Дүнгээ харах</button>
        <button class="btn" data-act="resume">Үргэлжлүүлэх</button>
        <button class="btn" data-act="home">Эхлэл рүү</button>
      </div></div>`);
  }

  async function flipCamera() {
    if (demo || !running) return;
    settings.camera = settings.camera === "user" ? "environment" : "user";
    saveSettings();
    running = false;
    panel("loading", '<div class="panel glass"><div class="spinner"></div></div>');
    if (await startCamera()) {
      running = true;
      panel("", "");
      schedule();
    }
  }

  const actions = {
    leave,
    flip: flipCamera,
    sound() {
      settings.sound = !settings.sound;
      saveSettings();
      updateSoundButton();
    },
    pause: () => setPaused(!paused),
    resume: () => setPaused(false),
    skip() {
      if (running && !paused) engine.py.command("skip");
    },
    finish: () => finish("summary"),
    summary: () => finish("summary"),
    home: () => finish("start"),
    retry() {
      panelKey = "";
      boot();
    },
    demo() {
      settings.source = "demo";
      saveSettings();
      exited = true;
      destroy();
      onExit({ items: [], record: null, to: "workout" });
    },
  };

  function onClick(e) {
    audio.unlock();
    const ex = e.target.closest("[data-ex]");
    if (ex && running) {
      engine.py.command("exercise", ex.dataset.ex);
      settings.exercise = ex.dataset.ex;
      saveSettings();
      showExercise(ex.dataset.ex);
      return;
    }
    const act = e.target.closest("[data-act]");
    if (act && actions[act.dataset.act]) actions[act.dataset.act]();
  }

  async function onVisibility() {
    if (!alive || !running || demo) {
      if (alive && running && document.hidden) setPaused(true);
      return;
    }
    if (document.hidden) {
      setPaused(true);
      engine.closeCamera();   // апп ард байх үед камерыг чөлөөлнө
    } else {
      running = false;
      if (await startCamera()) {
        running = true;
        schedule();
      }
    }
  }

  function destroy() {
    if (!alive) return;
    alive = false;
    running = false;
    clearTimeout(doneTimer);
    clearTimeout(flashTimer);
    engine.closeCamera();
    el.removeEventListener("click", onClick);
    document.removeEventListener("visibilitychange", onVisibility);
    window.removeEventListener("resize", onResize);
    try { wakeLock?.release(); } catch { /* аль хэдийн суларсан */ }
  }

  const onResize = () => { inset = null; };
  el.addEventListener("click", onClick);
  document.addEventListener("visibilitychange", onVisibility);
  window.addEventListener("resize", onResize);
  boot();

  return {
    destroy,
    /** Буцах товчоор гарсан үед: давталт хийсэн бол дүнг хадгалаад буцаана. */
    abandon() {
      if (exited) return null;
      exited = true;
      let items = [], record = null;
      if (started) {
        items = engine.py.summary();
        record = addHistory(items, clock());
      }
      destroy();
      return items.length ? { items, record } : null;
    },
    get view() { return view; },
    get state() { return { running, paused, demo, panel: panelKey }; },
  };
}
