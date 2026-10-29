import { describe, it, expect, vi } from 'vitest';
import {
  h,
  parseMoney,
  centsToInput,
  formatMoney,
  formatDate,
  label,
  alertBox,
  emptyState,
  dataTable,
} from '../../frontend/dom.js';

describe('parseMoney', () => {
  it('parses whole and fractional amounts to cents', () => {
    expect(parseMoney('1250')).toBe(125000);
    expect(parseMoney('1250.50')).toBe(125050);
    expect(parseMoney('1250.5')).toBe(125050);
    expect(parseMoney('0')).toBe(0);
    expect(parseMoney('0.09')).toBe(9);
    expect(parseMoney('  12.30  ')).toBe(1230);
  });

  it('rejects malformed, negative and over-precise input', () => {
    for (const bad of ['', 'abc', '-5', '12.345', '1,250', '1.', '.5', '12e3', '1234567890']) {
      expect(parseMoney(bad)).toBeNull();
    }
  });
});

describe('centsToInput', () => {
  it('formats cents with two decimals', () => {
    expect(centsToInput(125050)).toBe('1250.50');
    expect(centsToInput(0)).toBe('0.00');
  });
  it('returns empty string for null/undefined', () => {
    expect(centsToInput(null)).toBe('');
    expect(centsToInput(undefined)).toBe('');
  });
  it('round-trips with parseMoney', () => {
    for (const cents of [0, 9, 1230, 125050, 99999999]) {
      expect(parseMoney(centsToInput(cents))).toBe(cents);
    }
  });
});

describe('formatMoney', () => {
  it('renders a grouped currency amount', () => {
    const out = formatMoney(125000, 'USD');
    expect(out).toContain('1,250');
    expect(out).toContain('.00');
  });
});

describe('formatDate', () => {
  it('formats an ISO date in UTC without off-by-one drift', () => {
    const out = formatDate('2027-06-12');
    expect(out).toContain('2027');
    expect(out).toContain('Jun');
    expect(out).toContain('12');
  });
  it('returns empty string for falsy input', () => {
    expect(formatDate('')).toBe('');
    expect(formatDate(null)).toBe('');
  });
});

describe('label', () => {
  it('maps known keys and falls back to the key', () => {
    const map = { todo: 'To do' };
    expect(label(map, 'todo')).toBe('To do');
    expect(label(map, 'unknown')).toBe('unknown');
  });
});

describe('h()', () => {
  it('sets class, for, boolean and string attributes', () => {
    const el = h('label', { class: 'field', for: 'x', 'data-k': 'v' });
    expect(el.className).toBe('field');
    expect(el.htmlFor).toBe('x');
    expect(el.getAttribute('data-k')).toBe('v');
  });

  it('renders boolean attributes as present/absent and skips nullish', () => {
    const on = h('input', { required: true, disabled: false, name: null });
    expect(on.hasAttribute('required')).toBe(true);
    expect(on.hasAttribute('disabled')).toBe(false);
    expect(on.hasAttribute('name')).toBe(false);
  });

  it('attaches event listeners for on* function props', () => {
    const onClick = vi.fn();
    const btn = h('button', { onclick: onClick }, 'Go');
    btn.dispatchEvent(new window.Event('click'));
    expect(onClick).toHaveBeenCalledOnce();
  });

  it('inserts all dynamic content as text, never as HTML (SEC-006 / XSS)', () => {
    const payload = '<img src=x onerror="alert(1)"><script>alert(2)</script>';
    const el = h('div', null, payload);
    expect(el.childElementCount).toBe(0);
    expect(el.querySelector('img')).toBeNull();
    expect(el.querySelector('script')).toBeNull();
    expect(el.textContent).toBe(payload);
  });

  it('flattens and ignores null/undefined/false children', () => {
    const el = h('ul', null, [h('li', null, 'a'), null, [false, h('li', null, 'b')]], undefined);
    expect(el.querySelectorAll('li')).toHaveLength(2);
  });
});

describe('alertBox', () => {
  it('uses role=alert for errors and role=status otherwise', () => {
    expect(alertBox('boom', 'error').getAttribute('role')).toBe('alert');
    expect(alertBox('ok', 'info').getAttribute('role')).toBe('status');
    expect(alertBox('boom', 'error').textContent).toContain('Error:');
  });
});

describe('emptyState', () => {
  it('renders the message and optional action', () => {
    const action = h('button', null, 'Add');
    const node = h('div', null, emptyState('Nothing yet', action));
    expect(node.textContent).toContain('Nothing yet');
    expect(node.querySelector('button')).not.toBeNull();
  });
});

describe('dataTable', () => {
  const columns = [
    { header: 'Name', cell: (r) => r.name },
    { header: 'Status', cell: (r) => r.status },
  ];

  it('returns the empty node when there are no rows', () => {
    const empty = h('p', null, 'None');
    expect(dataTable({ caption: 'c', columns, rows: [], empty })).toBe(empty);
  });

  it('renders a caption, scoped headers, row headers and an actions column', () => {
    const node = dataTable({
      caption: 'People',
      columns,
      rows: [{ name: 'Ada', status: 'todo' }],
      actions: (r) => h('button', null, `edit ${r.name}`),
    });
    expect(node.querySelector('caption').textContent).toBe('People');
    expect(node.querySelector('th[scope="col"]').textContent).toBe('Name');
    const rowHeader = node.querySelector('tbody th[scope="row"]');
    expect(rowHeader.textContent).toBe('Ada');
    expect(node.querySelector('.row-actions button').textContent).toBe('edit Ada');
  });
});
