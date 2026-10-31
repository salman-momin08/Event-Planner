import { del, get, patch, post, put } from '../api.js';
import { EVENT_TYPE, announce, button, confirmAction, emptyState, formatDate, formView, h, showBanner } from '../dom.js';

const SPACE_PRESETS = [
  ['open_garden', 'Open Garden', 'Outdoor lawn, trees, canopy & natural surroundings'],
  ['party_hall', 'Party Hall', 'Indoor banquet hall, stage, chandeliers & high ceiling'],
  ['house_room', 'House Room', 'Home living room, intimate indoor walls & cozy corners'],
  ['rooftop', 'Rooftop Terrace', 'Open-air skyline deck, pergola & string-light rails'],
  ['banquet_lawn', 'Banquet & Courtyard', 'Covered marquee tent with courtyard entryway'],
  ['other', 'Other / Custom Space', 'Specify your own unique venue or architectural space'],
];

const LIGHTING_MOODS = [
  ['warm_ambient', 'Warm Ambient & Fairy Lights'],
  ['candlelight_intimate', 'Candlelight & Lantern Glow'],
  ['bright_festive', 'Bright Festive & Vibrant'],
  ['daylight_natural', 'Natural Daylight & Botanicals'],
  ['neon_party', 'Modern Uplighting & Party Glow'],
];

const INVITATION_THEMES = {
  royal_indigo: {
    label: 'Royal Indigo & Gold',
    bg: '#161b33',
    innerBg: '#1e2545',
    border: '#d4af37',
    accent: '#f0c75e',
    text: '#f8f9fc',
    muted: '#c7cee3',
    motif: 'royal_lotus',
    defaults: {
      hostLine: 'TOGETHER WITH THEIR FAMILIES',
      subheadline: 'Request the honour of your presence at the royal celebration of',
      bodyText: 'Join us for an unforgettable evening of sacred traditions, music, royal dining, and joyous celebration.',
      dressCode: 'Royal Traditional / Black Tie',
    },
  },
  rose_velvet: {
    label: 'Crimson Rose & Velvet Gold',
    bg: '#380e1c',
    innerBg: '#4c1427',
    border: '#e6b86a',
    accent: '#ffd894',
    text: '#fff7f8',
    muted: '#eec6cf',
    motif: 'rose_blossom',
    defaults: {
      hostLine: 'WITH JOYFUL HEARTS & BLESSINGS',
      subheadline: 'Cordially invite you to share in the celebration of love and union',
      bodyText: 'We warmly welcome you to celebrate with us over a feast of fine cuisine, heartfelt toasts, and dancing.',
      dressCode: 'Festive Couture / Formal',
    },
  },
  botanical_sage: {
    label: 'Botanical Sage & Cream',
    bg: '#1f3328',
    innerBg: '#274033',
    border: '#a3c9a8',
    accent: '#d6eadf',
    text: '#f5fbf7',
    muted: '#c2d8c9',
    motif: 'botanical_vines',
    defaults: {
      hostLine: 'GATHER UNDER THE OPEN CANOPY',
      subheadline: 'You are warmly invited to an intimate garden celebration',
      bodyText: 'Surrounded by greenery, acoustic melodies, and seasonal fare, come celebrate this special day with us.',
      dressCode: 'Garden Chic / Linen & Pastels',
    },
  },
  sunset_terracotta: {
    label: 'Sunset Terracotta & Amber',
    bg: '#3b1d1a',
    innerBg: '#4d2622',
    border: '#f2a65a',
    accent: '#ffd29d',
    text: '#fff8f3',
    muted: '#f0cfc3',
    motif: 'sunburst_marigold',
    defaults: {
      hostLine: 'LET THE CELEBRATION BEGIN',
      subheadline: 'Join us for a vibrant evening of joy, music, and merriment',
      bodyText: 'Bring your warmest smiles and dancing shoes as we celebrate this milestone surrounded by family and friends!',
      dressCode: 'Vibrant Festive Casual',
    },
  },
  lavender_dusk: {
    label: 'Lavender Dusk & Silver Rose',
    bg: '#241b35',
    innerBg: '#312547',
    border: '#d2b7e5',
    accent: '#eed9fc',
    text: '#faf7fc',
    muted: '#cfc1de',
    motif: 'lavender_sprig',
    defaults: {
      hostLine: 'AN ENCHANTING TWILIGHT SOIREE',
      subheadline: 'We invite you to an evening under the twilight sky',
      bodyText: 'Join us as dusk falls for candlelit conversations, signature mocktails, live music, and celebration.',
      dressCode: 'Cocktail / Twilight Elegance',
    },
  },
  ocean_breeze: {
    label: 'Ocean Breeze & Pearl',
    bg: '#0f293a',
    innerBg: '#16384f',
    border: '#7cc6de',
    accent: '#b8e7f5',
    text: '#f4fbfe',
    muted: '#bad7e3',
    motif: 'coastal_palm',
    defaults: {
      hostLine: 'WELCOME TO OUR GATHERING',
      subheadline: 'Bringing together friends, family, and community',
      bodyText: 'We look forward to hosting you for a refreshing celebration filled with inspiring moments and great company.',
      dressCode: 'Smart Coastal Casual',
    },
  },
  midnight_gold: {
    label: 'Midnight Onyx & Champagne',
    bg: '#121318',
    innerBg: '#1a1c24',
    border: '#e0c088',
    accent: '#f5deb3',
    text: '#ffffff',
    muted: '#cfd3e0',
    motif: 'art_deco_fan',
    defaults: {
      hostLine: 'A STARLIGHT GALA CELEBRATION',
      subheadline: 'The pleasure of your company is requested at',
      bodyText: 'Step into an evening of timeless glamour, live entertainment, and celebratory toasts.',
      dressCode: 'Black Tie / Evening Gown',
    },
  },
  minimal_ivory: {
    label: 'Minimal Ivory & Espresso',
    bg: '#f7f3eb',
    innerBg: '#fffdf9',
    border: '#5c4738',
    accent: '#8a5a36',
    text: '#231b15',
    muted: '#5c4e43',
    motif: 'olive_branch',
    defaults: {
      hostLine: 'WARMLY HOSTED BY OUR FAMILY',
      subheadline: 'Please join us for an intimate gathering celebrating',
      bodyText: 'Your presence is the greatest gift as we gather around the table for warm conversation and celebration.',
      dressCode: 'Warm Minimal / Smart Casual',
    },
  },
};

