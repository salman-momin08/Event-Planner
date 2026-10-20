import { ApiError, get, post, setUnauthenticatedHandler } from './api.js';
import { EVENT_TYPE, alertBox, announce, button, formatDate, h } from './dom.js';
import { accountView, authView } from './views/auth.js';
import { eventsListView, exportSection, newEventView, overviewSection } from './views/events.js';
import { budgetSection } from './views/budget.js';
import { tasksSection, timelineSection, vendorsSection } from './views/planning.js';
import { aiSection } from './views/ai.js';

const state = { user: null };
const main = document.getElementById('main');
const nav = document.getElementById('main-nav');

const SECTIONS = [
  ['overview', 'Overview', overviewSection],
  ['budget', 'Budget', budgetSection],
  ['tasks', 'Tasks', tasksSection],
  ['timeline', 'Timeline', timelineSection],
  ['vendors', 'Vendors', vendorsSection],
  ['ai', 'AI assistant', aiSection],
  ['export', 'Export', exportSection],
];

const navigate = (hash) => {
  if (location.hash === hash) render();
  else location.hash = hash;
};

function renderNav() {
  const current = location.hash;
  const link = (href, text) => h('li', null, h('a', { href, 'aria-current': current.startsWith(href) ? 'page' : undefined }, text));
  nav.replaceChildren(
    h(
      'ul',
      { class: 'nav-list' },
      ...(state.user
        ? [
            link('#/events', 'Events'),
            link('#/account', 'Account'),
            h('li', null, button('Sign out', { onClick: signOut })),
          ]
        : [link('#/login', 'Sign in'), link('#/register', 'Create account')]),
    ),
  );
}

async function signOut() {
  await post('/auth/logout');
  state.user = null;
  navigate('#/login');
  announce('You have been signed out.');
}

async function onAuthenticated(user) {
  state.user = user;
  navigate('#/events');
}

function notFoundView() {
  return { title: 'Not found', node: h('div', null, h('h1', null, 'Page not found'), h('p', null, h('a', { href: '#/events' }, 'Back to your events'))) };
}

async function eventView(id, section, ctx) {
  const ev = await get(`/events/${id}`);
  const entry = SECTIONS.find(([key]) => key === section);
  if (!entry) return notFoundView();
  const content = await entry[2](ev, ctx);
  return {
    title: `${ev.title} – ${entry[1]}`,
    node: h(
      'div',
      null,
      h('p', null, h('a', { href: '#/events' }, '← All events')),
      h('h1', null, ev.title),
      h('p', { class: 'sub' }, `${EVENT_TYPE[ev.type]} · ${formatDate(ev.eventDate)}`),
      h('nav', { 'aria-label': 'Event sections' }, h('ul', { class: 'subnav' }, SECTIONS.map(([key, text]) =>
        h('li', null, h('a', { href: `#/events/${id}${key === 'overview' ? '' : `/${key}`}`, 'aria-current': key === section ? 'page' : undefined }, text))))),
      content,
    ),
  };
}

let renderToken = 0;

async function render({ keepContext = false } = {}) {
  const token = ++renderToken;
  const segments = (location.hash.replace(/^#\/?/, '') || '').split('/').filter(Boolean);
  const ctx = { navigate, refresh: async (message) => { await render({ keepContext: true }); if (message) announce(message); } };
  let view;
  try {
    const [root, a, b] = segments;
    if (!root) return navigate(state.user ? '#/events' : '#/login');
    if (root === 'login' || root === 'register') {
      if (state.user) return navigate('#/events');
      view = authView({ mode: root, onAuthenticated });
    } else if (!state.user) {
      return navigate('#/login');
    } else if (root === 'account' && !a) {
      view = accountView({ user: state.user, onDeleted: async () => { state.user = null; navigate('#/register'); announce('Your account was deleted.'); } });
    } else if (root === 'events' && !a) {
      view = await eventsListView();
    } else if (root === 'events' && a === 'new') {
      view = newEventView(ctx);
    } else if (root === 'events' && /^\d{1,9}$/.test(a)) {
      view = await eventView(Number(a), b ?? 'overview', ctx);
    } else {
      view = notFoundView();
    }
  } catch (err) {
    if (token !== renderToken) return;
    if (err instanceof ApiError && err.status === 404) view = notFoundView();
    else view = { title: 'Error', node: h('div', null, h('h1', null, 'Something went wrong'), alertBox(err instanceof ApiError ? err.message : 'Unexpected error. Please try again.', 'error'), h('p', null, button('Try again', { onClick: () => render() }))) };
  }
  if (token !== renderToken) return;
  main.replaceChildren(view.node);
  document.title = `${view.title} · Event Planner`;
  renderNav();
  const heading = (keepContext && main.querySelector('h2')) || main.querySelector('h1');
  if (heading) {
    heading.setAttribute('tabindex', '-1');
    heading.focus();
    heading.scrollIntoView?.({ block: 'start' });
  }
}

setUnauthenticatedHandler(() => {
  state.user = null;
  navigate('#/login');
});

window.addEventListener('hashchange', () => render());

try {
  state.user = await get('/auth/me');
} catch {
  state.user = null;
}
await render();
