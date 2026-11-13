// Апп аль орчинд ажиллаж байгааг ялгана: Android апп (APK доторх WebView), iPhone / iPad (Safari эсвэл нүүр дэлгэцэнд
// нэмсэн вэб апп), эсвэл бусад хөтөч. Зөвхөн тайлбар текст, service worker-т хэрэглэнэ: шалгах логик бүгд ижил.

export const ANDROID_APP = typeof window.AndroidApp === "object" && window.AndroidApp !== null;
// iPadOS 13+ өөрийгөө Mac гэж танилцуулдаг тул мэдрэгчтэй дэлгэцээр нь ялгана
export const IOS = !ANDROID_APP && (/iPhone|iPad|iPod/.test(navigator.userAgent) ||
  (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1));
// Нүүр дэлгэцэнд нэмсэн (хаягийн мөргүй, тусдаа апп шиг) нээгдсэн эсэх
export const STANDALONE = matchMedia("(display-mode: standalone)").matches || navigator.standalone === true;

export const NAME = ANDROID_APP ? "Android" : IOS ? "iPhone" : "Вэб";

/** Камерын зөвшөөрлийг хаанаас асаахыг тайлбарлана. */
export const CAMERA_PERMISSION = ANDROID_APP
  ? "утасны Тохиргоо → Апп → Ухаалаг дасгалжуулагч → Зөвшөөрөл → Камер-ыг зөвшөөрнө."
  : IOS
    ? "iPhone-ы Тохиргоо (Settings) → Safari → Камер (Camera) → «Асуух» эсвэл «Зөвшөөрөх»-ийг сонгоод аппаа хаагаад " +
      "дахин нээнэ. Safari дээр бол хаягийн мөрний «аА» → Вэбсайтын тохиргоо → Камер → Зөвшөөрөх."
    : "хөтчийн хаягийн мөрний түгжээний дүрс → Камер → Зөвшөөрөх, дараа нь хуудсаа дахин ачаална.";

/** Апп ачаалагдахгүй үед юуг шинэчлэхийг зөвлөнө. */
export const UPDATE_HINT = ANDROID_APP
  ? "Давтагдвал Play Store-оос «Android System WebView» болон «Chrome»-оо шинэчлээд дахин оролдоно уу."
  : IOS
    ? "Давтагдвал iPhone-оо шинэчилнэ үү (Тохиргоо → Ерөнхий → Програм хангамжийн шинэчлэл). iOS 16.4 ба түүнээс " +
      "шинэ хувилбар хэрэгтэй. Бусад аппаа хаагаад дахин оролдож болно."
    : "Давтагдвал хөтчөө шинэчлээд дахин оролдоно уу.";

/**
 * Вэб хувилбарт (iPhone, компьютерын хөтөч) service worker бүртгэнэ: анх нээхэд бүх файл утсанд хадгалагдаж, дараа нь
 * интернэтгүй ажиллаж, хурдан нээгдэнэ. Android апп файлуудаа APK-аасаа шууд уншдаг тул хэрэггүй.
 * Шинэ хувилбар гарвал дасгалын дэлгэц дээр биш үед хуудсыг өөрөө дахин ачаална.
 */
export function registerServiceWorker(busy) {
  if (ANDROID_APP || !("serviceWorker" in navigator) || !window.isSecureContext) return;
  const hadController = !!navigator.serviceWorker.controller;
  let reloading = false;
  const reload = () => {
    if (reloading) return;
    if (busy()) {   // дасгалын дундуур дахин ачаалахгүй: дэлгэц солигдох үед
      window.addEventListener("hashchange", reload, { once: true });
      return;
    }
    reloading = true;
    location.reload();
  };
  navigator.serviceWorker.addEventListener("controllerchange", () => { if (hadController) reload(); });
  navigator.serviceWorker.register("sw.js").catch((e) => console.warn("service worker", e));
}