const INVITATION_LAYOUTS = [
  ['classic_crest', 'Classic Crest & Double Frame'],
  ['royal_mandala', 'Royal Heritage Corner Filigree'],
  ['garden_arch', 'Botanical Archway Dome'],
  ['festive_confetti', 'Celebration Starburst & Ribbon'],
  ['modern_editorial', 'Modern Editorial Minimal'],
  ['minimal_split', 'Contemporary Split Banner'],
];

const OCCASION_DESIGN_PRESETS = [
  [
    'Wedding — Royal Crest',
    'royal_indigo',
    'classic_crest',
    {
      hostLine: 'TOGETHER WITH THEIR FAMILIES',
      subheadline: 'Request the honour of your presence at the wedding celebration of',
      bodyText: 'Join us for an unforgettable evening of sacred traditions, music, royal dining, and joyous celebration.',
      dressCode: 'Royal Traditional / Black Tie',
    },
  ],
  [
    'Wedding — Heritage Filigree',
    'rose_velvet',
    'royal_mandala',
    {
      hostLine: 'WITH JOYFUL HEARTS & FAMILY BLESSINGS',
      subheadline: 'Cordially invite you to celebrate the auspicious union of',
      bodyText: 'We warmly welcome you to celebrate with us over a feast of fine cuisine, heartfelt toasts, and Sangeet dancing.',
      dressCode: 'Festive Couture / Traditional Indian',
    },
  ],
  [
    'Garden — Botanical Arch',
    'botanical_sage',
    'garden_arch',
    {
      hostLine: 'GATHER UNDER THE OPEN CANOPY',
      subheadline: 'You are warmly invited to an intimate outdoor garden celebration',
      bodyText: 'Surrounded by greenery, acoustic melodies, and seasonal fare, come celebrate this special occasion with us.',
      dressCode: 'Garden Chic / Linen & Pastels',
    },
  ],
  [
    'Birthday — Festive Celebration',
    'sunset_terracotta',
    'festive_confetti',
    {
      hostLine: 'LET THE CELEBRATION BEGIN',
      subheadline: 'Join us for a milestone birthday celebration of joy, music, and merriment',
      bodyText: 'Bring your warmest smiles and dancing shoes as we celebrate another wonderful year surrounded by family and friends!',
      dressCode: 'Vibrant Festive Casual',
    },
  ],
  [
    'Twilight — Lavender Soiree',
    'lavender_dusk',
    'garden_arch',
    {
      hostLine: 'AN ENCHANTING TWILIGHT SOIREE',
      subheadline: 'We invite you to an evening celebration under the starlit sky',
      bodyText: 'Join us as dusk falls for candlelit conversations, signature mocktails, live acoustic music, and celebration.',
      dressCode: 'Cocktail / Twilight Elegance',
    },
  ],
  [
    'Community — Modern Editorial',
    'ocean_breeze',
    'modern_editorial',
    {
      hostLine: 'WELCOME TO OUR COMMUNITY GATHERING',
      subheadline: 'Bringing together neighbours, friends, and community members',
      bodyText: 'We look forward to hosting you for an inspiring gathering filled with meaningful connections, refreshments, and celebration.',
      dressCode: 'Smart Casual',
    },
  ],
  [
    'Gala — Midnight Champagne',
    'midnight_gold',
    'minimal_split',
    {
      hostLine: 'A STARLIGHT GALA CELEBRATION',
      subheadline: 'The pleasure of your company is requested at our evening gala',
      bodyText: 'Step into an evening of timeless glamour, live entertainment, fine dining, and celebratory toasts.',
      dressCode: 'Black Tie / Evening Attire',
    },
  ],
  [
    'Intimate — Minimal Ivory',
    'minimal_ivory',
    'classic_crest',
    {
      hostLine: 'WARMLY HOSTED BY OUR FAMILY',
      subheadline: 'Please join us for an intimate family gathering celebrating',
      bodyText: 'Your presence is our greatest joy as we gather around the table for warm conversation, dinner, and celebration.',
      dressCode: 'Warm Minimal / Smart Casual',
    },
  ],
];

const INVITATION_TONES = [
  ['warm_traditional', 'Warm & Heartfelt'],
  ['modern_minimal', 'Crisp & Modern'],
  ['playful_celebration', 'Joyful & Festive'],
  ['formal_black_tie', 'Formal & Elegant'],
];

