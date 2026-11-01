/**
 * Ornamental corner flora for invitation cards. A single SVG definition drives both the
 * live on-screen card preview and the high-resolution canvas export, so they stay 1:1.
 */
const SVG_NS = 'http://www.w3.org/2000/svg';

export function svgNode(tag, attrs, ...children) {
  const el = document.createElementNS(SVG_NS, tag);
  for (const [k, v] of Object.entries(attrs ?? {})) {
    if (v !== undefined && v !== null) el.setAttribute(k, String(v));
  }
  for (const child of children.flat(Infinity)) {
    if (child) el.append(child);
  }
  return el;
}

/** Creates an ornate corner floral/botanical SVG ornament for top-right and bottom-left card borders. */
export function createCornerFloraSvg(motif, position) {
  const cls = `inv-corner-decor inv-corner-${position}`;
  const paths = [];

  if (motif === 'botanical_vines' || motif === 'olive_branch' || motif === 'coastal_palm') {
    // Flowing botanical vine with leaves and berries
    paths.push(
      svgNode('path', {
        d: 'M112 8 C84 12, 52 28, 28 58 C16 74, 10 92, 8 112',
        fill: 'none',
        stroke: 'currentColor',
        'stroke-width': '2',
      }),
      svgNode('path', {
        d: 'M86 16 C70 4, 54 12, 62 28 C72 26, 82 22, 86 16 Z',
        fill: 'currentColor',
        opacity: '0.85',
      }),
      svgNode('path', {
        d: 'M58 34 C40 20, 26 30, 38 48 C48 44, 54 40, 58 34 Z',
        fill: 'currentColor',
        opacity: '0.75',
      }),
      svgNode('path', {
        d: 'M34 62 C16 50, 8 64, 20 80 C28 74, 32 68, 34 62 Z',
        fill: 'currentColor',
        opacity: '0.85',
      }),
      svgNode('path', {
        d: 'M72 28 C88 38, 78 54, 62 42 C66 36, 70 32, 72 28 Z',
        fill: 'currentColor',
        opacity: '0.65',
      }),
      svgNode('path', {
        d: 'M46 52 C62 64, 50 80, 36 66 C40 60, 44 56, 46 52 Z',
        fill: 'currentColor',
        opacity: '0.65',
      }),
      svgNode('circle', { cx: '96', cy: '24', r: '4', fill: 'currentColor' }),
      svgNode('circle', { cx: '24', cy: '96', r: '4', fill: 'currentColor' }),
    );
  } else if (motif === 'art_deco_fan') {
    // Geometric Art-Deco sunburst & lotus petals
    paths.push(
      svgNode('path', { d: 'M116 4 L4 116 M116 4 L32 4 M116 4 L4 32', stroke: 'currentColor', 'stroke-width': '2', fill: 'none' }),
      svgNode('path', { d: 'M116 4 C76 18, 48 46, 34 86', stroke: 'currentColor', 'stroke-width': '1.8', fill: 'none' }),
      svgNode('path', { d: 'M116 28 C84 36, 60 60, 52 92', stroke: 'currentColor', 'stroke-width': '1.5', fill: 'none' }),
      svgNode('circle', { cx: '88', cy: '32', r: '5', fill: 'currentColor' }),
      svgNode('circle', { cx: '64', cy: '56', r: '4', fill: 'currentColor' }),
      svgNode('circle', { cx: '40', cy: '80', r: '3.5', fill: 'currentColor' }),
    );
  } else {
    // Lush multi-petal floral rosette with trailing tendrils & leaves (royal_lotus, rose_blossom, sunburst_marigold, lavender_sprig)
    paths.push(
      // Trailing stems along top and right edge
      svgNode('path', {
        d: 'M98 22 C66 12, 34 14, 6 26',
        fill: 'none',
        stroke: 'currentColor',
        'stroke-width': '1.8',
      }),
      svgNode('path', {
        d: 'M98 22 C108 54, 106 86, 94 114',
        fill: 'none',
        stroke: 'currentColor',
        'stroke-width': '1.8',
      }),
      // Leaves along top stem
      svgNode('path', {
        d: 'M62 16 C48 4, 34 10, 44 22 C52 22, 58 19, 62 16 Z',
        fill: 'currentColor',
        opacity: '0.75',
      }),
      svgNode('path', {
        d: 'M34 20 C20 10, 10 18, 20 28 C26 26, 30 24, 34 20 Z',
        fill: 'currentColor',
        opacity: '0.65',
      }),
      // Leaves along vertical stem
      svgNode('path', {
        d: 'M104 58 C116 72, 110 86, 98 76 C98 68, 101 62, 104 58 Z',
        fill: 'currentColor',
        opacity: '0.75',
      }),
      svgNode('path', {
        d: 'M100 86 C110 100, 102 110, 92 100 C94 94, 96 90, 100 86 Z',
        fill: 'currentColor',
        opacity: '0.65',
      }),
      // Corner 8-petal flower blossom at (88, 32)
      svgNode('circle', { cx: '88', cy: '18', r: '8', fill: 'currentColor', opacity: '0.85' }),
      svgNode('circle', { cx: '88', cy: '46', r: '8', fill: 'currentColor', opacity: '0.85' }),
      svgNode('circle', { cx: '74', cy: '32', r: '8', fill: 'currentColor', opacity: '0.85' }),
      svgNode('circle', { cx: '102', cy: '32', r: '8', fill: 'currentColor', opacity: '0.85' }),
      svgNode('circle', { cx: '78', cy: '22', r: '7', fill: 'currentColor', opacity: '0.65' }),
      svgNode('circle', { cx: '98', cy: '22', r: '7', fill: 'currentColor', opacity: '0.65' }),
      svgNode('circle', { cx: '78', cy: '42', r: '7', fill: 'currentColor', opacity: '0.65' }),
      svgNode('circle', { cx: '98', cy: '42', r: '7', fill: 'currentColor', opacity: '0.65' }),
      svgNode('circle', { cx: '88', cy: '32', r: '5.5', fill: 'var(--inv-inner, #1e2545)' }),
      svgNode('circle', { cx: '88', cy: '32', r: '3', fill: 'currentColor' }),
    );
  }

  return svgNode(
    'svg',
    {
      class: cls,
      viewBox: '0 0 120 120',
      'aria-hidden': 'true',
      focusable: 'false',
    },
    paths,
  );
}

