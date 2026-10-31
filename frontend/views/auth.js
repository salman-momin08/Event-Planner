import { api, post } from '../api.js';
import { announce, confirmAction, formView, h } from '../dom.js';

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
    submitVariant: register ? 'primary' : 'success',
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
        h('a', { href: register ? '#/login' : '#/register', class: register ? 'sign-in-link' : undefined }, register ? 'Sign in' : 'Create an account'),
      ),
      h('p', { class: 'hint' }, 'There is no password reset yet. Keep your password safe.'),
    ),
  };
}

export function accountView({ user, onDeleted }) {
  const passwordForm = formView({
    fields: [
      {
        name: 'currentPassword',
        label: 'Current password',
        kind: 'password',
        required: true,
        autocomplete: 'current-password',
      },
      {
        name: 'newPassword',
        label: 'New password',
        kind: 'password',
        required: true,
        autocomplete: 'new-password',
        hint: 'At least 12 characters. Changing your password signs out other sessions.',
      },
    ],
    submitLabel: 'Update password',
    onSubmit: async (values) => {
      await post('/auth/password', values);
      passwordForm.reset();
      announce('Your password has been updated.');
    },
  });
  const form = formView({
    fields: [{ name: 'password', label: 'Confirm your password to delete', kind: 'password', required: true, autocomplete: 'current-password' }],
    submitLabel: 'Delete my account and all data',
    submitVariant: 'danger',
    onSubmit: async (values) => {
      if (
        !(await confirmAction('Permanently delete your account and all events? This cannot be undone.', {
          title: 'Delete account',
          confirmLabel: 'Delete account',
          variant: 'danger',
        }))
      )
        return;
      await api('DELETE', '/auth/me', values);
      await onDeleted();
    },
  });
  return {
    title: 'Account',
    node: h(
      'div',
      { class: 'narrow' },
      h(
        'nav',
        { class: 'breadcrumb', 'aria-label': 'Breadcrumb' },
        h(
          'ol',
          { class: 'breadcrumb-list' },
          h('li', null, h('a', { href: '#/events' }, 'All events')),
          h('li', null, h('span', { 'aria-current': 'page' }, 'Account')),
        ),
      ),
      h('h1', null, 'Account'),
      h('dl', { class: 'facts' }, h('dt', null, 'Name'), h('dd', null, user.displayName), h('dt', null, 'Email'), h('dd', null, user.email)),
      h('h2', null, 'Change password'),
      passwordForm,
      h('h2', null, 'Delete account'),
      h('p', null, 'This removes your account, events, budgets, tasks, vendors and AI drafts. Backups may retain data until they rotate.'),
      form,
    ),
  };
}