const ALLOWED_IMAGE_MIMES = new Set(['image/jpeg', 'image/png', 'image/webp']);
const ALLOWED_IMAGE_EXT = /\.(?:jpe?g|png|webp)$/i;
const MAX_UPLOAD_BYTES = 8 * 1024 * 1024; // 8 MB max raw upload before client-side downscaling
const MAX_SOURCE_DIMENSION = 6000; // Guard against decompression-bomb images

/** Validates raw magic bytes of an uploaded File before decoding it in the browser. */
async function verifyFileMagicBytes(file) {
  const slice = file.slice(0, 12);
  const buf = await slice.arrayBuffer();
  const b = new Uint8Array(buf);
  if (b.length < 12) return false;
  // JPEG: FF D8 FF
  const isJpeg = b[0] === 0xff && b[1] === 0xd8 && b[2] === 0xff;
  // PNG: 89 50 4E 47 0D 0A 1A 0A
  const isPng =
    b[0] === 0x89 &&
    b[1] === 0x50 &&
    b[2] === 0x4e &&
    b[3] === 0x47 &&
    b[4] === 0x0d &&
    b[5] === 0x0a &&
    b[6] === 0x1a &&
    b[7] === 0x0a;
  // WebP: RIFF....WEBP
  const isWebp =
    b[0] === 0x52 &&
    b[1] === 0x49 &&
    b[2] === 0x46 &&
    b[3] === 0x46 &&
    b[8] === 0x57 &&
    b[9] === 0x45 &&
    b[10] === 0x42 &&
    b[11] === 0x50;
  return isJpeg || isPng || isWebp;
}

/** Sanitizes a filename for safe display (strips paths, double extensions, and control chars). */
function safeFileName(name) {
  return String(name || 'photo.jpg')
    .replace(/^.*[/\\]/, '')
    .replace(/[^\w.-]+/g, '_')
    .slice(0, 60);
}

/** Validates, re-encodes (stripping EXIF/metadata), and compresses an image file into a safe base64 JPEG data URL (< 45 KB). */
async function compressImageFile(file) {
  if (!file || typeof file.size !== 'number') {
    throw new Error('No valid file selected.');
  }
  if (file.size <= 0) {
    throw new Error('The selected file is empty.');
  }
  if (file.size > MAX_UPLOAD_BYTES) {
    throw new Error('Image file is too large (maximum 8 MB). Please choose a smaller photo.');
  }
  if (!ALLOWED_IMAGE_MIMES.has(file.type) || !ALLOWED_IMAGE_EXT.test(file.name || '')) {
    throw new Error('Only JPEG (.jpg, .jpeg), PNG (.png), and WebP (.webp) photos are allowed.');
  }
  if (!(await verifyFileMagicBytes(file))) {
    throw new Error('File signature does not match a valid JPEG, PNG, or WebP image.');
  }

  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onerror = () => reject(new Error('Could not read the selected image file.'));
    reader.onload = () => {
      const img = new Image();
      img.onerror = () => reject(new Error('Selected file could not be decoded as a valid image.'));
      img.onload = () => {
        if (img.width < 16 || img.height < 16 || img.width > MAX_SOURCE_DIMENSION || img.height > MAX_SOURCE_DIMENSION) {
          reject(new Error(`Image dimensions must be between 16×16 and ${MAX_SOURCE_DIMENSION}×${MAX_SOURCE_DIMENSION} pixels.`));
          return;
        }
        const maxDim = 560;
        const scale = Math.min(1, maxDim / Math.max(img.width, img.height));
        const w = Math.max(1, Math.round(img.width * scale));
        const hPx = Math.max(1, Math.round(img.height * scale));
        const canvas = document.createElement('canvas');
        canvas.width = w;
        canvas.height = hPx;
        const ctx = canvas.getContext('2d');
        ctx.drawImage(img, 0, 0, w, hPx);
        let quality = 0.72;
        let dataUrl = canvas.toDataURL('image/jpeg', quality);
        while (dataUrl.length > 44000 && quality > 0.3) {
          quality -= 0.12;
          dataUrl = canvas.toDataURL('image/jpeg', quality);
        }
        if (dataUrl.length > 48000) {
          reject(new Error('Could not compress image below the 48 KB safety limit.'));
          return;
        }
        resolve(dataUrl);
      };
      img.src = String(reader.result);
    };
    reader.readAsDataURL(file);
  });
}

