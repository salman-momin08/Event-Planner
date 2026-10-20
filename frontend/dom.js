import { ApiError } from './api.js';

// DOM helpers. All content is inserted as text nodes: never innerHTML (SEC-006).

export function h(tag, attrs, ...children) {
  const el = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs ?? {})) {
    if (value === undefined || value === null || value === false) continue;
    if (key.startsWith('on') && typeof value === 'function') el.addEventListener(key.slice(2), value);
    else if (key === 'class') el.className = value;
    else if (key === 'for') el.htmlFor = value;
    else if (value === true) el.setAttribute(key, '');
    else el.setAttribute(key, String(value));
  }
  append(el, children);
  return el;
}

function append(el, children) {
  for (const child of children.flat(Infinity)) {
    if (child === null || child === undefined || child === false) continue;
    el.append(child instanceof Node ? child : document.createTextNode(String(child)));
  }
}

export function announce(message) {
  const region = document.getElementById('status');
  region.textContent = '';
  setTimeout(() => (region.textContent = message), 50);
}

export function focusHeading(root = document) {
  const heading = root.querySelector('h1, h2');
  if (heading) {
    heading.setAttribute('tabindex', '-1');
    heading.focus();
  }
}

export function formatMoney(cents, currency = 'USD') {
  return new Intl.NumberFormat(undefined, { style: 'currency', currency }).format(cents / 100);
}

export const centsToInput = (cents) => (cents === null || cents === undefined ? '' : (cents / 100).toFixed(2));

export function parseMoney(text) {
  const t = text.trim();
  if (!/^\d{1,9}(\.\d{1,2})?$/.test(t)) return null;
  const [whole, frac = ''] = t.split('.');
  return Number(whole) * 100 + Number(frac.padEnd(2, '0'));
}

export function formatDate(iso) {
  if (!iso) return '';
  const [y, m, d] = iso.split('-').map(Number);
  return new Date(Date.UTC(y, m - 1, d)).toLocaleDateString(undefined, { timeZone: 'UTC', year: 'numeric', month: 'short', day: 'numeric' });
}

export const label = (map, key) => map[key] ?? key;

export const TASK_STATUS = { todo: '○ To do', in_progress: '◐ In progress', done: '✔ Done' };
export const VENDOR_STATUS = { researching: 'Researching', contacted: 'Contacted', quoted: 'Quoted', booked: '✔ Booked', declined: 'Declined' };
export const BUDGET_STATUS = { on_track: '✔ On track', near_limit: '⚠ Near limit (90%+)', over: '⛔ Over budget' };
export const EVENT_TYPE = { wedding: 'Wedding', birthday: 'Birthday', community: 'Community event' };

export function alertBox(message, kind = 'info') {
  return h('p', { class: `alert ${kind}`, role: kind === 'error' ? 'alert' : 'status' }, kind === 'error' ? 'Error: ' : '', message);
}

export function emptyState(text, action) {
  return h('div', { class: 'empty' }, h('p', null, text), action);
}

export function showBanner(message) {
  const main = document.getElementById('main');
  main.querySelector('.banner')?.remove();
  main.prepend(h('div', { class: 'banner' }, alertBox(message, 'error')));
}

export function button(text, { onClick, variant = '', type = 'button' } = {}) {
  const handler =
    onClick &&
    (async (event) => {
      try {
        await onClick(event);
      } catch (err) {
        showBanner(err instanceof ApiError ? err.message : 'Something went wrong. Please try again.');
      }
    });
  return h('button', { type, class: `btn ${variant}`.trim(), onclick: handler }, text);
}

let uid = 0;

function fieldEl(spec, initial) {
  const id = `f-${++uid}`;
  const hintId = `${id}-hint`;
  const errId = `${id}-err`;
  let input;
  const common = { id, name: spec.name, 'aria-describedby': `${spec.hint ? hintId + ' ' : ''}${errId}` };
  switch (spec.kind) {
    case 'textarea':
      input = h('textarea', { ...common, rows: spec.rows ?? 3, maxlength: spec.max }, initial ?? '');
      break;
    case 'select':
    case 'multiselect': {
      input = h(
        'select',
        { ...common, multiple: spec.kind === 'multiselect', size: spec.kind === 'multiselect' ? Math.min(6, Math.max(3, spec.options.length)) : undefined },
        spec.options.map(([value, text]) => {
          const selected = Array.isArray(initial) ? initial.map(String).includes(String(value)) : String(initial ?? '') === String(value);
          return h('option', { value, selected }, text);
        }),
      );
      break;
    }
    case 'money':
      input = h('input', { ...common, type: 'text', inputmode: 'decimal', value: initial === null || initial === undefined ? '' : centsToInput(initial), autocomplete: 'off' });
      break;
    case 'number':
      input = h('input', { ...common, type: 'number', min: spec.min, max: spec.max, step: 1, value: initial ?? '' });
      break;
    default:
      input = h('input', { ...common, type: spec.kind ?? 'text', value: initial ?? '', maxlength: spec.max, autocomplete: spec.autocomplete });
  }
  const errorEl = h('p', { id: errId, class: 'field-error' });
  const el = h(
    'div',
    { class: 'field' },
    h('label', { for: id }, spec.label, spec.required ? h('span', { class: 'req' }, ' (required)') : null),
    spec.hint ? h('p', { id: hintId, class: 'hint' }, spec.hint) : null,
    input,
    errorEl,
  );
  return {
    el,
    input,
    id,
    setError(message) {
      errorEl.textContent = message ? `Error: ${message}` : '';
      if (message) input.setAttribute('aria-invalid', 'true');
      else input.removeAttribute('aria-invalid');
    },
  };
}

