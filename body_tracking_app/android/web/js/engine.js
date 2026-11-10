// Хөдөлгүүр: (1) Python логик Pyodide дээр, (2) MediaPipe Pose Landmarker, (3) камер.
//
// Давталт тоолох, техник шалгах код нь компьютерын хувилбарынхтай яг ижил Python файлууд (py/app.zip):
// form_checker/mobile.py-ийн функцуудыг эндээс дуудна. Бүх оролт / гаралт JSON мөр.

import { saveSettings, settings } from "./store.js";

const base = new URL("../", import.meta.url).href;

export const state = {
  python: "idle",    // idle | loading | ready | error
  vision: "idle",
  error: null,
  stage: { python: "", vision: "" },   // ачаалалтын аль алхам дээр байгаа (оношлогоонд)
  delegate: null,    // GPU | CPU
  info: null,        // mobile.info(): хувилбар, араг ясны холбоос
  gpuFailed: false,  // өмнөх удаа видео картаар гацсан тул процессор руу шилжсэн
};

const listeners = new Set();
export function onChange(fn) {
  listeners.add(fn);
  return () => listeners.delete(fn);
}
function emit() {
  for (const fn of listeners) fn(state);
}

let mobile = null;       // Python модуль form_checker.mobile
let landmarker = null;
let pythonPromise = null;
let visionPromise = null;
let visionApi = null, fileset = null;

// Видео картын хамгаалалт. Зарим утасны WebView видео картаар илрүүлэгч үүсгэх / эхний кадрыг боловсруулах үед гацаж
// эсвэл унаж болно. Тэр эрсдэлтэй алхмын өмнө тэмдэг тавьж, амжилттай дуусмагц арилгана. Дараагийн удаа апп нээгдэхэд
// тэмдэг хэвээр байвал өмнөх оролдлого дуусаагүй гэсэн үг: процессор руу өөрөө шилжинэ.
const GPU_FLAG = "ud.gpu.pending";
const flag = {
  get: () => { try { return localStorage.getItem(GPU_FLAG) === "1"; } catch { return false; } },
  set: () => { try { localStorage.setItem(GPU_FLAG, "1"); } catch { /* хадгалах боломжгүй */ } },
  clear: () => { try { localStorage.removeItem(GPU_FLAG); } catch { /* хадгалах боломжгүй */ } },
};
let firstGpuFrame = false;   // видео картаар эхний кадрыг хараахан боловсруулаагүй

export function loadPython() {
  if (pythonPromise) return pythonPromise;
  state.python = "loading";
  emit();
  pythonPromise = (async () => {
    if (typeof WebAssembly !== "object") throw new Error("Энэ утасны WebView WebAssembly дэмждэггүй байна");
    state.stage.python = "pyodide";
    const { loadPyodide } = await import(base + "vendor/pyodide/pyodide.mjs");
    const pyodide = await loadPyodide({ indexURL: base + "vendor/pyodide/" });
    state.stage.python = "numpy";
    await pyodide.loadPackage("numpy");
    state.stage.python = "app";
    const zip = await (await fetch(base + "py/app.zip")).arrayBuffer();
    pyodide.unpackArchive(zip, "zip", { extractDir: "/home/pyodide/app" });
    pyodide.runPython('import sys\nsys.path.insert(0, "/home/pyodide/app")');
    mobile = pyodide.pyimport("form_checker.mobile");
    state.info = JSON.parse(mobile.info());
    state.python = "ready";
    state.stage.python = "ready";
    emit();
  })().catch((e) => {
    state.python = "error";
    state.error = "Шалгах логик ачаалагдсангүй: " + (e && e.message ? e.message : e);
    pythonPromise = null;
    emit();
    throw e;
  });
  return pythonPromise;
}

async function createLandmarker(vision, fileset, delegate) {
  return vision.PoseLandmarker.createFromOptions(fileset, {
    baseOptions: { modelAssetPath: base + "models/pose_landmarker_lite.task", delegate },
    runningMode: "VIDEO",
    numPoses: 1,
    minPoseDetectionConfidence: 0.5,
    minPosePresenceConfidence: 0.5,
    minTrackingConfidence: 0.5,
  });
}