function decorCard(ev, item, base, refresh) {
  const a = item.analysis;
  const isDraft = item.status === 'draft';
  const taskBoxes = [];
  const presetTitle = SPACE_PRESETS.find(([k]) => k === item.spaceType)?.[1] ?? item.spaceType;
  const spaceTitle = item.spaceType === 'other' && item.customSpaceType ? item.customSpaceType : presetTitle;

  const editPanel = h('div', { hidden: true });
  const editForm = formView({
    fields: [
      { name: 'themeConcept', label: 'Theme concept title', required: true, max: 240 },
      { name: 'venueAssessment', label: 'Venue & image spatial assessment', kind: 'textarea', rows: 3, required: true, max: 500 },
      {
        name: 'focalZonesText',
        label: 'Focal zones & styling (one per line: Zone: Idea)',
        kind: 'textarea',
        rows: 4,
        max: 2000,
      },
      { name: 'lightingPlan', label: 'Lighting & ambience plan', kind: 'textarea', rows: 2, required: true, max: 400 },
      {
        name: 'decorTasksText',
        label: 'Decor checklist tasks (one per line: Task | DaysBefore | Details)',
        kind: 'textarea',
        rows: 4,
        max: 3000,
      },
    ],
    initial: {
      themeConcept: a.themeConcept,
      venueAssessment: a.venueAssessment,
      focalZonesText: a.focalZones.map((z) => `${z.zone}: ${z.idea}${z.materials ? ` (${z.materials})` : ''}`).join('\n'),
      lightingPlan: a.lightingPlan,
      decorTasksText: a.decorTasks.map((t) => `${t.title} | ${t.daysBeforeEvent} | ${t.description || ''}`).join('\n'),
    },
    submitLabel: 'Save edited concept',
    onCancel: () => {
      editPanel.hidden = true;
    },
    onSubmit: async (values) => {
      await patch(`${base}/${item.id}`, values);
      await refresh('Decoration concept updated.');
    },
  });
  editPanel.append(h('h5', null, 'Edit Generated Concept Content'), editForm);

  return h(
    'article',
    { class: 'card' },
    h(
      'div',
      { class: 'studio-card-header' },
      h('h4', null, `${spaceTitle} — ${a.themeConcept}`),
      h('span', { class: 'flag' }, isDraft ? 'Draft concept' : 'Applied to plan'),
    ),
    h(
      'p',
      { class: 'sub' },
      `${item.hasImage ? 'Analyzed from uploaded space photo' : 'Generated from venue profile'} · Lighting: ${
        LIGHTING_MOODS.find(([k]) => k === item.lightingMood)?.[1] ?? item.lightingMood
      }`,
    ),
    h('p', null, a.venueAssessment),
    h('h5', null, 'Recommended Color Palette'),
    h(
      'div',
      { class: 'swatch-grid', role: 'list', 'aria-label': 'Color palette' },
      a.colorPalette.map((c) =>
        h(
          'div',
          { class: 'swatch-chip', role: 'listitem' },
          h('span', { class: 'swatch-dot', style: `background:${c.hex}` }),
          h('div', null, h('strong', null, `${c.name} (${c.hex})`), c.usage ? h('span', { class: 'sub' }, c.usage) : null),
        ),
      ),
    ),
    h('h5', null, 'Focal Zones & Spatial Styling'),
    h(
      'ul',
      null,
      a.focalZones.map((z) =>
        h('li', null, h('strong', null, `${z.zone}: `), z.idea, z.materials ? h('span', { class: 'sub' }, `Materials: ${z.materials}`) : null),
      ),
    ),
    h('h5', null, 'Lighting & Ambience Plan'),
    h('p', null, a.lightingPlan),
    h('h5', null, `Actionable Decor Checklist (${a.decorTasks.length})`),
    h(
      'ul',
      { class: isDraft ? 'checklist-list' : undefined },
      a.decorTasks.map((t) => {
        const labelNodes = [
          h('strong', null, t.title),
          ` — ${t.daysBeforeEvent} day${t.daysBeforeEvent === 1 ? '' : 's'} before event`,
          t.description ? `. ${t.description}` : '',
        ];
        if (!isDraft) return h('li', null, ...labelNodes);
        const cb = h('input', { type: 'checkbox', checked: true, value: t.title });
        taskBoxes.push(cb);
        return h('li', null, h('label', { class: 'checkbox-item' }, cb, h('span', null, ...labelNodes)));
      }),
    ),
    h(
      'div',
      { class: 'actions' },
      isDraft
        ? button('Apply decor tasks & budget category', {
            variant: 'primary',
            onClick: async () => {
              const selectedTasks = taskBoxes.filter((cb) => cb.checked).map((cb) => cb.value);
              const r = await post(`${base}/${item.id}/apply`, { tasks: selectedTasks, budgetCategoryPercent: 15 });
              await refresh(
                `Decor plan applied: ${r.tasksCreated} task${r.tasksCreated === 1 ? '' : 's'} added${
                  r.categoryCreated ? ' and "Decor & Styling" budget category created' : ''
                }.`,
              );
            },
          })
        : null,
      button('Edit content', {
        variant: 'tertiary',
        onClick: () => {
          editPanel.hidden = !editPanel.hidden;
          if (!editPanel.hidden) editPanel.querySelector('input, textarea')?.focus();
        },
      }),
      button('Delete', {
        variant: 'danger',
        onClick: async () => {
          if (await confirmAction('Delete this decoration concept?', { title: 'Delete decor concept', confirmLabel: 'Delete', variant: 'danger' })) {
            await del(`${base}/${item.id}`);
            await refresh('Decoration concept deleted.');
          }
        },
      }),
    ),
    editPanel,
  );
}