/** Draws matching motif-specific corner ornaments onto the 1200x1600 HTML5 Canvas at Top-Right and Bottom-Left. */
export function drawCanvasCornerFlora(ctx, W, H, theme) {
  const svgEl = createCornerFloraSvg(theme.motif, 'top-right');
  svgEl.setAttribute('xmlns', SVG_NS);
  svgEl.setAttribute('width', '180');
  svgEl.setAttribute('height', '180');
  const rawSvg = new XMLSerializer()
    .serializeToString(svgEl)
    .replace(/currentColor/g, theme.border)
    .replace(/var\(--inv-inner,\s*#[0-9a-fA-F]+\)/g, theme.innerBg);

  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => {
      // Top-Right inside inner panel (inner panel is x: 70..W-70, y: 70..H-70)
      ctx.save();
      ctx.globalAlpha = 0.9;
      ctx.drawImage(img, W - 70 - 195, 70 + 15, 180, 180);
      // Bottom-Left rotated 180deg
      ctx.translate(70 + 15 + 180, H - 70 - 15);
      ctx.rotate(Math.PI);
      ctx.drawImage(img, 0, 0, 180, 180);
      ctx.restore();
      resolve();
    };
    img.onerror = () => reject(new Error('Could not render the invitation decorations. Please try downloading again.'));
    img.src = `data:image/svg+xml;charset=utf-8,${encodeURIComponent(rawSvg)}`;
  });
}
