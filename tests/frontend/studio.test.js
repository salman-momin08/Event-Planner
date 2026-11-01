import { describe, it, expect, vi } from 'vitest';
import {
  INVITATION_THEMES,
  INVITATION_LAYOUTS,
  INVITATION_TONES,
  LIGHTING_MOODS,
  OCCASION_DESIGN_PRESETS,
  SPACE_PRESETS,
} from '../../frontend/views/studio/themes.js';
import { compressImageFile, safeFileName, verifyFileMagicBytes } from '../../frontend/views/studio/image-upload.js';
import { createCornerFloraSvg } from '../../frontend/views/studio/motifs.js';
import { createInvitationPng, wrapCanvasParagraphs, wrapCanvasText } from '../../frontend/views/studio/invitation-png.js';
import { renderLiveInvitationCard } from '../../frontend/views/studio/invitation-preview.js';

const HEX = /^#[0-9a-f]{6}$/i;

const relLuminance = (hex) => {
  const c = hex.replace('#', '');
  const [r, g, b] = [0, 2, 4]
    .map((i) => parseInt(c.slice(i, i + 2), 16) / 255)
    .map((v) => (v <= 0.04045 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4));
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
};

const contrast = (a, b) => {
  const [bright, dark] = [relLuminance(a), relLuminance(b)].sort((x, y) => y - x);
  return (bright + 0.05) / (dark + 0.05);
};

describe('studio theme data', () => {
  it('defines complete, well-formed color themes', () => {
    for (const [key, theme] of Object.entries(INVITATION_THEMES)) {
      for (const colorKey of ['bg', 'innerBg', 'border', 'accent', 'text', 'muted']) {
        expect(theme[colorKey], `${key}.${colorKey}`).toMatch(HEX);
      }
      expect(theme.label).toBeTruthy();
      expect(theme.motif).toBeTruthy();
      for (const textKey of ['hostLine', 'subheadline', 'bodyText', 'dressCode']) {
        expect(theme.defaults[textKey], `${key}.defaults.${textKey}`).toBeTruthy();
      }
    }
  });

  it('keeps every invitation theme at WCAG AA contrast or better', () => {
    for (const [key, theme] of Object.entries(INVITATION_THEMES)) {
      expect(contrast(theme.text, theme.bg), `${key} text/bg`).toBeGreaterThanOrEqual(4.5);
      expect(contrast(theme.muted, theme.innerBg), `${key} muted/innerBg`).toBeGreaterThanOrEqual(4.5);
      expect(contrast(theme.accent, theme.innerBg), `${key} accent/innerBg`).toBeGreaterThanOrEqual(4.5);
    }
  });

  it('references only known themes and layouts from occasion presets', () => {
    const layoutKeys = new Set(INVITATION_LAYOUTS.map(([k]) => k));
    expect(OCCASION_DESIGN_PRESETS.length).toBeGreaterThanOrEqual(6);
    for (const [title, themeKey, layoutKey, defaults] of OCCASION_DESIGN_PRESETS) {
      expect(title).toBeTruthy();
      expect(INVITATION_THEMES[themeKey], `preset theme ${themeKey}`).toBeDefined();
      expect(layoutKeys.has(layoutKey), `preset layout ${layoutKey}`).toBe(true);
      expect(defaults.hostLine).toBeTruthy();
      expect(defaults.bodyText).toBeTruthy();
    }
  });

  it('has unique space preset keys and non-empty lighting/tone options', () => {
    const keys = SPACE_PRESETS.map(([k]) => k);
    expect(new Set(keys).size).toBe(keys.length);
    expect(keys).toContain('other');
    expect(LIGHTING_MOODS.length).toBeGreaterThanOrEqual(4);
    expect(INVITATION_TONES.length).toBeGreaterThanOrEqual(3);
  });
});

describe('safeFileName', () => {
  it('strips directory paths and unsafe characters', () => {
    expect(safeFileName('C:\\Users\\me\\My Photo!.jpg')).toBe('My_Photo_.jpg');
    expect(safeFileName('../../etc/passwd.png')).toBe('passwd.png');
    expect(safeFileName('normal-photo_2.webp')).toBe('normal-photo_2.webp');
  });

  it('falls back to a default and caps length at 60 chars', () => {
    expect(safeFileName('')).toBe('photo.jpg');
    expect(safeFileName(null)).toBe('photo.jpg');
    expect(safeFileName(`${'a'.repeat(100)}.jpg`)).toHaveLength(60);
  });
});