export async function decorSection(ev, { refresh }) {
  const [aiStatus, analyses] = await Promise.all([get('/ai/status'), get(`/events/${ev.id}/ai/decor`)]);
  const base = `/events/${ev.id}/ai/decor`;

  let uploadedDataUrl = '';

  const spaceSelect = h(
    'select',
    { id: 'decor-space-type' },
    SPACE_PRESETS.map(([key, title, desc]) => h('option', { value: key }, `${title} — ${desc}`)),
  );
  const spaceSelectWrap = h(
    'div',
    { class: 'field-control select-wrap has-value' },
    spaceSelect,
    h('label', { for: 'decor-space-type' }, 'Venue space type'),
  );
  spaceSelect.addEventListener('mousedown', () => {
    if (document.activeElement === spaceSelect) spaceSelectWrap.classList.toggle('is-open');
    else spaceSelectWrap.classList.add('is-open');
  });
  spaceSelect.addEventListener('keydown', (e) => {
    if (e.key === ' ' || e.key === 'Enter' || (e.altKey && (e.key === 'ArrowDown' || e.key === 'ArrowUp'))) {
      spaceSelectWrap.classList.add('is-open');
    } else if (e.key === 'Escape' || e.key === 'Tab') {
      spaceSelectWrap.classList.remove('is-open');
    }
  });
  spaceSelect.addEventListener('blur', () => spaceSelectWrap.classList.remove('is-open'));

  const customFieldWrap = h('div', { class: 'field', hidden: true });
  const customInput = h('input', {
    id: 'decor-custom-space',
    type: 'text',
    placeholder: ' ',
    maxlength: 80,
  });
  const customControl = h('div', { class: 'field-control' }, customInput, h('label', { for: 'decor-custom-space' }, 'Describe your space type'));
  customInput.addEventListener('input', () => customControl.classList.toggle('has-value', customInput.value.trim() !== ''));
  customFieldWrap.append(customControl, h('p', { class: 'hint' }, 'For example: Beachfront Gazebo, Art Gallery, Barn Loft'));

  spaceSelect.addEventListener('change', () => {
    spaceSelectWrap.classList.remove('is-open');
    const isOther = spaceSelect.value === 'other';
    customFieldWrap.hidden = !isOther;
    if (isOther) customInput.focus();
  });

  const previewImg = h('img', { class: 'upload-preview-img', alt: 'Selected venue space preview', hidden: true });
  const clearImgBtn = button('Remove photo', {
    variant: 'danger',
    onClick: () => {
      uploadedDataUrl = '';
      fileInput.value = '';
      previewImg.hidden = true;
      clearImgBtn.hidden = true;
      uploadStatus.textContent = 'No photo selected (optional — helps AI inspect ceiling height, lighting & layout).';
    },
  });
  clearImgBtn.hidden = true;
  const uploadStatus = h(
    'p',
    { class: 'hint' },
    'Optional: Upload a photo of your Open Garden, Party Hall, or House Room so the AI can tailor decor to your actual space.',
  );

  const fileInput = h('input', {
    id: 'decor-photo-input',
    type: 'file',
    accept: '.jpg,.jpeg,.png,.webp,image/jpeg,image/png,image/webp',
    onchange: async () => {
      if (fileInput.files && fileInput.files.length > 1) {
        fileInput.value = '';
        showBanner('Please select only a single venue photo.');
        return;
      }
      const file = fileInput.files?.[0];
      if (!file) return;
      try {
        uploadStatus.textContent = 'Validating and optimizing photo for AI vision analysis…';
        uploadedDataUrl = await compressImageFile(file);
        previewImg.src = uploadedDataUrl;
        previewImg.hidden = false;
        clearImgBtn.hidden = false;
        uploadStatus.textContent = `Ready: ${safeFileName(file.name)} verified and re-encoded for spatial analysis.`;
      } catch (err) {
        uploadedDataUrl = '';
        fileInput.value = '';
        previewImg.removeAttribute('src');
        previewImg.hidden = true;
        clearImgBtn.hidden = true;
        uploadStatus.textContent = 'No photo selected (optional — JPEG, PNG, or WebP up to 8 MB).';
        showBanner(err.message || 'Could not process image.');
      }
    },
  });

  const lightingSelect = h(
    'select',
    { id: 'decor-lighting' },
    LIGHTING_MOODS.map(([val, text]) => h('option', { value: val }, text)),
  );
  const lightingSelectWrap = h(
    'div',
    { class: 'field-control select-wrap has-value' },
    lightingSelect,
    h('label', { for: 'decor-lighting' }, 'Lighting mood'),
  );
  lightingSelect.addEventListener('mousedown', () => {
    if (document.activeElement === lightingSelect) lightingSelectWrap.classList.toggle('is-open');
    else lightingSelectWrap.classList.add('is-open');
  });
  lightingSelect.addEventListener('change', () => lightingSelectWrap.classList.remove('is-open'));
  lightingSelect.addEventListener('blur', () => lightingSelectWrap.classList.remove('is-open'));

  const styleTextarea = h('textarea', {
    id: 'decor-style-pref',
    rows: 3,
    placeholder: ' ',
    maxlength: 600,
  });
  const styleWrap = h('div', { class: 'field-control' }, styleTextarea, h('label', { for: 'decor-style-pref' }, 'Theme, flowers, colors or cultural elements'));
  styleTextarea.addEventListener('input', () => styleWrap.classList.toggle('has-value', styleTextarea.value.trim() !== ''));

  const submitBtn = h('button', { type: 'submit', class: 'btn primary' }, 'Analyze space & generate decor plan');
  const studioForm = h(
    'form',
    {
      class: 'card',
      onsubmit: async (e) => {
        e.preventDefault();
        if (submitBtn.getAttribute('aria-disabled') === 'true') return;
        submitBtn.setAttribute('aria-disabled', 'true');
        const orig = submitBtn.textContent;
        submitBtn.textContent = 'Analyzing space…';
        try {
          announce('Analyzing venue space and generating decoration plan.');
          await post(base, {
            spaceType: spaceSelect.value,
            customSpaceType: spaceSelect.value === 'other' ? customInput.value.trim() : '',
            lightingMood: lightingSelect.value,
            stylePreferences: styleTextarea.value.trim(),
            imageDataUrl: uploadedDataUrl,
          });
          await refresh('Decoration vision plan generated.');
        } catch (err) {
          showBanner(err.message || 'Could not generate decoration plan.');
        } finally {
          submitBtn.removeAttribute('aria-disabled');
          submitBtn.textContent = orig;
        }
      },
    },
    h('h3', null, '1. Choose Your Venue Space Type'),
    h(
      'div',
      { class: 'fields' },
      h(
        'div',
        { class: 'field' },
        spaceSelectWrap,
        h('p', { class: 'hint' }, 'Select the setting that matches your venue so the AI understands structural boundaries, weather exposure, and rigging options.'),
      ),
      customFieldWrap,
    ),
    h('h3', null, '2. Upload Venue or Inspiration Photo (Optional)'),
    h(
      'div',
      { class: 'upload-zone' },
      h(
        'div',
        { class: 'upload-zone-bar' },
        h('label', { for: 'decor-photo-input', class: 'btn secondary' }, 'Choose venue / room photo'),
        clearImgBtn,
      ),
      fileInput,
      uploadStatus,
      previewImg,
    ),
    h('h3', null, '3. Ambience & Styling Preferences'),
    h(
      'div',
      { class: 'fields' },
      h('div', { class: 'field' }, lightingSelectWrap),
      h(
        'div',
        { class: 'field' },
        styleWrap,
        h('p', { class: 'hint' }, 'For example: pastel drapes, marigold garlands, eco-friendly florals, minimalist stage arch, kid-friendly balloon backdrop.'),
      ),
    ),
    h('div', { class: 'actions' }, submitBtn),
  );

  return h(
    'div',
    null,
    h('h2', null, 'Venue & Decoration Vision Studio'),
    h(
      'p',
      null,
      'Select whether your event is in an Open Garden, Party Hall, House Room, or custom venue and upload a photo of the space. The AI inspects the setting and creates a cohesive color palette, focal-zone styling, lighting plan, and setup checklist.',
    ),
    aiStatus.available
      ? studioForm
      : h(
          'div',
          { class: 'alert warn', role: 'status' },
          'The AI assistant is not configured yet. Add your GEMINI_API_KEY in backend/.env to analyze venue photos and generate decoration plans.',
        ),
    h('h3', null, 'Saved Decoration Concepts'),
    analyses.length
      ? h(
          'div',
          null,
          analyses.map((item) => decorCard(ev, item, base, refresh)),
        )
      : emptyState('No decoration concepts yet. Choose a space type above to generate your first spatial styling plan.'),
  );
}

