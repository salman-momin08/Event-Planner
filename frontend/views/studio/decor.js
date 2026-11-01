/** Decoration Vision Studio: venue space analysis, AI decor concept cards, editing, and apply-to-plan. */
import { del, get, patch, post } from '../../api.js';
import { announce, button, confirmAction, emptyState, formView, h, showBanner } from '../../dom.js';
import { compressImageFile, safeFileName } from './image-upload.js';
import { LIGHTING_MOODS, SPACE_PRESETS } from './themes.js';
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
  const spaceSelectWrap = h('div', { class: 'field-control select-wrap has-value' }, spaceSelect, h('label', { for: 'decor-space-type' }, 'Venue space type'));
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
  const lightingSelectWrap = h('div', { class: 'field-control select-wrap has-value' }, lightingSelect, h('label', { for: 'decor-lighting' }, 'Lighting mood'));
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
        h(
          'p',
          { class: 'hint' },
          'Select the setting that matches your venue so the AI understands structural boundaries, weather exposure, and rigging options.',
        ),
      ),
      customFieldWrap,
    ),
    h('h3', null, '2. Upload Venue or Inspiration Photo (Optional)'),
    h(
      'div',
      { class: 'upload-zone' },
      h('div', { class: 'upload-zone-bar' }, h('label', { for: 'decor-photo-input', class: 'btn secondary' }, 'Choose venue / room photo'), clearImgBtn),
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
