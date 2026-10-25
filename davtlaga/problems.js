/*
 * Давтлага — бодлого үүсгэгч.
 *
 * Бодлого бүрийг загвараас (template) санамсаргүй тоогоор үүсгэнэ. Хариуг томьёогоор
 * тооцдог тул үргэлж зөв. Талбар бүр түгээмэл алдааны хариунуудыг урьдчилан тооцоолж
 * хадгалдаг тул "буруу" гэхээс гадна ямар алдаа хийснийг тайлбарлана.
 *
 * Хөтөч дээр window.Davtlaga, Node дээр require('./problems.js').
 */
(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.Davtlaga = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';

  // ---------- Санамсаргүй тоо (seed-тэй тул ижил seed → ижил бодлого) ----------

  function makeRng(seed) {
    let a = seed >>> 0;
    function next() {
      a = (a + 0x6d2b79f5) >>> 0;
      let t = a;
      t = Math.imul(t ^ (t >>> 15), t | 1);
      t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    }
    return {
      next,
      int: (lo, hi) => lo + Math.floor(next() * (hi - lo + 1)),
      pick: (arr) => arr[Math.floor(next() * arr.length)],
      shuffle(arr) {
        const out = arr.slice();
        for (let i = out.length - 1; i > 0; i--) {
          const j = Math.floor(next() * (i + 1));
          [out[i], out[j]] = [out[j], out[i]];
        }
        return out;
      },
    };
  }

  // ---------- IPv4 туслах функцүүд (bitwise биш арифметикаар, тэмдгийн алдаагүй) ----------

  const MAX32 = 4294967295;
  const ORD = ['1-р', '2-р', '3-р', '4-р'];
  const LETTERS = ['А', 'Б', 'В', 'Г', 'Д', 'Е'];

  function fromOctets(o) {
    return ((o[0] * 256 + o[1]) * 256 + o[2]) * 256 + o[3];
  }
  function octets(n) {
    return [Math.floor(n / 16777216) % 256, Math.floor(n / 65536) % 256, Math.floor(n / 256) % 256, n % 256];
  }
  function intToIp(n) {
    return octets(n).join('.');
  }
  function maskInt(p) {
    return MAX32 - (2 ** (32 - p) - 1);
  }
  function networkOf(ip, p) {
    const size = 2 ** (32 - p);
    return Math.floor(ip / size) * size;
  }
  function broadcastOf(ip, p) {
    return networkOf(ip, p) + 2 ** (32 - p) - 1;
  }
  // Prefix аль октет дээр тасрах вэ (0-ээс эхэлсэн индекс): /24–/31 → 3, /16–/23 → 2, /8–/15 → 1
  function cutIndex(p) {
    return Math.min(3, Math.floor(p / 8));
  }
  // Тасарсан октет дээрх блокийн хэмжээ
  function octetBlock(p) {
    return 2 ** (8 * (cutIndex(p) + 1) - p);
  }
  function setOctet(n, i, v) {
    const o = octets(n);
    o[i] = v;
    return fromOctets(o);
  }
  function setTrailing(n, i, v) {
    const o = octets(n);
    for (let k = i + 1; k < 4; k++) o[k] = v;
    return fromOctets(o);
  }
  function copyTrailing(n, i, src) {
    const o = octets(n);
    const s = octets(src);
    for (let k = i + 1; k < 4; k++) o[k] = s[k];
    return fromOctets(o);
  }

  function parseIp(raw) {
    const s = String(raw ?? '').replace(/\s+/g, '').replace(/\/\d{1,2}$/, '');
    if (!/^\d{1,3}(\.\d{1,3}){3}$/.test(s)) return null;
    const o = s.split('.').map(Number);
    if (o.some((x) => x > 255)) return null;
    return fromOctets(o);
  }
  function parseNumber(raw) {
    const s = String(raw ?? '').replace(/\s+/g, '').replace(',', '.');
    const m = s.match(/^[-+]?(\d+\.?\d*|\.\d+)(e[-+]?\d+)?/i);
    return m ? Number(m[0]) : null;
  }
  function fmt(x) {
    return String(Math.round(x * 10000) / 10000);
  }

  // ---------- Хариулт авах талбарууд ----------

  const EMPTY = { status: 'empty', msg: 'Хариугаа бичнэ үү.' };
  const WRONG = 'Буруу байна. Бодолтыг нээж алхам бүрээ шалгаарай.';
  const eqExact = (a, b) => a === b;
  const isIpInt = (v) => Number.isInteger(v) && v >= 0 && v <= MAX32;

  function uniqueMistakes(expected, list, same) {
    const out = [];
    for (const m of list) {
      if (m.value === null || m.value === undefined) continue;
      if (same(m.value, expected) || out.some((o) => same(o.value, m.value))) continue;
      out.push(m);
    }
    return out;
  }
  function verdict(v, expected, mistakes, same) {
    if (same(v, expected)) return { status: 'ok' };
    const hit = mistakes.find((m) => same(m.value, v));
    return { status: 'wrong', msg: hit ? hit.msg : WRONG };
  }

  function ipField(key, label, expected, mistakes) {
    const ms = uniqueMistakes(expected, mistakes.filter((m) => isIpInt(m.value)), eqExact);
    return {
      key,
      label,
      kind: 'ip',
      expected: intToIp(expected),
      mistakes: ms.map((m) => ({ value: intToIp(m.value), msg: m.msg })),
      check(raw) {
        if (!String(raw ?? '').trim()) return EMPTY;
        const v = parseIp(raw);
        if (v === null) return { status: 'format', msg: 'IP хаягийг a.b.c.d хэлбэрээр бичнэ (жишээ нь 192.168.1.10).' };
        return verdict(v, expected, ms, eqExact);
      },
    };
  }

  function maskField(key, label, p) {
    const f = ipField(key, label, maskInt(p), maskMistakes(p));
    const base = f.check;
    f.kind = 'mask';
    f.check = (raw) =>
      /^\s*\/?\s*\d{1,2}\s*$/.test(String(raw ?? ''))
        ? { status: 'format', msg: 'Маскийг 255.255.255.0 хэлбэрээр бичнэ (prefix биш).' }
        : base(raw);
    return f;
  }

  function intField(key, label, expected, mistakes, unit) {
    const ms = uniqueMistakes(expected, mistakes.filter((m) => Number.isFinite(m.value)), eqExact);
    return {
      key,
      label,
      kind: 'number',
      unit,
      expected: String(expected),
      mistakes: ms.map((m) => ({ value: String(m.value), msg: m.msg })),
      check(raw) {
        if (!String(raw ?? '').trim()) return EMPTY;
        const v = parseNumber(raw);
        if (v === null) return { status: 'format', msg: 'Тоо бичнэ үү.' };
        return verdict(v, expected, ms, eqExact);
      },
    };
  }

  function numField(key, label, expected, mistakes, unit) {
    const same = (a, b) => Math.abs(a - b) <= Math.max(1e-9, Math.abs(b) * 0.01);
    const ms = uniqueMistakes(expected, mistakes.filter((m) => Number.isFinite(m.value)), same);
    return {
      key,
      label,
      kind: 'number',
      unit,
      expected: fmt(expected),
      mistakes: ms.map((m) => ({ value: String(m.value), msg: m.msg })),
      check(raw) {
        if (!String(raw ?? '').trim()) return EMPTY;
        const v = parseNumber(raw);
        if (v === null) return { status: 'format', msg: 'Тоо бичнэ үү (жишээ нь 4.8).' };
        return verdict(v, expected, ms, same);
      },
    };
  }

  function prefixField(key, label, p, mistakes) {
    const ms = uniqueMistakes(p, mistakes.filter((m) => Number.isInteger(m.value) && m.value >= 0 && m.value <= 32), eqExact);
    return {
      key,
      label,
      kind: 'prefix',
      expected: '/' + p,
      mistakes: ms.map((m) => ({ value: '/' + m.value, msg: m.msg })),
      check(raw) {
        const s = String(raw ?? '').trim();
        if (!s) return EMPTY;
        const m = s.match(/^\/?\s*(\d{1,2})$/);
        if (!m || Number(m[1]) > 32) return { status: 'format', msg: 'Prefix-ийг /23 эсвэл 23 гэж бичнэ.' };
        return verdict(Number(m[1]), p, ms, eqExact);
      },
    };
  }

  function choiceField(key, label, options, answer, msgs) {
    return {
      key,
      label,
      kind: 'choice',
      options,
      answer,
      expected: options.find((o) => o.value === answer).label,
      mistakes: options.filter((o) => o.value !== answer).map((o) => ({ value: o.value, msg: msgs[o.value] || WRONG })),
      check(raw) {
        if (!raw) return { status: 'empty', msg: 'Нэг хариуг сонгоно уу.' };
        if (raw === answer) return { status: 'ok' };
        return { status: 'wrong', msg: msgs[raw] || WRONG };
      },
    };
  }

  // ---------- Subnet: алдааны жагсаалтууд ----------

  function subnetCore(ip, p) {
    const T = 2 ** (32 - p);
    const na = networkOf(ip, p);
    return { T, na, ba: na + T - 1, idx: cutIndex(p), B: octetBlock(p), mask: maskInt(p), h: 32 - p };
  }

  function blockMsg(p) {
    const idx = cutIndex(p);
    return `Блокийн хэмжээг шалга: /${p}-д ${ORD[idx]} октет дээрх блок = 2^(${8 * (idx + 1)} − ${p}) = ${octetBlock(p)}.`;
  }

  function maskMistakes(p) {
    const idx = cutIndex(p);
    const B = octetBlock(p);
    const list = [];
    if (p > 1) list.push({ value: maskInt(p - 1), msg: `Энэ бол /${p - 1}-ийн маск. /${p}-д эхний ${p} бит 1 байна.` });
    if (p < 32) list.push({ value: maskInt(p + 1), msg: `Энэ бол /${p + 1}-ийн маск. /${p}-д эхний ${p} бит 1 байна.` });
    for (const q of [8, 16, 24]) {
      if (q !== p) list.push({ value: maskInt(q), msg: `Энэ бол /${q}-ийн маск. Энд prefix /${p} байна.` });
    }
    list.push({ value: MAX32 - maskInt(p), msg: 'Энэ бол урвуу (wildcard) маск. Subnet mask-т сүлжээний битүүд 1 байна.' });
    if (B < 256) {
      list.push({ value: setOctet(maskInt(p), idx, B), msg: `${ORD[idx]} октетын утга нь блок биш: 256 − ${B} = ${256 - B}.` });
      list.push({ value: setOctet(maskInt(p), idx, 255 - B), msg: `256 − блок гэж бодно: 256 − ${B} = ${256 - B} (255 − ${B} биш).` });
    }
    return list;
  }

  function naMistakes(ip, p) {
    const c = subnetCore(ip, p);
    const list = [
      { value: ip, msg: 'Та хостын хаягийг өөрчлөлгүй бичсэн байна. N.A нь блокийн эхний хаяг (host битүүд 0).' },
      { value: c.ba, msg: 'Энэ бол broadcast хаяг (блокийн сүүлийн хаяг). N.A нь блокийн эхний хаяг.' },
      { value: c.na + 1, msg: 'Энэ бол эхний хостын хаяг. N.A үүнээс 1-ээр бага.' },
      { value: c.na + c.T, msg: `Энэ бол дараагийн сүлжээ. ${ORD[c.idx]} октетыг ${c.B}-д хуваагаад бүхэл хэсгийг нь доош нь авна.` },
    ];
    if (c.idx < 3) {
      list.push({ value: copyTrailing(c.na, c.idx, ip), msg: `N.A дээр ${ORD[c.idx]} октетоос хойших октетууд 0 болно.` });
    }
    for (const q of [p - 1, p + 1]) if (q >= 1 && q <= 31) list.push({ value: networkOf(ip, q), msg: blockMsg(p) });
    return list;
  }

  function baMistakes(ip, p) {
    const c = subnetCore(ip, p);
    const list = [
      { value: c.na + c.T, msg: 'Блокийг бүтнээр нь нэмсэн байна. Энэ бол дараагийн сүлжээний хаяг. Broadcast = дараагийн сүлжээ − 1.' },
      { value: c.na, msg: 'Энэ бол сүлжээний хаяг (блокийн эхлэл). Broadcast нь блокийн сүүлийн хаяг.' },
      { value: c.ba - 1, msg: 'Энэ бол сүүлийн хостын хаяг. Broadcast үүнээс 1-ээр их.' },
    ];
    if (c.idx < 3) {
      const msg = `Broadcast дээр ${ORD[c.idx]} октетоос хойших октетууд 255 байна.`;
      list.push({ value: setTrailing(c.ba, c.idx, 0), msg });
      list.push({ value: copyTrailing(c.ba, c.idx, ip), msg });
      const s = octets(c.na)[c.idx];
      if (s + c.B <= 255) {
        list.push({
          value: setTrailing(setOctet(c.na, c.idx, s + c.B), c.idx, 255),
          msg: `${ORD[c.idx]} октетэд блокийг бүтнээр нэмсэн байна: ${s} + ${c.B} − 1 = ${s + c.B - 1} байх ёстой.`,
        });
      }
    }
    for (const q of [p - 1, p + 1]) if (q >= 1 && q <= 31) list.push({ value: broadcastOf(ip, q), msg: blockMsg(p) });
    return list;
  }

  function firstMistakes(ip, p) {
    const c = subnetCore(ip, p);
    const list = [
      { value: c.na, msg: 'Сүлжээний хаягийг хостод олгодоггүй. Эхний хост = N.A + 1.' },
      { value: ip, msg: 'Энэ бол өгөгдсөн хост. Эхний хост = N.A + 1.' },
      { value: c.ba, msg: 'Энэ бол broadcast хаяг. Эхний хост = N.A + 1.' },
    ];
    if (c.idx < 3) {
      list.push({ value: c.na + 256 ** (3 - c.idx), msg: `1-ийг ${ORD[c.idx]} октетэд биш, 4-р октетэд нэмнэ.` });
    }
    for (const q of [p - 1, p + 1]) if (q >= 1 && q <= 30) list.push({ value: networkOf(ip, q) + 1, msg: blockMsg(p) });
    return list;
  }

  function lastMistakes(ip, p) {
    const c = subnetCore(ip, p);
    const list = [
      { value: c.ba, msg: 'Broadcast хаягийг хостод олгодоггүй. Сүүлийн хост = Br.A − 1.' },
      { value: ip, msg: 'Энэ бол өгөгдсөн хост. Сүүлийн хост = Br.A − 1.' },
      { value: c.na + c.T - 2 + 2, msg: 'Энэ бол дараагийн сүлжээний хаяг. Сүүлийн хост = Br.A − 1.' },
    ];
    for (const q of [p - 1, p + 1]) if (q >= 1 && q <= 30) list.push({ value: broadcastOf(ip, q) - 1, msg: blockMsg(p) });
    return list;
  }

  function usableMistakes(p) {
    const h = 32 - p;
    const B = octetBlock(p);
    const list = [
      { value: 2 ** h, msg: `N.A ба Br.A-г хасаагүй байна: 2^${h} − 2.` },
      { value: 2 ** h - 1, msg: `Хоёр хаяг хасна (N.A ба Br.A): 2^${h} − 2.` },
      { value: 2 ** (h - 1) - 2, msg: `Host битийн тоог шалга: 32 − ${p} = ${h}.` },
      { value: 2 ** (h + 1) - 2, msg: `Host битийн тоог шалга: 32 − ${p} = ${h}.` },
    ];
    if (cutIndex(p) < 3) list.push({ value: B - 2, msg: `${B} нь зөвхөн нэг октет дээрх блок. Host ${h} бит тул 2^${h} − 2.` });
    return list;
  }

  function subnetSteps(ip, p) {
    const c = subnetCore(ip, p);
    const k = c.idx;
    const x = octets(ip)[k];
    const q = Math.floor(x / c.B);
    const s = q * c.B;
    const range = k === 3 ? '/24–/31' : k === 2 ? '/16–/23' : '/8–/15';
    const before = k > 0 ? 'өмнөх октетууд 255, ' : '';
    const after0 = k < 3 ? ', хойших октетууд 0' : '';
    const after255 = k < 3 ? ', хойших октетууд 255' : '';
    return [
      `Prefix /${p}: сүлжээ ${p} бит, host 32 − ${p} = ${c.h} бит. Нийт хаяг 2^${c.h} = ${c.T}.`,
      `/${p} нь ${ORD[k]} октет дээр тасарна (${range}). Блок = 2^(${8 * (k + 1)} − ${p}) = ${c.B}.`,
      `Mask: ${before}${ORD[k]} октет = 256 − ${c.B} = ${256 - c.B}${after0} → ${intToIp(c.mask)}.`,
      `N.A: ${x} ÷ ${c.B} = ${q} (үлдэгдэл ${x - s}) → ${q} × ${c.B} = ${s}${after0} → ${intToIp(c.na)}.`,
      `Br.A: ${s} + ${c.B} − 1 = ${s + c.B - 1}${after255} → ${intToIp(c.ba)}.`,
      `Эхний хост = N.A + 1 → ${intToIp(c.na + 1)}. Сүүлийн хост = Br.A − 1 → ${intToIp(c.ba - 1)}.`,
      `Usable = 2^${c.h} − 2 = ${c.T - 2}.`,
    ];
  }

  function randomHost(level, rng, p) {
    for (;;) {
      let o;
      if (level === 1) {
        o = [192, 168, rng.int(0, 254), rng.int(1, 254)];
      } else if (level === 2) {
        const first = rng.pick([10, 172, 192, 200]);
        const second = first === 172 ? rng.int(16, 31) : first === 192 ? 168 : rng.int(0, 255);
        o = [first, second, rng.int(0, 255), rng.int(0, 255)];
      } else {
        let first = rng.int(1, 223);
        if (first === 127) first = 126;
        o = [first, rng.int(0, 255), rng.int(0, 255), rng.int(0, 255)];
      }
      const ip = fromOctets(o);
      if (ip !== networkOf(ip, p) && ip !== broadcastOf(ip, p)) return ip;
    }
  }

  function levelPrefix(level, rng) {
    if (level === 1) return rng.int(25, 30);
    if (level === 2) return rng.int(17, 23);
    return rng.int(9, 30);
  }

  // ---------- Загвар 1: Хаягаас mask, N.A, Br.A ----------

  function genSubnet(level, rng) {
    const p = levelPrefix(level, rng);
    const ip = randomHost(level, rng, p);
    const c = subnetCore(ip, p);
    const ipStr = `${intToIp(ip)}/${p}`;
    return {
      title: `Хост ${ipStr}`,
      prompt: [`Хостын хаяг ${ipStr}. Subnet mask, сүлжээний хаяг (N.A), broadcast (Br.A), эхний ба сүүлийн хаяглаж болох хаяг, usable хостын тоог ол.`],
      hint: `/${p} аль октет дээр тасрахыг эхлээд ол. 4-р октет бол блок = 2^(32 − p), 3-р октет бол 2^(24 − p), 2-р октет бол 2^(16 − p).`,
      fields: [
        maskField('mask', 'Subnet mask', p),
        ipField('na', 'Сүлжээний хаяг (N.A)', c.na, naMistakes(ip, p)),
        ipField('ba', 'Broadcast (Br.A)', c.ba, baMistakes(ip, p)),
        ipField('first', 'Эхний хаяглаж болох хаяг', c.na + 1, firstMistakes(ip, p)),
        ipField('last', 'Сүүлийн хаяглаж болох хаяг', c.ba - 1, lastMistakes(ip, p)),
        intField('usable', 'Usable хостын тоо', c.T - 2, usableMistakes(p)),
      ],
      steps: subnetSteps(ip, p),
      visual: {
        type: 'bits',
        rows: [
          { label: 'Хост', ip: intToIp(ip), prefix: p },
          { label: 'N.A', ip: intToIp(c.na), prefix: p },
          { label: 'Br.A', ip: intToIp(c.ba), prefix: p },
        ],
      },
    };
  }

  // ---------- Загвар 2: N хосттой сүлжээ (шалгалтын "Бодлого 1") ----------

  function genHosts(level, rng) {
    const ranges = { 1: [10, 250], 2: [260, 4000], 3: [4100, 60000] };
    const [lo, hi] = ranges[level];
    let N = rng.int(lo, hi);
    if (rng.next() < 0.6) N = Math.min(hi, Math.max(lo, Math.round(N / 10) * 10));
    let h = 1;
    while (2 ** h - 2 < N) h++;
    const p = 32 - h;
    const T = 2 ** h;
    const k = cutIndex(p);
    const B = octetBlock(p);
    const exampleFirst = rng.int(192, 223);
    const exampleNet = networkOf(fromOctets([exampleFirst, exampleFirst === 192 ? 168 : rng.int(0, 255), rng.int(0, 255), rng.int(0, 255)]), p);
    const isValidNet = (v) => v !== null && Math.floor(v / 16777216) >= 192 && Math.floor(v / 16777216) <= 223 && networkOf(v, p) === v;

    const network = {
      key: 'network',
      label: 'Сүлжээний хаяг (өөрөө сонгоно)',
      kind: 'ip',
      expected: `C ангиллын, /${p} блокийн эхлэл бүр зөв (жишээ нь ${intToIp(exampleNet)})`,
      mistakes: [],
      check(raw) {
        if (!String(raw ?? '').trim()) return EMPTY;
        const v = parseIp(raw);
        if (v === null) return { status: 'format', msg: 'IP хаягийг a.b.c.d хэлбэрээр бичнэ (жишээ нь 192.168.0.0).' };
        const first = Math.floor(v / 16777216);
        if (first < 192 || first > 223) return { status: 'wrong', msg: 'C ангиллын хаягийн эхний октет 192–223 хооронд байна.' };
        if (networkOf(v, p) !== v) {
          return { status: 'wrong', msg: `${intToIp(v)} нь /${p} блокийн эхлэл биш. Энэ хаягийн блокийн эхлэл ${intToIp(networkOf(v, p))} байна.` };
        }
        return { status: 'ok' };
      },
    };

    const broadcast = {
      key: 'broadcast',
      label: 'Broadcast хаяг',
      kind: 'ip',
      expected: `Сонгосон N.A + ${T - 1} (жишээ нь ${intToIp(exampleNet + T - 1)})`,
      expectedFor(values) {
        const net = parseIp(values.network);
        return isValidNet(net) ? intToIp(net + T - 1) : null;
      },
      mistakes: [],
      check(raw, values) {
        if (!String(raw ?? '').trim()) return EMPTY;
        const v = parseIp(raw);
        if (v === null) return { status: 'format', msg: 'IP хаягийг a.b.c.d хэлбэрээр бичнэ.' };
        const net = parseIp(values && values.network);
        if (!isValidNet(net)) return { status: 'wrong', msg: 'Broadcast нь сүлжээний хаягаас хамаарна. Эхлээд сүлжээний хаягаа зөв бич.' };
        const ms = uniqueMistakes(net + T - 1, baMistakes(net, p).filter((m) => isIpInt(m.value)), eqExact);
        return verdict(v, net + T - 1, ms, eqExact);
      },
    };

    const exampleRule =
      B === 256 ? `${ORD[k]} октет 0` : `${ORD[k]} октет ${B}-ийн үржвэр${k < 3 ? ', хойших октетууд 0' : ''}`;

    return {
      title: `${N} хосттой сүлжээ`,
      prompt: [
        `${N} хосттой сүлжээг C ангиллын (эхний октет 192–223) дурын хаягаар зохион байгуулна. Хаягаа өөрөө сонгоод доорх утгуудыг ол.`,
      ],
      hint: '2^h − 2 ≥ хостын тоо байх хамгийн бага h-ийг ол. Prefix = 32 − h.',
      fields: [
        maskField('mask', 'Subnet mask', p),
        network,
        broadcast,
        intField('total', 'Нийт хаягийн тоо', T, [
          { value: T - 2, msg: `Энэ бол usable хостын тоо. Нийт хаяг N.A ба Br.A-г оруулаад 2^${h} = ${T}.` },
          { value: N, msg: `Энэ бол өгөгдсөн хостын тоо. Нийт хаяг = 2^${h}.` },
          { value: T / 2, msg: `2^${h - 1} − 2 = ${T / 2 - 2} нь ${N}-д хүрэхгүй. h = ${h}.` },
          { value: T * 2, msg: `Хэт их байна. 2^${h} − 2 = ${T - 2} аль хэдийн ${N}-д хүрнэ.` },
        ]),
        prefixField('prefix', 'CIDR prefix-ийн урт', p, [
          { value: h, msg: `Энэ бол host битийн тоо. Prefix = 32 − ${h} = ${p}.` },
          { value: p + 1, msg: `/${p + 1}-д usable 2^${h - 1} − 2 = ${T / 2 - 2} нь ${N}-д хүрэхгүй.` },
          { value: p - 1, msg: `/${p - 1} хүрнэ, гэхдээ хамгийн бага блок нь /${p} (2^${h} − 2 = ${T - 2} ≥ ${N}).` },
        ]),
      ],
      steps: [
        `2^h − 2 ≥ ${N} байх хамгийн бага h-ийг ол: 2^${h - 1} − 2 = ${T / 2 - 2} (хүрэхгүй), 2^${h} − 2 = ${T - 2} (хүрнэ) → h = ${h}.`,
        `Prefix = 32 − ${h} = /${p}. Mask → ${intToIp(maskInt(p))}.`,
        `N.A: эхний октет 192–223 хаяг сонгоно. /${p}-д ${exampleRule}. Жишээ нь ${intToIp(exampleNet)}.`,
        `Br.A = N.A + 2^${h} − 1 = N.A + ${T - 1} → жишээ нь ${intToIp(exampleNet + T - 1)}.`,
        `Нийт хаяг = 2^${h} = ${T} (usable ${T - 2}).`,
      ],
      visual: {
        type: 'bits',
        rows: [
          { label: 'N.A', ip: intToIp(exampleNet), prefix: p },
          { label: 'Br.A', ip: intToIp(exampleNet + T - 1), prefix: p },
        ],
      },
    };
  }

  // ---------- Загвар 3: Нэг сүлжээнд үү? ----------

  function genSame(level, rng) {
    const p = levelPrefix(level, rng);
    const A = randomHost(level, rng, p);
    const c = subnetCore(A, p);
    const same = rng.next() < 0.5;
    let B;
    if (same) {
      do B = c.na + 1 + rng.int(0, c.T - 3);
      while (B === A);
    } else {
      let dir = rng.next() < 0.5 ? 1 : -1;
      if (c.na < c.T) dir = 1;
      if (c.na + 2 * c.T - 1 > MAX32) dir = -1;
      B = c.na + dir * c.T + 1 + rng.int(0, c.T - 3);
    }
    const naA = intToIp(networkOf(A, p));
    const naB = intToIp(networkOf(B, p));
    const answer = same ? 'yes' : 'no';
    const k = cutIndex(p);
    const stepFor = (name, ip) => {
      const x = octets(ip)[k];
      const q = Math.floor(x / c.B);
      return `${name} ${intToIp(ip)}: ${x} ÷ ${c.B} = ${q} → ${q * c.B} → N.A ${intToIp(networkOf(ip, p))}.`;
    };
    return {
      title: `${intToIp(A)} ба ${intToIp(B)} /${p}`,
      prompt: [`Хост A ${intToIp(A)}/${p}, хост B ${intToIp(B)}/${p}. Хоёр хостын сүлжээний хаягийг олж, нэг сүлжээнд байгаа эсэхийг тодорхойл.`],
      hint: 'Хоёр хостын N.A-г ижил prefix-ээр тус тусад нь ол. N.A ижил бол нэг сүлжээ.',
      fields: [
        ipField('naA', 'A-ийн сүлжээний хаяг', networkOf(A, p), naMistakes(A, p)),
        ipField('naB', 'B-ийн сүлжээний хаяг', networkOf(B, p), naMistakes(B, p)),
        choiceField('same', 'Нэг сүлжээнд байна уу?', [
          { value: 'yes', label: 'Тийм' },
          { value: 'no', label: 'Үгүй' },
        ], answer, {
          yes: `N.A нь ялгаатай: ${naA} ≠ ${naB}. Нэг сүлжээнд биш.`,
          no: `Хоёулаа ${naA} сүлжээнд багтана.`,
        }),
      ],
      steps: [
        `/${p} нь ${ORD[k]} октет дээр тасарна. Блок = ${c.B}.`,
        stepFor('A', A),
        stepFor('B', B),
        same ? `N.A ижил (${naA}) → нэг сүлжээ.` : `N.A ялгаатай (${naA} ≠ ${naB}) → өөр сүлжээ.`,
      ],
      visual: {
        type: 'bits',
        rows: [
          { label: 'A', ip: intToIp(A), prefix: p },
          { label: 'B', ip: intToIp(B), prefix: p },
        ],
      },
    };
  }

  // ---------- Загвар 4: TCP Seq / Ack ----------

  function genTcp(level, rng) {
    const isn = () => (level === 1 ? 0 : level === 2 ? rng.int(1000, 99999) : rng.int(100000000, 3999999999));
    const cIsn = isn();
    const sIsn = isn();
    const L1 = rng.int(2, 60) * 10 + rng.pick([0, 5]);
    const L2 = rng.int(10, 146) * 10;
    const pk = [];
    let cNext = cIsn;
    let sNext = sIsn;
    function add(from, flags, len) {
      const syn = flags.includes('SYN');
      const fin = flags.includes('FIN');
      const seq = from === 'C' ? cNext : sNext;
      const ack = flags.includes('ACK') ? (from === 'C' ? sNext : cNext) : null;
      pk.push({ n: pk.length + 1, from, flags, seq, ack, len, syn, fin });
      const adv = len + (syn || fin ? 1 : 0);
      if (from === 'C') cNext += adv;
      else sNext += adv;
    }
    add('C', 'SYN', 0);
    add('S', 'SYN, ACK', 0);
    add('C', 'ACK', 0);
    add('C', 'PSH, ACK', L1);
    if (level === 1) {
      add('S', 'ACK', 0);
    } else if (level === 2) {
      add('S', 'PSH, ACK', L2);
      add('C', 'ACK', 0);
    } else {
      add('S', 'ACK', 0);
      add('S', 'PSH, ACK', L2);
      add('C', 'ACK', 0);
      add('C', 'FIN, ACK', 0);
      add('S', 'FIN, ACK', 0);
      add('C', 'ACK', 0);
    }

    const who = (side) => (side === 'C' ? 'Client' : 'Server');
    const plus1 = (q) => (q.syn ? ' + 1 (SYN)' : q.fin ? ' + 1 (FIN)' : '');
    const lastFrom = (side, i) => {
      for (let j = i - 1; j >= 0; j--) if (pk[j].from === side) return pk[j];
      return null;
    };
    const desc = (q) => `№${q.n} (${q.flags}, Seq=${q.seq}, Len=${q.len})`;

    // Хоосон нүдний нэр дэвшигчид
    let cands = [];
    pk.forEach((q, i) => {
      if (i >= 2) cands.push({ i, col: 'seq' });
      if (i >= 1) cands.push({ i, col: 'ack' });
    });
    const blanks = [];
    if (level === 3 && rng.next() < 0.6) {
      const data = pk.map((q, i) => i).filter((i) => pk[i].len > 0);
      const di = rng.pick(data);
      const dep = pk.findIndex((q, j) => j > di && q.from !== pk[di].from);
      blanks.push({ i: di, col: 'len' });
      cands = cands.filter((b) => !(b.i === dep && b.col === 'ack'));
    }
    const want = level === 1 ? 3 : level === 2 ? 4 : 5;
    for (const b of rng.shuffle(cands)) {
      if (blanks.length >= want) break;
      blanks.push(b);
    }
    blanks.sort((a, b) => a.i - b.i || (a.col > b.col ? 1 : -1));

    const fields = [];
    const steps = [
      'Дүрэм: Seq = өөрийн өмнөх Seq + Len (+1 SYN/FIN). Ack = нөгөө талын сүүлийн Seq + Len (+1 SYN/FIN).',
    ];
    blanks.forEach((b, bi) => {
      const letter = LETTERS[bi];
      const q = pk[b.i];
      b.key = 'b' + bi;
      b.letter = letter;
      const label = `(${letter}) №${q.n} ${b.col === 'seq' ? 'Seq' : b.col === 'ack' ? 'Ack' : 'Len'}`;
      if (b.col === 'seq') {
        const prev = lastFrom(q.from, b.i);
        const mistakes = [];
        if (prev.syn || prev.fin) mistakes.push({ value: prev.seq + prev.len, msg: `Өмнөх пакет ${prev.syn ? 'SYN' : 'FIN'} байсан. SYN/FIN 1 байт эзэлдэг тул +1 нэмнэ.` });
        if (prev.len > 0) mistakes.push({ value: prev.seq, msg: `Өмнөх пакетын Len=${prev.len}-ийг нэмээгүй байна.` });
        if (q.ack !== null) mistakes.push({ value: q.ack, msg: 'Seq ба Ack-ийг андуурсан байна. Seq нь илгээгчийн өөрийн тоолуур.' });
        if (!prev.syn && !prev.fin) mistakes.push({ value: q.seq + 1, msg: '+1-ийг зөвхөн SYN эсвэл FIN-ий дараа нэмнэ.' });
        fields.push(intField(b.key, label, q.seq, mistakes));
        steps.push(`(${letter}) №${q.n} Seq: ${who(q.from)}-ийн өмнөх пакет ${desc(prev)} → ${prev.seq} + ${prev.len}${plus1(prev)} = ${q.seq}.`);
      } else if (b.col === 'ack') {
        const o = lastFrom(q.from === 'C' ? 'S' : 'C', b.i);
        const mistakes = [];
        if (o.syn || o.fin) mistakes.push({ value: o.seq + o.len, msg: `${who(o.from)}-ийн сүүлийн пакет ${o.syn ? 'SYN' : 'FIN'} байсан. +1 нэмнэ.` });
        if (o.len > 0) mistakes.push({ value: o.seq, msg: `${who(o.from)}-ийн Len=${o.len}-ийг нэмээгүй байна.` });
        mistakes.push({ value: q.seq, msg: 'Ack нь нөгөө талын дугаараар тооцогдоно, өөрийн Seq биш.' });
        if (!o.syn && !o.fin) mistakes.push({ value: q.ack + 1, msg: '+1-ийг зөвхөн SYN эсвэл FIN-ий дараа нэмнэ.' });
        fields.push(intField(b.key, label, q.ack, mistakes));
        steps.push(`(${letter}) №${q.n} Ack: ${who(o.from)}-ийн сүүлийн пакет ${desc(o)} → ${o.seq} + ${o.len}${plus1(o)} = ${q.ack}.`);
      } else {
        const dep = pk.find((r, j) => j > b.i && r.from !== q.from);
        fields.push(intField(b.key, label, q.len, [
          { value: q.len + 1, msg: 'Ack − Seq-ийг яг тооцно. Энэ пакет SYN/FIN биш тул +1 нэмэхгүй.' },
          { value: q.len - 1, msg: 'Ack − Seq-ийг яг тооцно. 1 хасахгүй.' },
          { value: dep.ack, msg: 'Энэ бол Ack дугаар. Илгээсэн байт = Ack − Seq.' },
        ], 'байт'));
        steps.push(`(${letter}) №${q.n} Len: №${dep.n}-ийн Ack=${dep.ack} нь ${who(q.from)}-ийн дараагийн байт → ${dep.ack} − ${q.seq} = ${q.len}.`);
      }
    });

    const blankAt = (i, col) => blanks.find((b) => b.i === i && b.col === col);
    const cell = (i, col, value) => {
      const b = blankAt(i, col);
      return b ? { blank: b.key, label: b.letter } : value === null ? '–' : String(value);
    };
    const cport = rng.int(49152, 65535);
    const sport = rng.pick([80, 443]);
    const cip = `192.168.${rng.int(0, 20)}.${rng.int(2, 250)}`;
    const sip = `203.0.113.${rng.int(1, 254)}`;
    return {
      title: `TCP ${cport} → ${sport}`,
      prompt: [
        `Client ${cip}:${cport} нь Server ${sip}:${sport}-тэй TCP холболт тогтоож өгөгдөл солилцов${level === 3 ? ', дараа нь холболтыг хаав' : ''}. Wireshark-ийн хүснэгтийн хоосон нүднүүдийг бөглө.`,
        level === 1 ? 'Дугаарууд relative (0-ээс эхэлсэн).' : 'Дугаарууд raw (бодит) утгатай.',
      ],
      hint: 'Хоосон нүд хэн илгээсэн пакетынх вэ? Seq бол ижил чиглэлийн өмнөх пакетыг, Ack бол эсрэг чиглэлийн сүүлийн пакетыг хар.',
      table: {
        head: ['№', 'Чиглэл', 'Flag', 'Seq', 'Ack', 'Len'],
        rows: pk.map((q, i) => [
          String(q.n),
          q.from === 'C' ? `${cport} → ${sport}` : `${sport} → ${cport}`,
          q.flags,
          cell(i, 'seq', q.seq),
          cell(i, 'ack', q.ack),
          cell(i, 'len', q.len),
        ]),
      },
      fields,
      steps,
    };
  }

  // ---------- Загвар 5: IP fragmentation ----------

  function genFrag(level, rng) {
    const mtu = level === 1 ? 1500 : level === 2 ? rng.pick([1500, 1000]) : rng.pick([576, 1000, 1006, 1492]);
    const maxP = Math.floor((mtu - 20) / 8) * 8;
    const nWanted = level === 1 ? rng.int(2, 3) : rng.int(2, 4);
    const lo = (nWanted - 1) * maxP + 21;
    const hi = nWanted * maxP + 20;
    let T = rng.int(lo, hi);
    const rounded = Math.round(T / 10) * 10;
    if (rounded >= lo && rounded <= hi) T = rounded;
    const P = T - 20;
    const n = Math.ceil(P / maxP);
    const frags = [];
    for (let k = 0; k < n; k++) {
      const payload = k < n - 1 ? maxP : P - maxP * (n - 1);
      frags.push({ k: k + 1, payload, total: payload + 20, offset: (k * maxP) / 8, mf: k < n - 1 ? 1 : 0 });
    }
    const notMultiple = mtu - 20 !== maxP;
    const fields = [
      intField('count', 'Фрагментийн тоо', n, [
        { value: Math.ceil(T / maxP), msg: `Payload = ${T} − 20 = ${P}-ийг хуваана (total length биш).` },
        { value: Math.ceil(P / (mtu - 20)), msg: `MTU − 20 = ${mtu - 20} нь 8-д хуваагдахгүй тул ${maxP}-д хуваана.` },
        { value: Math.ceil(T / mtu), msg: `Payload-ыг (${P}) фрагментийн max payload-д (${maxP}) хуваана.` },
      ]),
    ];
    const cols = level === 1 ? ['offset', 'mf'] : ['payload', 'total', 'offset', 'mf'];
    const colLabels = { payload: 'Payload', total: 'Total length', offset: 'Offset', mf: 'MF' };
    for (const f of frags) {
      const last = f.k === n;
      const mk = (col) => `f${f.k}_${col}`;
      const lab = (col) => `${f.k}-р фрагмент ${colLabels[col]}`;
      const grid = (col) => ({ row: f.k, col });
      if (cols.includes('payload')) {
        const m = [{ value: f.total, msg: 'Энэ бол total length. Payload-д 20 байт header ороогүй.' }];
        if (!last) {
          if (notMultiple) m.push({ value: mtu - 20, msg: `MTU − 20 = ${mtu - 20} нь 8-д хуваагдахгүй. 8-ын үржвэр болгож доош нь бууруулна: ${maxP}.` });
          m.push({ value: mtu, msg: `Payload = MTU − 20 (header-ийг хасна), 8-ын үржвэр болгоно → ${maxP}.` });
        } else {
          m.push({ value: T - maxP * (n - 1), msg: `Үлдэгдлийг payload-аас (${P}) тооцно: ${P} − ${maxP * (n - 1)}.` });
        }
        fields.push(Object.assign(intField(mk('payload'), lab('payload'), f.payload, m), { grid: grid('payload') }));
      }
      if (cols.includes('total')) {
        const m = [{ value: f.payload, msg: 'Total length = payload + 20 байт header.' }];
        if (!last && notMultiple) m.push({ value: mtu, msg: `MTU − 20 нь 8-д хуваагдахгүй тул total = ${maxP} + 20 = ${maxP + 20}.` });
        if (last) m.push({ value: T - maxP * (n - 1), msg: `Сүүлийн payload = ${P} − ${maxP * (n - 1)} = ${f.payload}, total = payload + 20.` });
        fields.push(Object.assign(intField(mk('total'), lab('total'), f.total, m), { grid: grid('total') }));
      }
      {
        const before = (f.k - 1) * maxP;
        const m = [];
        if (f.k === 1) {
          m.push({ value: 1, msg: 'Эхний фрагментийн offset үргэлж 0.' });
        } else {
          m.push({ value: before, msg: `Offset 8 байтын нэгжээр: ${before} ÷ 8 = ${f.offset}.` });
          if (((f.k - 1) * mtu) % 8 === 0) m.push({ value: ((f.k - 1) * mtu) / 8, msg: 'Offset-д зөвхөн payload-ыг тооцно (header-гүй).' });
          if (notMultiple && ((f.k - 1) * (mtu - 20)) % 8 === 0) m.push({ value: ((f.k - 1) * (mtu - 20)) / 8, msg: `8-ын үржвэр болгосон payload-ыг (${maxP}) хэрэглэнэ.` });
          m.push({ value: (f.k * maxP) / 8, msg: 'Энэ бол дараагийн фрагментийн offset. Зөвхөн өмнөх фрагментуудын payload-ыг тооцно.' });
        }
        fields.push(Object.assign(intField(mk('offset'), lab('offset'), f.offset, m), { grid: grid('offset') }));
      }
      fields.push(
        Object.assign(
          intField(mk('mf'), lab('mf'), f.mf, [
            { value: 1 - f.mf, msg: last ? 'Сүүлийн фрагмент MF=0.' : 'Сүүлийнхээс бусад бүх фрагмент MF=1 (цаана нь фрагмент бий).' },
          ]),
          { grid: grid('mf') },
        ),
      );
    }
    return {
      title: `Total ${T}, MTU ${mtu}`,
      prompt: [`IPv4 datagram: total length ${T} байт (header 20 байт), MTU ${mtu}, DF=0. Фрагментийн тоо болон фрагмент бүрийн ${level === 1 ? 'offset, MF' : 'payload, total length, offset, MF'}-ийг ол.`],
      hint: 'Payload = total − 20. Фрагментийн max payload = MTU − 20-ийг 8-ын үржвэр болгож доош нь. Offset = өмнөх payload ÷ 8.',
      grid: { rows: frags.map((f) => `${f.k}-р`), cols: cols.map((c) => ({ key: c, label: colLabels[c] })) },
      fields,
      steps: [
        `Payload нийт = ${T} − 20 = ${P} байт.`,
        `Max payload = ${mtu} − 20 = ${mtu - 20}${notMultiple ? ` → 8-ын үржвэр болгож доош нь: ${maxP}` : ' (8-ын үржвэр)'}.`,
        `Фрагментийн тоо = ⌈${P} ÷ ${maxP}⌉ = ${n}.`,
        ...frags.map((f) => `${f.k}-р: payload ${f.payload}, total ${f.payload} + 20 = ${f.total}, offset ${(f.k - 1) * maxP} ÷ 8 = ${f.offset}, MF=${f.mf}.`),
      ],
    };
  }

  // ---------- Загвар 6: Longest prefix match ----------

  function genLpm(level, rng) {
    const dest = fromOctets([10, rng.int(0, 255), rng.int(0, 255), rng.int(1, 254)]);
    let prefixes;
    if (level === 1) prefixes = [8, 16, 24];
    else if (level === 2) prefixes = [8, rng.int(12, 15), rng.int(17, 22)];
    else prefixes = [rng.int(8, 11), rng.int(14, 19), rng.int(21, 26)];
    const sibling = (p) => {
      const size = 2 ** (32 - p);
      const net = networkOf(dest, p);
      return (net / size) % 2 === 0 ? net + size : net - size;
    };
    let routes;
    const noMatch = level === 1 && rng.next() < 0.15;
    if (noMatch) {
      const other = setOctet(dest, 0, 172);
      routes = prefixes.map((p) => ({ net: networkOf(other, p), p }));
    } else {
      routes = prefixes.map((p) => ({ net: networkOf(dest, p), p }));
      const longest = prefixes[2];
      if (rng.next() < 0.45) {
        routes[2] = { net: sibling(longest), p: longest };
      } else if (level >= 2) {
        const q = Math.min(30, longest + rng.int(1, 4));
        routes.push({ net: sibling(q), p: q });
      }
    }
    routes.forEach((r) => (r.matches = networkOf(dest, r.p) === r.net));
    const ordered = rng.shuffle(routes);
    ordered.push({ net: 0, p: 0, matches: true, isDefault: true });
    const names = ['A', 'B', 'C', 'D', 'E', 'F'];
    ordered.forEach((r, i) => (r.iface = names[i]));
    const best = ordered.filter((r) => r.matches).sort((a, b) => b.p - a.p)[0];
    const cidr = (r) => (r.isDefault ? 'default (0.0.0.0/0)' : `${intToIp(r.net)}/${r.p}`);
    const msgs = {};
    for (const r of ordered) {
      if (r === best) continue;
      if (r.isDefault) msgs[r.iface] = 'Default (0.0.0.0/0) нь өөр ямар ч маршрут таарахгүй үед л ашиглагдана.';
      else if (r.matches) msgs[r.iface] = `${cidr(r)} таарна, гэхдээ ${cidr(best)} илүү урт (/${best.p}) prefix-ээр таарна.`;
      else msgs[r.iface] = `${cidr(r)} таарахгүй: ${intToIp(dest)}-ийн эхний ${r.p} бит → ${intToIp(networkOf(dest, r.p))}/${r.p}.`;
    }
    const steps = ordered.map((r) => {
      if (r.isDefault) return `${r.iface}: default бүх хаягтай таарна (/0).`;
      const mine = intToIp(networkOf(dest, r.p));
      return `${r.iface}: ${intToIp(dest)}-ийн эхний ${r.p} бит → ${mine}/${r.p} ${r.matches ? '= ' + cidr(r) + ' → таарна' : '≠ ' + cidr(r) + ' → таарахгүй'}.`;
    });
    steps.push(best.isDefault ? 'Ямар ч маршрут таарахгүй тул default → ' + best.iface + '.' : `Таарсан маршрутаас хамгийн урт нь /${best.p} → interface ${best.iface}.`);
    return {
      title: `Destination ${intToIp(dest)}`,
      prompt: [`Router-ийн forwarding table доор байна. Destination ${intToIp(dest)} хаягтай пакет аль interface-ээр гарах вэ?`],
      hint: 'Маршрут бүрт destination-ийн эхний p битийг тооцож маршрутын сүлжээтэй харьцуул. Таарсан маршрутаас хамгийн урт prefix-тэйг сонго.',
      table: { head: ['Сүлжээ', 'Interface'], rows: ordered.map((r) => [cidr(r), r.iface]) },
      fields: [
        choiceField(
          'iface',
          'Гарах interface',
          ordered.map((r) => ({ value: r.iface, label: r.iface })),
          best.iface,
          msgs,
        ),
      ],
      steps,
      visual: best.isDefault
        ? null
        : {
            type: 'bits',
            rows: [
              { label: 'Dest', ip: intToIp(dest), prefix: best.p },
              { label: best.iface, ip: intToIp(best.net), prefix: best.p },
            ],
          },
    };
  }

  // ---------- Загвар 7: Delay ----------

  function genDelay(level, rng) {
    const S = 2e8;
    const L = rng.pick([500, 800, 1000, 1200, 1500, 2000]);
    const R1 = rng.pick([1, 2, 4, 5, 8, 10, 20, 100]);
    const dt = (L * 8) / (R1 * 1e6) * 1000;
    const dtMistakes = (v) => [
      { value: v / 8, msg: 'Байтыг бит болгоогүй байна (× 8).' },
      { value: v / 1000, msg: 'Хариу секундээр байна. ms = с × 1000.' },
      { value: v * 1000, msg: 'Нэгжээ шалга: Mbps = 10^6 bps, хариуг ms-ээр.' },
    ];
    const fields = [numField('dt', 'd_trans', dt, dtMistakes(dt), 'ms')];
    const steps = [`L = ${L} байт × 8 = ${L * 8} бит. d_trans = ${L * 8} ÷ (${R1} × 10^6) с = ${fmt(dt)} ms.`];
    const prompt = [`${L} байт пакетыг ${R1} Mbps холбоосоор илгээнэ.`];
    if (level === 1) {
      prompt.push('Transmission delay-г ms-ээр ол.');
    } else if (level === 2) {
      const d = rng.pick([200, 400, 500, 1000, 1500, 2000, 3000, 5000]);
      const dp = (d * 1000) / S * 1000;
      prompt.push(`Холбоосын урт ${d} км, дохионы тархах хурд s = 2×10^8 м/с. Processing ба queueing delay 0. d_trans, d_prop болон нийт delay-г ms-ээр ол.`);
      fields.push(
        numField('dp', 'd_prop', dp, [
          { value: dp / 1000, msg: 'Нэгжээ шалга: км → м (× 1000), с → ms (× 1000).' },
          { value: (dp * 2) / 3, msg: 's = 2×10^8 м/с гэж өгөгдсөн (3×10^8 биш).' },
          { value: dp * 1000, msg: 'Нэгжээ шалга: хариуг ms-ээр бичнэ.' },
        ], 'ms'),
        numField('total', 'Нийт delay', dt + dp, [
          { value: dt, msg: 'd_prop-ийг нэмээгүй байна.' },
          { value: dp, msg: 'd_trans-ийг нэмээгүй байна.' },
          { value: dt / 8 + dp, msg: 'd_trans дээр байтыг бит болгоогүй байна (× 8).' },
        ], 'ms'),
      );
      steps.push(
        `d = ${d} км = ${d * 1000} м. d_prop = ${d * 1000} ÷ (2×10^8) с = ${fmt(dp)} ms.`,
        `Нийт = d_trans + d_prop = ${fmt(dt)} + ${fmt(dp)} = ${fmt(dt + dp)} ms.`,
      );
    } else {
      let R2 = rng.pick([1, 2, 4, 5, 8, 10, 20, 100]);
      if (R2 === R1) R2 = R1 === 100 ? 10 : 100;
      const d1 = rng.pick([100, 200, 500, 1000]);
      const d2 = rng.pick([300, 600, 1500, 2000]);
      const dt2 = (L * 8) / (R2 * 1e6) * 1000;
      const dp = ((d1 + d2) * 1000) / S * 1000;
      const total = dt + dt2 + dp;
      prompt[0] = `${L} байт пакет Host A → Router → Host B замаар явна. 1-р холбоос ${R1} Mbps, ${d1} км; 2-р холбоос ${R2} Mbps, ${d2} км. s = 2×10^8 м/с.`;
      prompt.push('Router store-and-forward хийнэ. Processing ба queueing delay 0. Холбоос тус бүрийн d_trans болон нийт end-to-end delay-г ms-ээр ол.');
      fields[0].label = '1-р холбоосын d_trans';
      fields.push(
        numField('dt2', '2-р холбоосын d_trans', dt2, dtMistakes(dt2), 'ms'),
        numField('total', 'Нийт end-to-end delay', total, [
          { value: dt + dp, msg: 'Router store-and-forward: 2-р холбоос дээр пакет дахин дамжина, d_trans2-ийг нэмнэ.' },
          { value: dt + dt2, msg: 'd_prop-ийг нэмээгүй байна.' },
          { value: dt + dt2 + dp / 1000, msg: 'd_prop-ийн нэгжийг шалга: км → м.' },
          { value: 2 * dt + dp, msg: 'Хоёр холбоосын хурд ялгаатай: d_trans2 = L ÷ R2.' },
        ], 'ms'),
      );
      steps[0] = `L = ${L} × 8 = ${L * 8} бит. d_trans1 = ${L * 8} ÷ (${R1} × 10^6) с = ${fmt(dt)} ms.`;
      steps.push(
        `d_trans2 = ${L * 8} ÷ (${R2} × 10^6) с = ${fmt(dt2)} ms.`,
        `d_prop = (${d1} + ${d2}) × 1000 м ÷ (2×10^8) = ${fmt(dp)} ms.`,
        `Нийт = ${fmt(dt)} + ${fmt(dt2)} + ${fmt(dp)} = ${fmt(total)} ms.`,
      );
    }
    return {
      title: `${L} байт · ${R1} Mbps`,
      prompt,
      hint: 'd_trans = L ÷ R (L-ийг битээр). d_prop = d ÷ s (d-г метрээр). Хариуг ms-ээр бичнэ.',
      fields,
      steps,
    };
  }

  // ---------- Загвар 8: Throughput ----------

  function genThru(level, rng) {
    const opts = [0.5, 1, 2, 5, 10, 20, 50, 100];
    for (;;) {
      const Rs = rng.pick(opts);
      const Rc = rng.pick(opts);
      const N = level >= 2 ? rng.pick([2, 4, 5, 10]) : 1;
      const R = level >= 2 ? rng.pick([10, 20, 50, 100, 200]) : null;
      const shared = R === null ? null : R / N;
      const cands = [Rs, Rc].concat(shared === null ? [] : [shared]);
      const min = Math.min(...cands);
      if (cands.filter((x) => x === min).length > 1) continue;
      const kbps = level === 3;
      const rcText = kbps ? `${Rc * 1000} kbps` : `${Rc} Mbps`;
      const prompt = [];
      if (level === 1) {
        prompt.push(`Server нь ${Rs} Mbps холбоосоор, client нь ${rcText} холбоосоор сүлжээнд холбогдсон. End-to-end throughput-ийг Mbps-ээр ол.`);
      } else {
        prompt.push(`${N} server нь ${N} client руу зэрэг файл илгээнэ. Server бүр ${Rs} Mbps, client бүр ${rcText} холбоостой. Бүх холболт сүлжээний цөм дэх ${R} Mbps холбоосыг тэнцүү хуваалцана.`);
        prompt.push('Нэг холболтын throughput-ийг Mbps-ээр олж, bottleneck аль холбоос болохыг сонго.');
      }
      const mistakes = [{ value: Math.max(...cands), msg: 'Throughput-ийг хамгийн бага хурд (bottleneck) тодорхойлно: min(...).' }];
      if (R !== null) mistakes.push({ value: R, msg: `${R} Mbps-ийг ${N} холболт хуваалцана: ${R} ÷ ${N}.` });
      if (kbps) mistakes.push({ value: Rc * 1000, msg: 'Хариуг Mbps-ээр бичнэ: kbps ÷ 1000.' });
      const fields = [numField('thr', 'Throughput', min, mistakes, 'Mbps')];
      const steps = [];
      if (kbps) steps.push(`Client: ${Rc * 1000} kbps = ${Rc} Mbps.`);
      if (level === 1) {
        steps.push(`Throughput = min(Rs, Rc) = min(${Rs}, ${Rc}) = ${min} Mbps.`);
      } else {
        const bottleneck = min === Rs ? 'rs' : min === Rc ? 'rc' : 'r';
        const names = { rs: 'Server-ийн холбоос (Rs)', rc: 'Client-ийн холбоос (Rc)', r: 'Хуваалцсан холбоос (R/N)' };
        fields.push(
          choiceField('bn', 'Bottleneck', ['rs', 'rc', 'r'].map((v) => ({ value: v, label: names[v] })), bottleneck, {
            rs: `Rs = ${Rs} Mbps нь хамгийн бага биш.`,
            rc: `Rc = ${Rc} Mbps нь хамгийн бага биш.`,
            r: `R/N = ${R} ÷ ${N} = ${shared} Mbps нь хамгийн бага биш.`,
          }),
        );
        steps.push(`Холболт бүрт ногдох цөмийн хурд = R ÷ N = ${R} ÷ ${N} = ${shared} Mbps.`);
        steps.push(`Throughput = min(${Rs}, ${Rc}, ${shared}) = ${min} Mbps → bottleneck: ${names[bottleneck]}.`);
      }
      return {
        title: level === 1 ? `${Rs} Mbps ба ${rcText}` : `${N} холболт · R = ${R} Mbps`,
        prompt,
        hint: level === 1 ? 'Throughput = min(Rs, Rc).' : 'Throughput = min(Rs, Rc, R/N). Хамгийн бага нь bottleneck.',
        fields,
        steps,
      };
    }
  }

  // ---------- Сэдвүүд ----------

  const TOPICS = [
    {
      id: 'subnet',
      title: 'Хаягаас N.A, Br.A',
      gen: genSubnet,
      tips: [
        'Блок: /24–/31 → 2^(32 − p) (4-р октет), /16–/23 → 2^(24 − p) (3-р октет).',
        'Mask-ийн тасарсан октет = 256 − блок.',
        'N.A = (октет ÷ блок)-ийн бүхэл × блок, хойших октетууд 0.',
        'Br.A = N.A + блок − 1, хойших октетууд 255.',
        'Эхний хост = N.A + 1, сүүлийн хост = Br.A − 1, usable = 2^h − 2.',
      ],
    },
    {
      id: 'hosts',
      title: 'N хосттой сүлжээ',
      gen: genHosts,
      tips: [
        '2^h − 2 ≥ хостын тоо байх хамгийн бага h-ийг ол.',
        'Prefix = 32 − h.',
        'C анги: эхний октет 192–223.',
        'Сонгосон N.A блокийн эхлэл байна: тасарсан октет нь блокийн үржвэр.',
      ],
    },
    {
      id: 'same',
      title: 'Нэг сүлжээнд үү?',
      gen: genSame,
      tips: ['Хоёр хостын N.A-г ижил prefix-ээр ол.', 'N.A ижил бол нэг сүлжээ, ялгаатай бол өөр сүлжээ.'],
    },
    {
      id: 'tcp',
      title: 'TCP Seq / Ack',
      gen: genTcp,
      tips: [
        'Seq = өөрийн өмнөх Seq + Len (+1 SYN/FIN).',
        'Ack = нөгөө талын сүүлийн Seq + Len (+1 SYN/FIN).',
        'Хоосон ACK (Len=0) тоолуурыг өсгөхгүй.',
        'Илгээсэн байт = шинэ Ack − хуучин Ack.',
      ],
    },
    {
      id: 'frag',
      title: 'IP fragmentation',
      gen: genFrag,
      tips: [
        'Payload = total length − 20.',
        'Max payload = MTU − 20-ийг 8-ын үржвэр болгож доош нь.',
        'Offset = өмнөх payload-уудын нийлбэр ÷ 8.',
        'Сүүлийнхээс бусад фрагмент MF=1.',
      ],
    },
    {
      id: 'lpm',
      title: 'Longest prefix match',
      gen: genLpm,
      tips: [
        'Маршрут бүрт destination-ийн эхний p битийг тооцож харьцуул.',
        'Таарсан маршрутаас хамгийн урт prefix-тэйг сонго.',
        'Default (/0) нь бусад нь таарахгүй үед.',
      ],
    },
    {
      id: 'delay',
      title: 'Delay тооцоо',
      gen: genDelay,
      tips: [
        'd_trans = L ÷ R (L-ийг битээр: байт × 8).',
        'd_prop = d ÷ s (d-г метрээр, s = 2×10^8 м/с).',
        'ms = с × 1000.',
        'Router store-and-forward: холбоос бүрт d_trans нэмэгдэнэ.',
      ],
    },
    {
      id: 'thru',
      title: 'Throughput',
      gen: genThru,
      tips: ['Нэг холболт: min(Rs, Rc).', 'N холболт R-ийг хуваалцвал: min(Rs, Rc, R/N).', 'Хамгийн бага нь bottleneck.'],
    },
  ];

  const LEVELS = { 1: 'Хялбар', 2: 'Дунд', 3: 'Хэцүү' };

  function generate(topicId, level, seed) {
    const topic = TOPICS.find((t) => t.id === topicId);
    if (!topic) throw new Error('Unknown topic: ' + topicId);
    const lv = LEVELS[level] ? level : 1;
    const problem = topic.gen(lv, makeRng(seed));
    return Object.assign(problem, { topic: topicId, level: lv, seed });
  }

  return {
    TOPICS: TOPICS.map(({ id, title, tips }) => ({ id, title, tips })),
    LEVELS,
    generate,
    makeRng,
    ip: { fromOctets, octets, intToIp, maskInt, networkOf, broadcastOf, parseIp, cutIndex, octetBlock },
  };
});