const SVG_NS = 'http://www.w3.org/2000/svg';

function svgNode(tag, attrs, ...children) {
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
function createCornerFloraSvg(motif, position) {
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
function drawCanvasCornerFlora(ctx, W, H, theme) {
  const svgEl = createCornerFloraSvg(theme.motif, 'top-right');
  svgEl.setAttribute('xmlns', SVG_NS);
  svgEl.setAttribute('width', '180');
  svgEl.setAttribute('height', '180');
  const rawSvg = new XMLSerializer()
    .serializeToString(svgEl)
    .replace(/currentColor/g, theme.border)
    .replace(/var\(--inv-inner,\s*#[0-9a-fA-F]+\)/g, theme.innerBg);

  return new Promise((resolve) => {
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
    img.onerror = () => resolve();
    img.src = `data:image/svg+xml;charset=utf-8,${encodeURIComponent(rawSvg)}`;
  });
}

/** Draws a high-resolution (1200x1600) invitation card onto an HTML5 Canvas that matches the Live Card Preview 1:1. */
async function downloadInvitationPng(ev, inv) {
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

  const link = document.createElement('a');
  link.download = `${ev.title.toLowerCase().replace(/[^a-z0-9]+/g, '-') || 'invitation'}-card.png`;
  link.href = canvas.toDataURL('image/png');
  link.click();
}

function wrapCanvasText(ctx, text, x, startY, maxWidth, lineHeight) {
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

function wrapCanvasParagraphs(ctx, text, x, startY, maxWidth, lineHeight) {
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

function renderLiveInvitationCard(ev, inv, onEditField) {
  const theme = INVITATION_THEMES[inv.themeStyle] ?? INVITATION_THEMES.royal_indigo;
  const styleVars = `--inv-bg:${theme.bg};--inv-inner:${theme.innerBg};--inv-border:${theme.border};--inv-accent:${theme.accent};--inv-text:${theme.text};--inv-muted:${theme.muted}`;
  const editableProps = (fieldName, labelText) => ({
    contenteditable: 'true',
    spellcheck: 'false',
    role: 'textbox',
    'aria-label': `Edit ${labelText} directly on card`,
    title: 'Click to edit directly on card',
    oninput: (e) => onEditField?.(fieldName, e.currentTarget.textContent ?? ''),
  });
  return h(
    'div',
    {
      class: `invitation-card-preview layout-${inv.layoutStyle} motif-${theme.motif}`,
      style: styleVars,
      role: 'region',
      'aria-label': 'Live invitation card preview (click any text to edit)',
    },
    h(
      'div',
      { class: 'invitation-inner' },
      createCornerFloraSvg(theme.motif, 'top-right'),
      createCornerFloraSvg(theme.motif, 'bottom-left'),
      h('p', { class: 'inv-host inv-editable', ...editableProps('hostLine', 'host line') }, inv.hostLine || 'Hosted with love'),
      h('p', { class: 'inv-sub inv-editable', ...editableProps('subheadline', 'occasion subtitle') }, inv.subheadline),
      h('h3', { class: 'inv-headline inv-editable', ...editableProps('headline', 'main headline') }, inv.headline || ev.title),
      h('div', { class: 'inv-divider', 'aria-hidden': 'true' }),
      h('p', { class: 'inv-body prewrap inv-editable', ...editableProps('bodyText', 'invitation message') }, inv.bodyText),
      h(
        'div',
        { class: 'inv-meta' },
        h('p', { class: 'inv-date' }, formatDate(ev.eventDate)),
        h('p', { class: 'inv-location' }, ev.location || 'Location to be announced'),
      ),
      h(
        'div',
        { class: 'inv-footer' },
        h('p', { class: 'inv-editable', ...editableProps('dressCode', 'dress code') }, inv.dressCode ? `Dress code: ${inv.dressCode}` : 'Add dress code'),
      ),
    ),
  );
}

export async function invitationSection(ev, { refresh }) {
  const [aiStatus, inv] = await Promise.all([get('/ai/status'), get(`/events/${ev.id}/invitation`)]);
  const base = `/events/${ev.id}/invitation`;

  let designForm;
  const syncCardInlineEditToForm = (fieldName, rawText) => {
    if (!designForm) return;
    const cleanVal = fieldName === 'dressCode' ? rawText.replace(/^Dress code:\s*/i, '').trim() : rawText;
    const el = designForm.querySelector(`[name="${fieldName}"]`);
    if (el) {
      el.value = cleanVal;
      el.closest('.field-control')?.classList.toggle('has-value', cleanVal.trim() !== '');
    }
  };

  const renderPreview = (draft) => renderLiveInvitationCard(ev, draft, syncCardInlineEditToForm);
  const previewHolder = h('div', null, renderPreview(inv));

  const initialPresetIdx = OCCASION_DESIGN_PRESETS.findIndex(([, tk, lk]) => tk === inv.themeStyle && lk === inv.layoutStyle);

  const fields = [
    {
      name: 'occasionPreset',
      label: 'Quick occasion theme preset',
      kind: 'select',
      options: [
        ...OCCASION_DESIGN_PRESETS.map(([title, themeKey], idx) => [String(idx), `${title} (${INVITATION_THEMES[themeKey].label})`]),
        ['custom', 'Custom combination'],
      ],
    },
    {
      name: 'themeStyle',
      label: 'Theme color palette',
      kind: 'select',
      options: Object.entries(INVITATION_THEMES).map(([k, v]) => [k, v.label]),
    },
    {
      name: 'layoutStyle',
      label: 'Card frame & architectural style',
      kind: 'select',
      options: INVITATION_LAYOUTS,
    },
    { name: 'hostLine', label: 'Host line (top header)', max: 120 },
    { name: 'headline', label: 'Main headline / Event title', required: true, max: 120 },
    { name: 'subheadline', label: 'Occasion subtitle', max: 160 },
    { name: 'bodyText', label: 'Invitation message', kind: 'textarea', rows: 4, max: 600 },
    { name: 'dressCode', label: 'Attire / Dress code (optional)', max: 80, hint: 'For example: Traditional Festive, Garden Formal, Casual' },
  ];

  const saveFieldNames = ['themeStyle', 'layoutStyle', 'hostLine', 'headline', 'subheadline', 'bodyText', 'dressCode'];
  let currentState = { ...inv };

  const saveBanner = h('p', { class: 'alert', role: 'status', hidden: true });

  designForm = formView({
    fields,
    initial: { ...currentState, occasionPreset: initialPresetIdx >= 0 ? String(initialPresetIdx) : 'custom' },
    submitLabel: 'Save invitation card',
    onSubmit: async () => {
      const draft = getDraftFromForm();
      const payload = {};
      for (const k of saveFieldNames) payload[k] = String(draft[k] ?? '').trim();
      if (!payload.headline) payload.headline = ev.title;
      const saved = await post(base, payload);
      currentState = { ...saved };
      for (const k of saveFieldNames) {
        const el = designForm.querySelector(`[name="${k}"]`);
        if (el && saved[k] !== undefined) {
          el.value = saved[k];
          el.closest('.field-control')?.classList.add('has-value');
        }
      }
      syncPresetDropdown();
      previewHolder.replaceChildren(renderPreview(getDraftFromForm()));
      saveBanner.textContent = 'Invitation card saved.';
      saveBanner.hidden = false;
      setTimeout(() => {
        saveBanner.hidden = true;
      }, 3500);
      announce('Invitation card saved.');
    },
  });

  const getDraftFromForm = () => {
    const draft = { ...currentState };
    for (const k of saveFieldNames) {
      const el = designForm.querySelector(`[name="${k}"]`);
      if (el) draft[k] = el.value;
    }
    return draft;
  };

  const syncPresetDropdown = () => {
    const presetEl = designForm.querySelector('[name="occasionPreset"]');
    if (!presetEl) return;
    const current = getDraftFromForm();
    const matchIdx = OCCASION_DESIGN_PRESETS.findIndex(([, tk, lk]) => tk === current.themeStyle && lk === current.layoutStyle);
    presetEl.value = matchIdx >= 0 ? String(matchIdx) : 'custom';
  };

  const applyThemeSelection = (themeKey, layoutKey, customDefaults) => {
    const theme = INVITATION_THEMES[themeKey];
    const themeEl = designForm.querySelector('[name="themeStyle"]');
    const layoutEl = designForm.querySelector('[name="layoutStyle"]');
    if (themeEl) {
      themeEl.value = themeKey;
      themeEl.closest('.field-control')?.classList.add('has-value');
    }
    if (layoutEl && layoutKey) {
      layoutEl.value = layoutKey;
      layoutEl.closest('.field-control')?.classList.add('has-value');
    }
    const defaults = customDefaults ?? theme?.defaults;
    if (defaults) {
      for (const [fieldName, textVal] of Object.entries(defaults)) {
        const el = designForm.querySelector(`[name="${fieldName}"]`);
        if (el) {
          el.value = textVal;
          el.closest('.field-control')?.classList.add('has-value');
        }
      }
    }
    syncPresetDropdown();
    previewHolder.replaceChildren(renderPreview(getDraftFromForm()));
  };

  // Live preview updates as the user edits any field in the form
  designForm.addEventListener('input', () => {
    previewHolder.replaceChildren(renderPreview(getDraftFromForm()));
  });
  designForm.addEventListener('change', (e) => {
    if (e.target?.name === 'occasionPreset') {
      const idx = Number(e.target.value);
      const entry = OCCASION_DESIGN_PRESETS[idx];
      if (entry) {
        applyThemeSelection(entry[1], entry[2], entry[3]);
      }
      return;
    }
    if (e.target?.name === 'themeStyle') {
      const matchedPreset = OCCASION_DESIGN_PRESETS.find(([, tk]) => tk === e.target.value);
      applyThemeSelection(e.target.value, matchedPreset?.[2], matchedPreset?.[3]);
      return;
    }
    syncPresetDropdown();
    previewHolder.replaceChildren(renderPreview(getDraftFromForm()));
  });

  const aiPromptBox = h('div', { class: 'card ai-inline-panel', hidden: true });

  if (aiStatus.available) {
    const includeThemeToggle = h('input', {
      type: 'checkbox',
      id: 'inv-ai-include-theme',
      checked: true,
    });
    const toggleWrap = h(
      'label',
      { class: 'checkbox-item', for: 'inv-ai-include-theme' },
      includeThemeToggle,
      h(
        'span',
        null,
        'Include selected theme & current card content (uncheck to let AI generate a fresh theme and wording from scratch)',
      ),
    );

    const aiForm = formView({
      fields: [
        { name: 'tone', label: 'Wording tone', kind: 'select', options: INVITATION_TONES },
        {
          name: 'changeRequest',
          label: 'Describe your invitation customization or idea',
          kind: 'textarea',
          rows: 3,
          required: true,
          max: 500,
          hint: 'For example: Make it a poetic royal Sangeet night invite hosted by the bride & groom, mention sunset cocktails at 6 PM and pastel attire.',
        },
      ],
      initial: { tone: 'warm_traditional', changeRequest: '' },
      submitLabel: 'Generate new template version',
      onCancel: () => {
        aiPromptBox.hidden = true;
      },
      onSubmit: async (v) => {
        const current = getDraftFromForm();
        announce('Generating new invitation template version with AI…');
        const updated = await post(`${base}/ai-draft`, {
          ...v,
          includeSelectedTheme: Boolean(includeThemeToggle.checked),
          themeStyle: current.themeStyle,
          layoutStyle: current.layoutStyle,
          hostLine: current.hostLine,
          dressCode: current.dressCode,
        });
        currentState = { ...updated };
        for (const k of saveFieldNames) {
          const el = designForm.querySelector(`[name="${k}"]`);
          if (el && updated[k] !== undefined) {
            el.value = updated[k];
            el.closest('.field-control')?.classList.add('has-value');
          }
        }
        syncPresetDropdown();
        previewHolder.replaceChildren(renderPreview(getDraftFromForm()));
        aiPromptBox.hidden = true;
        const headlineInput = designForm.querySelector('[name="headline"]');
        headlineInput?.focus();
        announce('New AI invitation template version generated. You can now edit any text directly on the card or in the form.');
      },
    });
    aiForm.prepend(toggleWrap);
    aiPromptBox.append(
      h('h4', null, 'Generate Invitation with AI'),
      h(
        'p',
        { class: 'hint' },
        'Keep the toggle on to refine your currently selected theme, or turn it off so the AI picks the best theme, frame, and wording from your prompt.',
      ),
      aiForm,
    );
  }

  return h(
    'div',
    null,
    h('h2', null, 'Invitation Card Studio'),
    h(
      'p',
      null,
      'Choose an occasion theme preset or mix-and-match color palettes and architectural card frames below. Export a high-resolution PNG invitation card or generate a tailored version with AI.',
    ),
    h(
      'div',
      { class: 'studio-split' },
      h(
        'div',
        null,
        h('h3', null, 'Live Card Preview'),
        previewHolder,
        h(
          'div',
          { class: 'actions' },
          button('Download High-Res PNG Card', {
            variant: 'primary',
            onClick: async () => {
              await downloadInvitationPng(ev, getDraftFromForm());
              announce('Invitation PNG card downloaded.');
            },
          }),
          aiStatus.available
            ? button('Generate with AI', {
                variant: 'secondary',
                onClick: () => {
                  aiPromptBox.hidden = !aiPromptBox.hidden;
                  if (!aiPromptBox.hidden) {
                    aiPromptBox.querySelector('textarea, select')?.focus();
                  }
                },
              })
            : null,
        ),
        aiPromptBox,
      ),
      h('div', null, h('h3', null, 'Customize Card & Wording'), saveBanner, designForm),
    ),
  );
}
