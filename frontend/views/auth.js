import { api, post } from '../api.js';
import { confirmAction, formView, h } from '../dom.js';

export function authView({ mode, onAuthenticated }) {
  const register = mode === 'register';
  const fields = [
    ...(register ? [{ name: 'displayName', label: 'Your name', required: true, max: 80, autocomplete: 'name' }] : []),
    { name: 'email', label: 'Email', kind: 'email', required: true, max: 254, autocomplete: 'email' },
    {
      name: 'password',
      label: 'Password',
      kind: 'password',
      required: true,
      autocomplete: register ? 'new-password' : 'current-password',
      hint: register ? 'At least 12 characters. A passphrase of several words works well.' : undefined,
    },
  ];
  const form = formView({
    fields,
    submitLabel: register ? 'Create account' : 'Sign in',
    onSubmit: async (values) => {
      const user = await post(register ? '/auth/register' : '/auth/login', values);
      await onAuthenticated(user);
    },
  });
  return {
    title: register ? 'Create account' : 'Sign in',
    node: h(
      'div',
      { class: 'narrow' },
      h('h1', null, register ? 'Create your account' : 'Sign in'),
      form,
      h(
        'p',
        null,
        register ? 'Already have an account? ' : 'New here? ',
        h('a', { href: register ? '#/login' : '#/register' }, register ? 'Sign in' : 'Create an account'),
      ),
      h('p', { class: 'hint' }, 'There is no password reset yet. Keep your password safe.'),
    ),
  };
}

export function accountView({ user, onDeleted }) {
  const form = formView({
    fields: [{ name: 'password', label: 'Confirm your password to delete', kind: 'password', required: true, autocomplete: 'current-password' }],
    submitLabel: 'Delete my account and all data',
    onSubmit: async (values) => {
      if (!confirmAction('Permanently delete your account and all events? This cannot be undone.')) return;
      await api('DELETE', '/auth/me', values);
      await onDeleted();
    },
  });
  return {
    title: 'Account',
    node: h(
      'div',
      { class: 'narrow' },
      h('h1', null, 'Account'),
      h('dl', { class: 'facts' }, h('dt', null, 'Name'), h('dd', null, user.displayName), h('dt', null, 'Email'), h('dd', null, user.email)),
      h('h2', null, 'Delete account'),
      h('p', null, 'This removes your account, events, budgets, tasks, vendors and AI drafts. Backups may retain data until they rotate.'),
      form,
    ),
  };
}