describe('verifyFileMagicBytes', () => {
  const fileWith = (bytes) => new File([new Uint8Array(bytes)], 'photo.jpg', { type: 'image/jpeg' });

  it('accepts JPEG, PNG and WebP signatures', async () => {
    await expect(verifyFileMagicBytes(fileWith([0xff, 0xd8, 0xff, 0xe0, 0, 0, 0, 0, 0, 0, 0, 0]))).resolves.toBe(true);
    await expect(verifyFileMagicBytes(fileWith([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a, 0, 0, 0, 0]))).resolves.toBe(true);
    await expect(verifyFileMagicBytes(fileWith([0x52, 0x49, 0x46, 0x46, 0, 0, 0, 0, 0x57, 0x45, 0x42, 0x50]))).resolves.toBe(true);
  });

  it('rejects truncated files and foreign signatures', async () => {
    await expect(verifyFileMagicBytes(fileWith([0xff, 0xd8, 0xff]))).resolves.toBe(false);
    await expect(verifyFileMagicBytes(fileWith([0x47, 0x49, 0x46, 0x38, 0x39, 0x61, 0, 0, 0, 0, 0, 0]))).resolves.toBe(false);
    await expect(verifyFileMagicBytes(fileWith([0x25, 0x50, 0x44, 0x46, 0x2d, 0, 0, 0, 0, 0, 0, 0]))).resolves.toBe(false);
  });
});

describe('compressImageFile validation', () => {
  it('rejects missing, empty, and oversized files before decoding', async () => {
    await expect(compressImageFile(null)).rejects.toThrow('No valid file selected.');
    await expect(compressImageFile(new File([], 'x.jpg', { type: 'image/jpeg' }))).rejects.toThrow('file is empty');
    const big = new File([new Uint8Array(8 * 1024 * 1024 + 1)], 'big.jpg', { type: 'image/jpeg' });
    await expect(compressImageFile(big)).rejects.toThrow('too large');
  });

  it('rejects disallowed MIME types and extensions', async () => {
    const payload = new Uint8Array(12);
    await expect(compressImageFile(new File([payload], 'anim.gif', { type: 'image/gif' }))).rejects.toThrow('Only JPEG');
    await expect(compressImageFile(new File([payload], 'x.png.exe', { type: 'image/png' }))).rejects.toThrow('Only JPEG');
  });

  it('rejects files whose signature does not match a real image', async () => {
    const fake = new File([new Uint8Array(64)], 'fake.jpg', { type: 'image/jpeg' });
    await expect(compressImageFile(fake)).rejects.toThrow('signature does not match');
  });
});

describe('canvas text wrapping', () => {
  const fakeCtx = () => {
    const lines = [];
    return {
      lines,
      measureText: (t) => ({ width: t.length * 10 }),
      fillText: (t, x, y) => lines.push([t, x, y]),
    };
  };

  it('wraps words within maxWidth and advances the cursor', () => {
    const ctx = fakeCtx();
    const endY = wrapCanvasText(ctx, 'alpha beta gamma delta', 50, 100, 160, 20);
    // 16 chars fit per line: 'alpha beta' (10) fits, adding 'gamma' (16) fits, adding 'delta' (22) wraps
    expect(ctx.lines).toEqual([
      ['alpha beta gamma', 50, 100],
      ['delta', 50, 120],
    ]);
    expect(endY).toBe(120);
  });

  it('handles empty text without drawing', () => {
    const ctx = fakeCtx();
    expect(wrapCanvasText(ctx, '', 0, 100, 100, 20)).toBe(100);
    expect(ctx.lines).toEqual([]);
  });

  it('keeps paragraph breaks and adds spacing between paragraphs', () => {
    const ctx = fakeCtx();
    const endY = wrapCanvasParagraphs(ctx, 'one two\n\nthree', 0, 100, 500, 20);
    expect(ctx.lines.map(([t]) => t)).toEqual(['one two', 'three']);
    // paragraph 1 at y=100, paragraph gap adds 20, blank line adds 12 -> 'three' at 132
    expect(ctx.lines[1][2]).toBe(132);
    expect(endY).toBe(132);
  });
});

