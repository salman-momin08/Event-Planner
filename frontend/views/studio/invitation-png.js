/** High-resolution (1200x1600) PNG export of an invitation card via HTML5 Canvas, mirroring the live preview. */
import { EVENT_TYPE, formatDate } from '../../dom.js';
import { drawCanvasCornerFlora } from './motifs.js';
import { INVITATION_THEMES } from './themes.js';
/** Draws a high-resolution (1200x1600) invitation card onto an HTML5 Canvas that matches the Live Card Preview 1:1. */
export async function createInvitationPng(ev, inv) {
  const theme = INVITATION_THEMES[inv.themeStyle] ?? INVITATION_THEMES.royal_indigo;
  const layout = inv.layoutStyle || 'classic_crest';
  const isLeftAligned = layout === 'modern_editorial' || layout === 'minimal_split';
  const fontFamily = layout === 'modern_editorial' ? "system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif" : 'Georgia, serif';

  const canvas = document.createElement('canvas');
  const W = 1200;
  const H = 1600;
  canvas.width = W;
  canvas.height = H;
  const ctx = canvas.getContext('2d');
  if (!ctx) throw new Error('Your browser could not create the invitation image. Please try again in a regular browser tab.');

  // Outer card background
  ctx.fillStyle = theme.bg;
  ctx.fillRect(0, 0, W, H);

  // Inner card panel & layout-specific border architecture
  const ix = 70;
  const iy = 70;
  const iw = W - 140;
  const ih = H - 140;

  ctx.save();
  if (layout === 'garden_arch') {
    ctx.beginPath();
    const archR = iw / 2;
    ctx.arc(W / 2, iy + archR, archR, Math.PI, 0, false);
    ctx.lineTo(ix + iw, iy + ih);
    ctx.lineTo(ix, iy + ih);
    ctx.closePath();
    ctx.fillStyle = theme.innerBg;
    ctx.fill();
    ctx.clip();
    ctx.strokeStyle = theme.border;
    ctx.lineWidth = 6;
    ctx.stroke();
  } else {
    ctx.fillStyle = theme.innerBg;
    ctx.fillRect(ix, iy, iw, ih);
    ctx.strokeStyle = theme.border;
    if (layout === 'festive_confetti') {
      ctx.lineWidth = 6;
      ctx.setLineDash([18, 12]);
      ctx.strokeRect(ix + 3, iy + 3, iw - 6, ih - 6);
      ctx.setLineDash([]);
      ctx.strokeStyle = theme.accent;
      ctx.globalAlpha = 0.25;
      ctx.lineWidth = 14;
      ctx.strokeRect(ix + 14, iy + 14, iw - 28, ih - 28);
      ctx.globalAlpha = 1;
    } else if (layout === 'royal_mandala') {
      ctx.lineWidth = 6;
      ctx.strokeRect(ix + 3, iy + 3, iw - 6, ih - 6);
      ctx.lineWidth = 3;
      ctx.strokeRect(ix + 24, iy + 24, iw - 48, ih - 48);
    } else if (layout === 'classic_crest') {
      ctx.lineWidth = 5;
      ctx.strokeRect(ix + 2, iy + 2, iw - 4, ih - 4);
      ctx.lineWidth = 2;
      ctx.strokeRect(ix + 20, iy + 20, iw - 40, ih - 40);
    } else if (layout === 'modern_editorial') {
      ctx.lineWidth = 2.5;
      ctx.strokeRect(ix + 1, iy + 1, iw - 2, ih - 2);
    } else if (layout === 'minimal_split') {
      ctx.lineWidth = 4;
      ctx.strokeRect(ix + 2, iy + 2, iw - 4, ih - 4);
      ctx.fillStyle = theme.border;
      ctx.fillRect(ix, iy, 24, ih);
    }
  }

  // Draw exact SVG corner flora in Top-Right and Bottom-Left
  await drawCanvasCornerFlora(ctx, W, H, theme);

  const textX = isLeftAligned ? ix + 110 : W / 2;
  const maxTextW = isLeftAligned ? iw - 220 : iw - 240;
  ctx.textAlign = isLeftAligned ? 'left' : 'center';

  // 1. Host line
  ctx.fillStyle = theme.accent;
  ctx.font = `700 26px ${fontFamily}`;
  ctx.fillText((inv.hostLine || 'HOSTED WITH LOVE').toUpperCase(), textX, 310);

  // 2. Occasion subtitle
  ctx.fillStyle = theme.muted;
  ctx.font = `italic 30px ${fontFamily}`;
  let curY = wrapCanvasText(ctx, inv.subheadline || EVENT_TYPE[ev.type], textX, 380, maxTextW, 44);

  // 3. Main Headline
  ctx.fillStyle = theme.text;
  ctx.font = `bold 64px ${fontFamily}`;
  curY = wrapCanvasText(ctx, inv.headline || ev.title, textX, curY + 75, maxTextW, 76);

  // 4. Divider line
  ctx.strokeStyle = theme.border;
  ctx.lineWidth = 3;
  ctx.beginPath();
  if (isLeftAligned) {
    ctx.moveTo(textX, curY + 45);
    ctx.lineTo(textX + 160, curY + 45);
  } else {
    ctx.moveTo(W / 2 - 80, curY + 45);
    ctx.lineTo(W / 2 + 80, curY + 45);
  }
  ctx.stroke();

  // 5. Invitation Body Message (preserves line breaks)
  ctx.fillStyle = theme.text;
  ctx.font = `32px ${fontFamily}`;
  curY = wrapCanvasParagraphs(ctx, inv.bodyText || '', textX, curY + 115, maxTextW, 50);

  // 6. Date & Location Meta Box (matches .inv-meta top & bottom border)
  const metaTop = Math.max(curY + 60, 1020);
  ctx.strokeStyle = theme.border;
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.moveTo(ix + 110, metaTop);
  ctx.lineTo(ix + iw - 110, metaTop);
  ctx.stroke();

  ctx.fillStyle = theme.accent;
  ctx.font = `bold 40px ${fontFamily}`;
  ctx.fillText(formatDate(ev.eventDate), textX, metaTop + 65);

  ctx.fillStyle = theme.text;
  ctx.font = `33px ${fontFamily}`;
  ctx.fillText(ev.location || 'Location to be announced', textX, metaTop + 120);

  const metaBottom = metaTop + 155;
  ctx.beginPath();
  ctx.moveTo(ix + 110, metaBottom);
  ctx.lineTo(ix + iw - 110, metaBottom);
  ctx.stroke();

  // 7. Dress Code Footer
  if (inv.dressCode) {
    ctx.fillStyle = theme.muted;
    ctx.font = `27px ${fontFamily}`;
    ctx.fillText(`Dress code: ${inv.dressCode}`, textX, metaBottom + 65);
  }
  ctx.restore();

  return new Promise((resolve, reject) => {
    canvas.toBlob((blob) => {
      if (blob) resolve(blob);
      else reject(new Error('Could not export the invitation as a PNG. Please try downloading again.'));
    }, 'image/png');
  });
}

export function wrapCanvasText(ctx, text, x, startY, maxWidth, lineHeight) {
  const words = String(text).split(/\s+/).filter(Boolean);
  let line = '';
  let y = startY;
  for (const word of words) {
    const test = line ? `${line} ${word}` : word;
    if (ctx.measureText(test).width > maxWidth && line) {
      ctx.fillText(line, x, y);
      line = word;
      y += lineHeight;
    } else {
      line = test;
    }
  }
  if (line) ctx.fillText(line, x, y);
  return y;
}

export function wrapCanvasParagraphs(ctx, text, x, startY, maxWidth, lineHeight) {
  const paragraphs = String(text).split(/\n/);
  let y = startY;
  for (let i = 0; i < paragraphs.length; i++) {
    const p = paragraphs[i].trim();
    if (!p) {
      y += lineHeight * 0.6;
      continue;
    }
    y = wrapCanvasText(ctx, p, x, y, maxWidth, lineHeight);
    if (i < paragraphs.length - 1) y += lineHeight;
  }
  return y;
}
