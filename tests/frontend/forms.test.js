import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { formView } from '../../frontend/dom.js';
import { ApiError } from '../../frontend/api.js';

function mount(node) {
  document.body.append(node);
  return node;
}

afterEach(() => {
  document.body.replaceChildren();
});

describe('formView validation and submission', () => {
  it('blocks submission and shows an error summary when a required field is empty', async () => {
    const onSubmit = vi.fn();
    const form = mount(
      formView({
        fields: [{ name: 'title', label: 'Title', required: true }],
        submitLabel: 'Save',
        onSubmit,
      }),
    );
    form.requestSubmit();
    await Promise.resolve();
    expect(onSubmit).not.toHaveBeenCalled();
    const summary = form.querySelector('.error-summary');
    expect(summary.hidden).toBe(false);
    expect(summary.querySelector('[role="alert"]')).not.toBeNull();
    expect(form.querySelector('.field-error').textContent).toContain('Required');
    expect(form.querySelector('input').getAttribute('aria-invalid')).toBe('true');
  });

  it('collects trimmed values and calls onSubmit when valid', async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    const form = mount(
      formView({
        fields: [
          { name: 'title', label: 'Title', required: true },
          { name: 'budget', label: 'Budget', kind: 'money' },
        ],
        submitLabel: 'Save',
        initial: { title: '  Gala  ' },
        onSubmit,
      }),
    );
    form.querySelector('input[name="budget"]').value = '1250.50';
    form.requestSubmit();
    await Promise.resolve();
    await Promise.resolve();
    expect(onSubmit).toHaveBeenCalledWith({ title: 'Gala', budget: 125050 });
  });

  it('surfaces server-side field errors from an ApiError', async () => {
    const onSubmit = vi.fn().mockRejectedValue(new ApiError(400, { error: { message: 'Invalid input', details: { title: 'Already taken' } } }));
    const form = mount(
      formView({
        fields: [{ name: 'title', label: 'Title', required: true }],
        submitLabel: 'Save',
        onSubmit,
      }),
    );
    form.querySelector('input[name="title"]').value = 'Gala';
    form.requestSubmit();
    await Promise.resolve();
    await Promise.resolve();
    await Promise.resolve();
    expect(form.querySelector('.field-error').textContent).toContain('Already taken');
  });

  it('rejects malformed money input before calling onSubmit', async () => {
    const onSubmit = vi.fn();
    const form = mount(
      formView({
        fields: [{ name: 'budget', label: 'Budget', kind: 'money', required: true }],
        submitLabel: 'Save',
        onSubmit,
      }),
    );
    form.querySelector('input[name="budget"]').value = 'not-a-number';
    form.requestSubmit();
    await Promise.resolve();
    expect(onSubmit).not.toHaveBeenCalled();
    expect(form.querySelector('.field-error').textContent).toContain('amount');
  });

  it('renders a floating label wrapper that toggles has-value on input', () => {
    const form = mount(
      formView({
        fields: [{ name: 'title', label: 'Title', required: true }],
        submitLabel: 'Save',
        onSubmit: vi.fn(),
      }),
    );
    const wrap = form.querySelector('.field-control');
    const input = form.querySelector('input[name="title"]');
    expect(wrap).not.toBeNull();
    expect(wrap.classList.contains('has-value')).toBe(false);
    input.value = 'Gala';
    input.dispatchEvent(new window.Event('input'));
    expect(wrap.classList.contains('has-value')).toBe(true);
  });

  it('toggles is-open on select-wrap for chevron open/close animation', () => {
    const form = mount(
      formView({
        fields: [{ name: 'type', label: 'Type', kind: 'select', options: [['wedding', 'Wedding'], ['birthday', 'Birthday']] }],
        submitLabel: 'Save',
        onSubmit: vi.fn(),
      }),
    );
    const wrap = form.querySelector('.field-control.select-wrap');
    const select = form.querySelector('select[name="type"]');
    expect(wrap).not.toBeNull();
    expect(wrap.classList.contains('is-open')).toBe(false);
    select.dispatchEvent(new window.MouseEvent('mousedown'));
    expect(wrap.classList.contains('is-open')).toBe(true);
    select.dispatchEvent(new window.Event('change'));
    expect(wrap.classList.contains('is-open')).toBe(false);
    select.dispatchEvent(new window.KeyboardEvent('keydown', { key: ' ' }));
    expect(wrap.classList.contains('is-open')).toBe(true);
    select.dispatchEvent(new window.KeyboardEvent('keydown', { key: 'Escape' }));
    expect(wrap.classList.contains('is-open')).toBe(false);
  });
});

describe('ApiError', () => {
  it('derives message, code, details and requestId from the error body', () => {
    const err = new ApiError(409, { error: { code: 'email_taken', message: 'Taken', details: { email: 'x' }, requestId: 'r1' } });
    expect(err.status).toBe(409);
    expect(err.code).toBe('email_taken');
    expect(err.message).toBe('Taken');
    expect(err.details).toEqual({ email: 'x' });
    expect(err.requestId).toBe('r1');
  });

  it('falls back to safe defaults for an empty body', () => {
    const err = new ApiError(0, null);
    expect(err.code).toBe('error');
    expect(err.message).toBe('Request failed');
    expect(err.details).toBeNull();
  });
});
