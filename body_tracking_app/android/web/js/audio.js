// Дуут дохио: компьютерын хувилбарын audio.py-тай ижил аялгуу (давтамж Гц, секунд). WebAudio-оор шууд үүсгэнэ.

const TONES = {
  tick: [[880, 0.09]],
  go: [[1320, 0.28]],
  depth: [[1568, 0.05]],
  good: [[660, 0.08], [0, 0.02], [990, 0.14]],
  bad: [[330, 0.12], [0, 0.04], [247, 0.20]],
  set_done: [[523, 0.12], [659, 0.12], [784, 0.26]],
  done: [[523, 0.12], [659, 0.12], [784, 0.12], [1047, 0.40]],
};
// Нэг кадрт олон үйл явдал давхцвал хамгийн чухлыг нь л тоглуулна
const PRIORITY = ["done", "set_done", "bad", "good", "go", "tick", "depth"];

let ctx = null;

/** Хэрэглэгч дэлгэцэнд хүрэх үед дуудна (хөтөч дууг зөвхөн тэгж нээдэг). */
export function unlock() {
  try {
    ctx = ctx || new (window.AudioContext || window.webkitAudioContext)();
    if (ctx.state === "suspended") ctx.resume();
  } catch { ctx = null; }
}

export function play(name, volume = 0.35) {
  if (!ctx || !TONES[name]) return;
  let at = ctx.currentTime + 0.01;
  for (const [freq, dur] of TONES[name]) {
    if (freq > 0) {
      const gain = ctx.createGain();
      const fade = Math.min(dur / 4, 0.01);
      gain.gain.setValueAtTime(0, at);
      gain.gain.linearRampToValueAtTime(volume, at + fade);
      gain.gain.setValueAtTime(volume, at + dur - fade);
      gain.gain.linearRampToValueAtTime(0, at + dur);
      gain.connect(ctx.destination);
      for (const [mult, level] of [[1, 0.8], [2, 0.2]]) {
        const osc = ctx.createOscillator();
        const g = ctx.createGain();
        osc.type = "sine";
        osc.frequency.value = freq * mult;
        g.gain.value = level;
        osc.connect(g).connect(gain);
        osc.start(at);
        osc.stop(at + dur);
      }
    }
    at += dur;
  }
}

export function playEvents(events) {
  if (!events || !events.length) return;
  const name = PRIORITY.find((p) => events.includes(p));
  if (name) play(name);
}