function readField(spec, control) {
  const raw = control.input.value;
  switch (spec.kind) {
    case 'multiselect':
      return { value: [...control.input.selectedOptions].map((o) => Number(o.value)) };
    case 'number':
      if (raw === '') return spec.required ? { error: 'Required' } : { skip: true };
      return { value: Number(raw) };
    case 'money': {
      if (raw.trim() === '') return spec.required ? { error: 'Required' } : spec.nullable ? { value: null } : { skip: true };
      const cents = parseMoney(raw);
      return cents === null ? { error: 'Enter an amount like 1250 or 1250.50' } : { value: cents };
    }
    case 'password':
      return raw === '' && spec.required ? { error: 'Required' } : { value: raw };
    default: {
      const value = spec.kind === 'textarea' || spec.kind === 'select' ? raw : raw.trim();
      if (value === '') {
        if (spec.required) return { error: 'Required' };
        if (spec.nullable) return { value: null };
        return { value: '' };
      }
      return { value: spec.numeric ? Number(value) : value };
    }
  }
}

/** Accessible form: labelled fields, hints, per-field errors, error summary that receives focus. */
export function formView({ fields, submitLabel, initial = {}, onSubmit, onCancel }) {
  const controls = new Map();
  const summary = h('div', { class: 'error-summary', tabindex: '-1', hidden: true });
  const form = h('form', { novalidate: true });
  const grid = h('div', { class: 'fields' });
  for (const spec of fields) {
    const c = fieldEl(spec, initial[spec.name]);
    controls.set(spec.name, c);
    grid.append(c.el);
  }
  const submit = h('button', { type: 'submit', class: 'btn primary' }, submitLabel);
  form.append(summary, grid, h('div', { class: 'actions' }, submit, onCancel ? button('Cancel', { onClick: onCancel }) : null));

  function showErrors(errors, general) {
    const items = [];
    for (const [name, message] of Object.entries(errors)) {
      const c = controls.get(name);
      if (c) {
        c.setError(message);
        items.push(h('li', null, h('a', { href: `#${c.id}`, onclick: (e) => (e.preventDefault(), c.input.focus()) }, `${fields.find((f) => f.name === name).label}: ${message}`)));
      } else items.push(h('li', null, message));
    }
    summary.replaceChildren(h('p', { role: 'alert' }, general ?? `Please fix ${items.length} problem${items.length === 1 ? '' : 's'}:`), h('ul', null, items));
    summary.hidden = false;
    summary.focus();
  }

  let busy = false;
  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    if (busy) return;
    for (const c of controls.values()) c.setError('');
    summary.hidden = true;
    const values = {};
    const errors = {};
    for (const spec of fields) {
      const r = readField(spec, controls.get(spec.name));
      if (r.error) errors[spec.name] = r.error;
      else if (!r.skip) values[spec.name] = r.value;
    }
    if (Object.keys(errors).length) return showErrors(errors);
    busy = true;
    submit.setAttribute('aria-disabled', 'true');
    const original = submit.textContent;
    submit.textContent = 'Working…';
    try {
      await onSubmit(values);
    } catch (err) {
      if (err instanceof ApiError && err.details) showErrors(err.details, err.message);
      else showErrors({}, err instanceof ApiError ? err.message : 'Something went wrong. Please try again.');
    } finally {
      busy = false;
      submit.removeAttribute('aria-disabled');
      submit.textContent = original;
    }
  });
  return form;
}

/** Data table with caption, scoped headers, mobile labels and an actions column. */
export function dataTable({ caption, columns, rows, empty, actions }) {
  if (!rows.length) return empty ?? null;
  const head = h('tr', null, columns.map((c) => h('th', { scope: 'col' }, c.header)), actions ? h('th', { scope: 'col' }, 'Actions') : null);
  const body = rows.map((row) =>
    h(
      'tr',
      null,
      columns.map((c, i) => (i === 0 ? h('th', { scope: 'row', 'data-label': c.header }, c.cell(row)) : h('td', { 'data-label': c.header }, c.cell(row)))),
      actions ? h('td', { 'data-label': 'Actions', class: 'row-actions' }, actions(row)) : null,
    ),
  );
  return h('div', { class: 'table-wrap', role: 'region', 'aria-label': caption, tabindex: '0' }, h('table', null, h('caption', null, caption), h('thead', null, head), h('tbody', null, body)));
}

export function confirmAction(message) {
  return window.confirm(message);
}
