// Видеоны кадр ба араг ясыг canvas дээр зурна. Компьютерын хувилбарын ui.py-тай ижил дүрслэл:
// саарал яс, ногоон үе, алдаатай үе улаан, гол үений өнцөг нумаар.

const GREEN = "#50c850", RED = "#e63c3c", ORANGE = "#ffa500", WHITE = "#ffffff", GRAY = "#aaaaaa";
const SIDES = {
  left: { shoulder: 11, elbow: 13, wrist: 15, hip: 23, knee: 25, ankle: 27 },
  right: { shoulder: 12, elbow: 14, wrist: 16, hip: 24, knee: 26, ankle: 28 },
};
const ARC = { squat: ["hip", "knee", "ankle"], pushup: ["shoulder", "elbow", "wrist"] };

/** Canvas-ийн пикселийн хэмжээг дэлгэцийн хэмжээнд тааруулна (хэт том болгохгүй: утсанд зурах ачаалал). */
export function fitCanvas(canvas) {
  const dpr = Math.min(window.devicePixelRatio || 1, 2);
  let w = Math.round(canvas.clientWidth * dpr), h = Math.round(canvas.clientHeight * dpr);
  const cap = 1280 / Math.max(w, h, 1);
  if (cap < 1) { w = Math.round(w * cap); h = Math.round(h * cap); }
  if (canvas.width !== w || canvas.height !== h) { canvas.width = w; canvas.height = h; }
  return canvas.clientWidth ? w / canvas.clientWidth : 1;   // CSS пиксел -> canvas пиксел
}

/**
 * Эх зургийг (sw × sh) canvas-д бүтнээр нь багтаах тэгш өнцөгт. Бие бүтэн харагдах нь чухал тул тайрахгүй.
 * Илүү зай гарвал зургийг мэдээллийн самбаруудаас (inset: canvas пикселээр) холдуулна: босоо дэлгэцэд дээш,
 * хэвтээ дэлгэцэд зүүн тийш шахна. focus = [x0, y0, x1, y1] өгвөл (демо) зөвхөн тэр хэсгийг самбаруудын
 * хооронд багтааж томруулна. Буцаах .box = дэлгэцэнд харагдах хэсэг (хүрээ зурахад).
 */
export function placeRect(cw, ch, sw, sh, inset, focus) {
  const { top = 0, bottom = 0, left = 0, right = 0 } = inset || {};
  if (focus) {
    const [x0, y0, x1, y1] = focus;
    const aw = Math.max(1, cw - left - right), ah = Math.max(1, ch - top - bottom);
    const scale = Math.min(aw / (x1 - x0), ah / (y1 - y0));
    const w = (x1 - x0) * scale, h = (y1 - y0) * scale;
    const x = left + (aw - w) / 2, y = top + (ah - h) / 2;
    return { x: x - x0 * scale, y: y - y0 * scale, w: sw * scale, h: sh * scale, scale, box: { x, y, w, h } };
  }
  const scale = Math.min(cw / sw, ch / sh);
  const w = sw * scale, h = sh * scale;
  const shift = (slack, a, b) => (slack >= a + b ? a : (slack * a) / Math.max(a + b, 1));
  const x = shift(cw - w, left, right), y = shift(ch - h, top, bottom);
  return { x, y, w, h, scale, box: { x, y, w, h } };
}

export function drawVideo(ctx, video, rect, mirror) {
  ctx.fillStyle = "#000";
  ctx.fillRect(0, 0, ctx.canvas.width, ctx.canvas.height);
  ctx.save();
  if (mirror) {
    ctx.translate(rect.x + rect.w, rect.y);
    ctx.scale(-1, 1);
  } else {
    ctx.translate(rect.x, rect.y);
  }
  ctx.drawImage(video, 0, 0, rect.w, rect.h);
  ctx.restore();
}

/** Демо: камерын оронд бараан дэвсгэр ба шалны шугам (дэлгэц дүүрэн). */
export function drawDemoBackground(ctx, rect, floorY) {
  const { width, height } = ctx.canvas;
  const y = rect.y + floorY * rect.scale;
  const g = ctx.createLinearGradient(0, 0, 0, height);
  g.addColorStop(0, "#343e46");
  g.addColorStop(1, "#202428");
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, width, height);
  ctx.fillStyle = "rgba(0, 0, 0, .22)";
  ctx.fillRect(0, y, width, height - y);
  ctx.strokeStyle = "#6e6e6e";
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.moveTo(0, y);
  ctx.lineTo(width, y);
  ctx.stroke();
}

/**
 * get(i) -> [x, y, visibility] эх зургийн пикселээр. view: mobile.py-ийн буцаасан dict.
 * k: зураасны зузааныг дэлгэцийн нягтралд тааруулах үржигдэхүүн.
 */
