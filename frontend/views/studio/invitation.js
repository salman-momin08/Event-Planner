/** Invitation Card Studio: theme/layout customization, live preview sync, PNG download, and AI-drafted variants. */
import { get, post } from '../../api.js';
import { announce, button, formView, h, showBanner } from '../../dom.js';
import { createInvitationPng } from './invitation-png.js';
import { renderLiveInvitationCard } from './invitation-preview.js';
import { INVITATION_LAYOUTS, INVITATION_THEMES, INVITATION_TONES, OCCASION_DESIGN_PRESETS } from './themes.js';
export async function invitationSection(ev) {
  const [aiStatus, inv] = await Promise.all([get('/ai/status'), get(`/events/${ev.id}/invitation`)]);
  const base = `/events/${ev.id}/invitation`;

  const syncCardInlineEditToForm = (fieldName, rawText) => {
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
    { name: 'dressCode', label: 'Dress code / Other', max: 80, hint: 'For example: Traditional Festive, Garden Formal, Casual' },
  ];

  const saveFieldNames = ['themeStyle', 'layoutStyle', 'hostLine', 'headline', 'subheadline', 'bodyText', 'dressCode'];
  let currentState = { ...inv };

  const saveBanner = h('p', { class: 'alert', role: 'status', hidden: true });
  const downloadLink = h(
    'a',
    {
      class: 'btn secondary',
      download: `${ev.title.toLowerCase().replace(/[^a-z0-9]+/g, '-') || 'invitation'}-card.png`,
      hidden: true,
    },
    'Save PNG to device',
  );
  const downloadStatus = h('p', { class: 'hint', role: 'status', hidden: true });
  let downloadUrl = null;
  const releaseDownload = () => {
    if (downloadUrl) URL.revokeObjectURL(downloadUrl);
    downloadUrl = null;
    downloadLink.removeAttribute('href');
    downloadLink.hidden = true;
    downloadStatus.hidden = true;
    window.removeEventListener('hashchange', releaseDownload);
    window.removeEventListener('pagehide', releaseDownload);
  };
  const downloadButton = button('Download High-Res PNG Card', {
    variant: 'primary',
    onClick: async () => {
      downloadButton.disabled = true;
      try {
        const blob = await createInvitationPng(ev, getDraftFromForm());
        releaseDownload();
        downloadUrl = URL.createObjectURL(blob);
        downloadLink.href = downloadUrl;
        downloadLink.hidden = false;
        window.addEventListener('hashchange', releaseDownload, { once: true });
        window.addEventListener('pagehide', releaseDownload, { once: true });
        downloadLink.click();
        downloadStatus.textContent = 'PNG ready. If your download did not start, click “Save PNG to device” and check your browser’s downloads.';
        downloadStatus.hidden = false;
        announce(downloadStatus.textContent);
      } catch (err) {
        showBanner(err instanceof Error ? err.message : 'Could not download the invitation. Please try again.');
      } finally {
        downloadButton.disabled = false;
      }
    },
  });

  const designForm = formView({
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
      h('span', null, 'Include selected theme & current card content (uncheck to let AI generate a fresh theme and wording from scratch)'),
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
          downloadButton,
          downloadLink,
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
        downloadStatus,
        aiPromptBox,
      ),
      h('div', null, h('h3', null, 'Customize Card & Wording'), saveBanner, designForm),
    ),
  );
}
