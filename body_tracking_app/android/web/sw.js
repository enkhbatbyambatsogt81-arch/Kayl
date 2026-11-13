// Service worker (зөвхөн вэб / iPhone хувилбарт): аппын файлуудыг утсанд хадгалж, дараагийн удаа интернэтгүй, хурдан
// нээнэ. build_web.py нь __VERSION__ ба __SHELL__-ийг угсрах үед бөглөнө: хувилбар солигдоход шинэ кэш үүсч, хуучин нь
// устна.
//
// Суулгахдаа зөвхөн жижиг файлуудыг (HTML, CSS, JavaScript, дүрс) татна. Том файлууд (Pyodide, MediaPipe, загвар; нийт
// ~38 MB) анх хэрэглэгдэх үедээ хадгалагдана: тэгэхгүй бол анхны нээлтэд хуудас ба service worker хоёр ижил файлыг
// зэрэг татаж, мобайл дата хоёр дахин зарцуулна.

const VERSION = "__VERSION__";
const SHELL = __SHELL__;
const CACHE = "ud-" + VERSION;

self.addEventListener("install", (event) => {
  event.waitUntil((async () => {
    const cache = await caches.open(CACHE);
    await cache.addAll(SHELL.map((f) => new Request(f, { cache: "reload" })));
    await self.skipWaiting();
  })());
});

self.addEventListener("activate", (event) => {
  event.waitUntil((async () => {
    for (const key of await caches.keys()) {
      if (key.startsWith("ud-") && key !== CACHE) await caches.delete(key);
    }
    await self.clients.claim();
  })());
});

self.addEventListener("fetch", (event) => {
  const req = event.request;
  const url = new URL(req.url);
  if (req.method !== "GET" || url.origin !== location.origin || req.headers.has("range")) return;
  event.respondWith((async () => {
    const cache = await caches.open(CACHE);
    // Хуудас (?selftest=1 гэх мэт нэмэлттэй ч) → хадгалсан index.html
    const hit = req.mode === "navigate"
      ? await cache.match("./index.html")
      : await cache.match(req, { ignoreSearch: true });
    if (hit) return hit;
    try {
      const res = await fetch(req);
      if (res.ok && res.type === "basic" && req.mode !== "navigate") {
        const key = new Request(url.origin + url.pathname);   // ?v=... гэх мэтийг хасаж нэг л хувийг хадгална
        event.waitUntil(cache.put(key, res.clone()).catch(() => { /* зай дутвал: дараа дахин татна */ }));
      }
      return res;
    } catch (e) {
      if (req.mode === "navigate") {
        return new Response("<meta charset=utf-8><meta name=viewport content='width=device-width'>" +
          "<p style='font:16px sans-serif;padding:24px'>Интернэтэд холбогдоод дахин нээнэ үү: апп анх удаа бүрэн " +
          "татагдаж амжаагүй байна.</p>", { headers: { "Content-Type": "text/html; charset=utf-8" } });
      }
      throw e;
    }
  })());
});