describe('createCornerFloraSvg', () => {
  it('renders a decorative SVG hidden from assistive technology', () => {
    const svg = createCornerFloraSvg('royal_lotus', 'top-right');
    expect(svg.tagName.toLowerCase()).toBe('svg');
    expect(svg.getAttribute('aria-hidden')).toBe('true');
    expect(svg.getAttribute('focusable')).toBe('false');
    expect(svg.getAttribute('viewBox')).toBe('0 0 120 120');
    expect(svg.classList.contains('inv-corner-top-right')).toBe(true);
    expect(svg.childElementCount).toBeGreaterThan(5);
  });

  it('produces motif-specific artwork for every theme motif', () => {
    const motifs = new Set(Object.values(INVITATION_THEMES).map((t) => t.motif));
    for (const motif of motifs) {
      const svg = createCornerFloraSvg(motif, 'bottom-left');
      expect(svg.childElementCount, motif).toBeGreaterThan(3);
    }
    // The three motif families produce distinct artwork
    const botanical = createCornerFloraSvg('botanical_vines', 'top-right').childElementCount;
    const deco = createCornerFloraSvg('art_deco_fan', 'top-right').childElementCount;
    const floral = createCornerFloraSvg('rose_blossom', 'top-right').childElementCount;
    expect(new Set([botanical, deco, floral]).size).toBe(3);
  });
});

describe('renderLiveInvitationCard', () => {
  const ev = { title: 'Aisha & Rohan', eventDate: '2027-06-12', location: 'Goa' };
  const inv = {
    themeStyle: 'royal_indigo',
    layoutStyle: 'classic_crest',
    hostLine: '',
    headline: '',
    subheadline: 'Together with their families',
    bodyText: 'Join us',
    dressCode: '',
  };

  it('renders an accessible, labelled preview region with both corner ornaments', () => {
    const card = renderLiveInvitationCard(ev, inv, () => {});
    expect(card.getAttribute('role')).toBe('region');
    expect(card.getAttribute('aria-label')).toContain('Live invitation card preview');
    expect(card.querySelectorAll('svg.inv-corner-decor')).toHaveLength(2);
    expect(card.classList.contains('layout-classic_crest')).toBe(true);
    expect(card.classList.contains('motif-royal_lotus')).toBe(true);
  });

  it('applies the selected theme as CSS variables and falls back for unknown themes', () => {
    const themed = renderLiveInvitationCard(ev, inv, () => {});
    expect(themed.style.getPropertyValue('--inv-bg').trim()).toBe('#161b33');
    expect(themed.style.getPropertyValue('--inv-border').trim()).toBe('#d4af37');
    const fallback = renderLiveInvitationCard(ev, { ...inv, themeStyle: 'does_not_exist' }, () => {});
    expect(fallback.style.getPropertyValue('--inv-bg').trim()).toBe('#161b33');
  });

  it('shows placeholder fallbacks for empty host line, headline, and location', () => {
    const card = renderLiveInvitationCard(ev, { ...inv, location: undefined }, () => {});
    expect(card.querySelector('.inv-host').textContent).toBe('Hosted with love');
    expect(card.querySelector('.inv-headline').textContent).toBe('Aisha & Rohan');
    expect(card.querySelector('.inv-location').textContent).toBe('Goa');
    expect(card.querySelector('.inv-footer p').textContent).toBe('Add dress code');
    const noLocation = renderLiveInvitationCard({ ...ev, location: '' }, inv, () => {});
    expect(noLocation.querySelector('.inv-location').textContent).toBe('Location to be announced');
  });

  it('marks card text as editable textboxes and reports inline edits', () => {
    const onEditField = vi.fn();
    const card = renderLiveInvitationCard(ev, inv, onEditField);
    const editables = card.querySelectorAll('.inv-editable');
    expect(editables.length).toBeGreaterThanOrEqual(4);
    for (const el of editables) {
      expect(el.getAttribute('role')).toBe('textbox');
      expect(el.getAttribute('aria-label')).toContain('Edit');
    }
    const host = card.querySelector('.inv-host');
    host.textContent = 'The Sharma Family';
    host.dispatchEvent(new Event('input', { bubbles: true }));
    expect(onEditField).toHaveBeenCalledWith('hostLine', 'The Sharma Family');
  });
});

describe('createInvitationPng', () => {
  it('fails with a clear error when the browser provides no 2D canvas context', async () => {
    const ev = { title: 'T', type: 'wedding', eventDate: '2027-06-12', location: 'Goa' };
    const inv = { themeStyle: 'royal_indigo', layoutStyle: 'classic_crest' };
    // jsdom has no canvas backend: getContext('2d') returns null
    await expect(createInvitationPng(ev, inv)).rejects.toThrow('could not create the invitation image');
  });
});