export function loadVision() {
  if (visionPromise) return visionPromise;
  state.vision = "loading";
  emit();
  visionPromise = (async () => {
    state.stage.vision = "bundle";
    visionApi = visionApi || await import(base + "vendor/mediapipe/vision_bundle.mjs");
    fileset = fileset || await visionApi.FilesetResolver.forVisionTasks(base + "vendor/mediapipe/wasm");
    // Эхлээд видео картаар (хурдан). Зарим утасны WebView-д WebGL дутуу байдаг: тэр үед процессороор ажиллуулна.
    // Тохиргоо → Тооцоолол → Процессор (эсвэл туршилтад ?delegate=cpu): шууд процессороор.
    if (settings.compute !== "cpu" && flag.get()) {   // өмнөх удаа видео картаар гацсан / унасан
      settings.compute = "cpu";
      saveSettings();
      flag.clear();
      state.gpuFailed = true;
    }
    const cpuOnly = settings.compute === "cpu" || new URLSearchParams(location.search).get("delegate") === "cpu";
    const order = cpuOnly ? ["CPU"] : ["GPU", "CPU"];
    let failure = null;
    for (const delegate of order) {
      try {
        state.stage.vision = delegate;
        if (delegate === "GPU") flag.set();
        landmarker = await createLandmarker(visionApi, fileset, delegate);
        flag.clear();
        firstGpuFrame = delegate === "GPU";
        state.delegate = delegate;
        state.stage.vision = "ready";
        break;
      } catch (e) {
        flag.clear();   // алдаа буцаасан бол гацаагүй: доор процессороор үргэлжлүүлнэ
        console.warn(delegate + " delegate failed", e);
        failure = e;
      }
    }
    if (!landmarker) throw failure;
    state.vision = "ready";
    emit();
  })().catch((e) => {
    state.vision = "error";
    state.error = "Биеийн цэг илрүүлэгч ачаалагдсангүй: " + (e && e.message ? e.message : e);
    visionPromise = null;
    emit();
    throw e;
  });
  return visionPromise;
}

/** Тохиргоо солигдоход: илрүүлэгчийг дараагийн удаа шинээр үүсгэнэ. */
export function resetVision() {
  try { landmarker?.close(); } catch { /* аль хэдийн хаагдсан */ }
  landmarker = null;
  visionPromise = null;
  state.vision = "idle";
  state.delegate = null;
  state.gpuFailed = false;
  flag.clear();
}

/** Видео картаар илрүүлэх явцад алдаа гарвал процессор руу шилжинэ. Шилжсэн бол true. */
export async function useCpu() {
  if (state.delegate !== "GPU" || !visionApi) return false;
  try { landmarker?.close(); } catch { /* үл хамаарна */ }
  landmarker = await createLandmarker(visionApi, fileset, "CPU");
  state.delegate = "CPU";
  emit();
  return true;
}

// ---- Python талын дуудлагууд ------------------------------------------------------------------------------------
export const py = {
  start: (options) => JSON.parse(mobile.start(JSON.stringify(options))),
  frame: (points, width, height, t) => JSON.parse(mobile.frame(points, width, height, t)),
  demoFrame: (t) => JSON.parse(mobile.demo_frame(t)),
  command: (name, arg) => mobile.command(name, arg),
  summary: () => JSON.parse(mobile.summary()),
};

// ---- Биеийн цэг -------------------------------------------------------------------------------------------------
const points = new Float64Array(33 * 4);
let lastStamp = 0;

/** Видеоны одоогийн кадраас 33 цэг: [x, y, z (пикселээр), visibility] × 33, эсвэл хүн олдоогүй бол null. */
export function detect(video, width, height) {
  const stamp = Math.max(performance.now(), lastStamp + 1);   // VIDEO горим монотон өсөх хугацаа шаарддаг
  lastStamp = stamp;
  if (firstGpuFrame) flag.set();
  const result = landmarker.detectForVideo(video, stamp);
  if (firstGpuFrame) {
    firstGpuFrame = false;
    flag.clear();
  }
  const lms = result.landmarks && result.landmarks[0];
  if (!lms || lms.length < 33) return null;
  for (let i = 0; i < 33; i++) {
    const p = lms[i];
    points[i * 4] = p.x * width;
    points[i * 4 + 1] = p.y * height;
    points[i * 4 + 2] = p.z * width;
    points[i * 4 + 3] = p.visibility ?? 1.0;
  }
  return points;
}

// ---- Камер ------------------------------------------------------------------------------------------------------
let stream = null;

export const CAMERA_ERRORS = {
  NotAllowedError: "Камер ашиглах зөвшөөрөл өгөөгүй байна. Утасны Тохиргоо → Апп → Ухаалаг дасгалжуулагч → " +
                   "Зөвшөөрөл → Камер-ыг зөвшөөрөөд дахин оролдоно уу.",
  NotFoundError: "Камер олдсонгүй.",
  NotReadableError: "Камерыг өөр апп ашиглаж байна. Тэр аппыг хаагаад дахин оролдоно уу.",
  OverconstrainedError: "Сонгосон камер энэ утсанд алга. Нөгөө камерыг сонгоно уу.",
};

export async function openCamera(video, facing) {
  closeCamera();
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    throw Object.assign(new Error("Энэ орчинд камер ашиглах боломжгүй байна."), { name: "Unsupported" });
  }
  stream = await navigator.mediaDevices.getUserMedia({
    audio: false,
    video: { facingMode: facing, width: { ideal: 640 }, height: { ideal: 480 }, frameRate: { ideal: 30 } },
  });
  video.srcObject = stream;
  video.muted = true;
  video.playsInline = true;
  await video.play();
  return stream;
}

export function closeCamera() {
  if (stream) {
    for (const track of stream.getTracks()) track.stop();
    stream = null;
  }
}
