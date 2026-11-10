// Дүрс (SVG): дасгалын зураас хүн ба товчлуурын тэмдгүүд. Өнгө нь currentColor тул горим солигдоход дагана.

const stroke = 'fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round"';

export const FIGURES = {
  squat: `<svg class="figure" viewBox="0 0 220 150" ${stroke} stroke-width="5" aria-hidden="true">
    <line x1="40" y1="143" x2="180" y2="143" stroke-width="1.5" opacity=".45"/>
    <circle cx="131" cy="20" r="7" fill="currentColor" stroke="none"/>
    <polyline points="162,45 113,39 90,81 125,103 97,137"/>
    <polyline points="91,141 97,137 119,141"/>
  </svg>`,
  pushup: `<svg class="figure" viewBox="0 0 220 150" ${stroke} stroke-width="5" aria-hidden="true">
    <line x1="24" y1="126" x2="196" y2="126" stroke-width="1.5" opacity=".45"/>
    <circle cx="172" cy="70" r="7" fill="currentColor" stroke="none"/>
    <polyline points="36,121 152,82 152,122"/>
  </svg>`,
};

const icon = (body, width = 2) =>
  `<svg viewBox="0 0 24 24" ${stroke} stroke-width="${width}" aria-hidden="true">${body}</svg>`;

export const ICONS = {
  start: icon('<polygon points="8,5 19,12 8,19" fill="currentColor" stroke="none"/>'),
  settings: icon('<line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="21" y2="12"/>' +
                 '<line x1="3" y1="18" x2="21" y2="18"/><circle cx="15" cy="6" r="2.4" fill="currentColor"/>' +
                 '<circle cx="8" cy="12" r="2.4" fill="currentColor"/><circle cx="13" cy="18" r="2.4" fill="currentColor"/>'),
  history: icon('<line x1="5" y1="20" x2="5" y2="12"/><line x1="12" y1="20" x2="12" y2="5"/>' +
                '<line x1="19" y1="20" x2="19" y2="9"/>', 2.6),
  help: icon('<circle cx="12" cy="12" r="9"/><path d="M9.6 9.4a2.5 2.5 0 1 1 3.6 2.3c-.8.4-1.2 1-1.2 1.9"/>' +
             '<circle cx="12" cy="17" r=".6" fill="currentColor"/>'),
  back: icon('<polyline points="14,6 8,12 14,18"/>', 2.4),
  next: icon('<line x1="5" y1="12" x2="19" y2="12"/><polyline points="13,6 19,12 13,18"/>', 2.4),
  close: icon('<line x1="6" y1="6" x2="18" y2="18"/><line x1="18" y1="6" x2="6" y2="18"/>', 2.4),
  flip: icon('<path d="M4 9a8 8 0 0 1 14-3l2 2"/><polyline points="20,3 20,8 15,8"/>' +
             '<path d="M20 15a8 8 0 0 1-14 3l-2-2"/><polyline points="4,21 4,16 9,16"/>'),
  sound: icon('<polygon points="4,9 8,9 13,5 13,19 8,15 4,15" fill="currentColor" stroke="none"/>' +
              '<path d="M16.5 8.5a5 5 0 0 1 0 7"/><path d="M19 6a8.5 8.5 0 0 1 0 12"/>'),
  mute: icon('<polygon points="4,9 8,9 13,5 13,19 8,15 4,15" fill="currentColor" stroke="none"/>' +
             '<line x1="16.5" y1="9" x2="21.5" y2="15"/><line x1="21.5" y1="9" x2="16.5" y2="15"/>'),
  sun: icon('<circle cx="12" cy="12" r="4" fill="currentColor" stroke="none"/>' +
            [0, 45, 90, 135, 180, 225, 270, 315].map((a) =>
              `<line x1="12" y1="2.5" x2="12" y2="5" transform="rotate(${a} 12 12)"/>`).join(""), 2.2),
  moon: icon('<path d="M19.5 14.5A8 8 0 0 1 9.5 4.5a8 8 0 1 0 10 10z" fill="currentColor" stroke="none"/>'),
};
