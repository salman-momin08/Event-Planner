/** Live, click-to-edit invitation card preview rendered with theme CSS variables and SVG corner flora. */
import { formatDate, h } from '../../dom.js';
import { createCornerFloraSvg } from './motifs.js';
import { INVITATION_THEMES } from './themes.js';
export function renderLiveInvitationCard(ev, inv, onEditField) {
  const theme = INVITATION_THEMES[inv.themeStyle] ?? INVITATION_THEMES.royal_indigo;
  const styleVars = `--inv-bg:${theme.bg};--inv-inner:${theme.innerBg};--inv-border:${theme.border};--inv-accent:${theme.accent};--inv-text:${theme.text};--inv-muted:${theme.muted}`;
  const editableProps = (fieldName, labelText) => ({
    contenteditable: 'plaintext-only',
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