export function drawSkeleton(ctx, get, rect, mirror, view, skeleton, k = 1) {
  const pt = (i) => {
    const [x, y, v] = get(i);
    const px = mirror ? rect.x + rect.w - x * rect.scale : rect.x + x * rect.scale;
    return [px, rect.y + y * rect.scale, v];
  };
  const pts = [];
  for (let i = 0; i < 33; i++) pts.push(pt(i));
  const bad = new Set(view.bad_joints || []);

  ctx.lineCap = "round";
  ctx.strokeStyle = GRAY;
  ctx.lineWidth = 3 * k;
  ctx.beginPath();
  for (const [a, b] of skeleton) {
    if (pts[a][2] > 0.5 && pts[b][2] > 0.5) {
      ctx.moveTo(pts[a][0], pts[a][1]);
      ctx.lineTo(pts[b][0], pts[b][1]);
    }
  }
  ctx.stroke();

  ctx.fillStyle = GREEN;
  for (let i = 11; i < 33; i++) {
    if (pts[i][2] > 0.5 && !bad.has(i)) {
      ctx.beginPath();
      ctx.arc(pts[i][0], pts[i][1], 5 * k, 0, Math.PI * 2);
      ctx.fill();
    }
  }
  // Алдаатай үеийг хамгийн сүүлд, томоор (бусад цэгт дарагдахгүй)
  for (const i of bad) {
    ctx.beginPath();
    ctx.arc(pts[i][0], pts[i][1], 9 * k, 0, Math.PI * 2);
    ctx.fillStyle = RED;
    ctx.fill();
    ctx.lineWidth = 1.5 * k;
    ctx.strokeStyle = WHITE;
    ctx.stroke();
  }

  // Гол үений өнцөг (өвдөг / тохой)
  if (view.angle != null && view.side && view.angle_joint != null) {
    const side = SIDES[view.side];
    const [aName, , cName] = ARC[view.exercise];
    const j = pts[view.angle_joint];
    if (view.view === "side") {
      const p1 = pts[side[aName]], p2 = pts[side[cName]];
      let a1 = Math.atan2(p1[1] - j[1], p1[0] - j[0]);
      const a2 = Math.atan2(p2[1] - j[1], p2[0] - j[0]);
      let sweep = (a2 - a1) % (Math.PI * 2);
      if (sweep < 0) sweep += Math.PI * 2;
      if (sweep > Math.PI) { a1 = a2; sweep = Math.PI * 2 - sweep; }
      ctx.beginPath();
      ctx.arc(j[0], j[1], 30 * k, a1, a1 + sweep);
      ctx.lineWidth = 3.5 * k;
      ctx.strokeStyle = view.state === "bottom" ? GREEN : WHITE;   // доод цэгт хүрэхэд нум ногоон
      ctx.stroke();
    }
    ctx.beginPath();
    ctx.arc(j[0], j[1], 9 * k, 0, Math.PI * 2);
    ctx.lineWidth = 2 * k;
    ctx.strokeStyle = WHITE;
    ctx.stroke();
    const label = `${Math.round(view.angle)}°`;
    ctx.font = `800 ${Math.round(24 * k)}px Roboto, system-ui, sans-serif`;
    ctx.lineWidth = 4 * k;
    ctx.strokeStyle = "rgba(0,0,0,.6)";
    ctx.strokeText(label, j[0] + 14 * k, j[1] - 14 * k);
    ctx.fillStyle = WHITE;
    ctx.fillText(label, j[0] + 14 * k, j[1] - 14 * k);
  }
}

/** Бэлтгэл шатанд кадрын хүрээ: улбар шар = бэлэн биш, ногоон = бэлэн (байрлалаа барьж байна). */
export function drawFrameBorder(ctx, rect, ready, k = 1) {
  rect = rect.box || rect;
  ctx.lineWidth = 5 * k;
  ctx.strokeStyle = ready ? GREEN : ORANGE;
  const o = ctx.lineWidth / 2;
  ctx.strokeRect(rect.x + o, rect.y + o, rect.w - 2 * o, rect.h - 2 * o);
}

/** Эхлэх байрлалаа барих явцын цагираг (1 секунд). */
export function drawReadyRing(ctx, rect, progress, k = 1) {
  rect = rect.box || rect;
  const cx = rect.x + rect.w / 2, cy = rect.y + rect.h * 0.16, r = Math.min(rect.w, rect.h) * 0.06;
  ctx.lineWidth = 3 * k;
  ctx.strokeStyle = GRAY;
  ctx.beginPath();
  ctx.arc(cx, cy, r, 0, Math.PI * 2);
  ctx.stroke();
  ctx.lineWidth = 6 * k;
  ctx.strokeStyle = GREEN;
  ctx.beginPath();
  ctx.arc(cx, cy, r, -Math.PI / 2, -Math.PI / 2 + Math.PI * 2 * Math.max(0, Math.min(1, progress)));
  ctx.stroke();
}
