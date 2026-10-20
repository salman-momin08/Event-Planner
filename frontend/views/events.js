import { del, get, patch, post } from '../api.js';
import { EVENT_TYPE, button, confirmAction, dataTable, emptyState, formatDate, formatMoney, formView, h } from '../dom.js';

const CURRENCIES = ['USD', 'EUR', 'GBP', 'INR', 'AUD', 'CAD', 'SGD', 'NZD', 'CHF', 'AED'];

export const eventFields = [
  { name: 'type', label: 'Event type', kind: 'select', required: true, options: Object.entries(EVENT_TYPE) },
  { name: 'title', label: 'Title', required: true, max: 120 },
  { name: 'eventDate', label: 'Event date', kind: 'date', required: true, hint: 'Format: YYYY-MM-DD, for example 2027-05-14' },
  { name: 'attendance', label: 'Expected attendance', kind: 'number', required: true, min: 1, max: 100000 },
  { name: 'location', label: 'Location', max: 120, hint: 'City or venue. This may be shared with the AI assistant if you use it.' },
  { name: 'currency', label: 'Currency', kind: 'select', options: CURRENCIES.map((c) => [c, c]) },
  { name: 'budgetCents', label: 'Total budget', kind: 'money', hint: 'Whole amount or with cents, for example 15000 or 15000.50' },
  { name: 'notes', label: 'Notes', kind: 'textarea', max: 2000, hint: 'Private notes. Not sent to the AI assistant. Do not store payment card details.' },
];

export async function eventsListView() {
  const events = await get('/events?limit=200');
  const node = h(
    'div',
    null,
    h('h1', null, 'Your events'),
    h('p', null, h('a', { class: 'btn primary', href: '#/events/new' }, 'Create event')),
    events.length
      ? dataTable({
          caption: 'Your events',
          columns: [
            { header: 'Event', cell: (e) => h('a', { href: `#/events/${e.id}` }, e.title) },
            { header: 'Type', cell: (e) => EVENT_TYPE[e.type] },
            { header: 'Date', cell: (e) => formatDate(e.eventDate) },
            { header: 'Guests', cell: (e) => e.attendance },
            { header: 'Budget', cell: (e) => formatMoney(e.budgetCents, e.currency) },
          ],
          rows: events,
        })
      : emptyState('You have no events yet. Create your first event to start planning: set a date, headcount and budget, then add tasks, vendors and expenses.'),
  );
  return { title: 'Your events', node };
}

export function newEventView({ navigate }) {
  const form = formView({
    fields: eventFields,
    initial: { currency: 'USD', type: 'wedding' },
    submitLabel: 'Create event',
    onSubmit: async (values) => {
      const ev = await post('/events', values);
      navigate(`#/events/${ev.id}`);
    },
  });
  return { title: 'New event', node: h('div', { class: 'narrow' }, h('h1', null, 'Create event'), form) };
}

export async function overviewSection(ev, { refresh, navigate }) {
  const s = await get(`/events/${ev.id}/summary`);
  const b = s.budget;
  const money = (c) => formatMoney(c, ev.currency);
  const editForm = formView({
    fields: eventFields,
    initial: ev,
    submitLabel: 'Save changes',
    onSubmit: async (values) => {
      await patch(`/events/${ev.id}`, values);
      await refresh('Event details saved.');
    },
  });
  return h(
    'div',
    null,
    h('h2', null, 'Overview'),
    h('dl', { class: 'facts' },
      h('dt', null, 'Type'), h('dd', null, EVENT_TYPE[ev.type]),
      h('dt', null, 'Date'), h('dd', null, formatDate(ev.eventDate)),
      h('dt', null, 'Expected attendance'), h('dd', null, ev.attendance),
      h('dt', null, 'Location'), h('dd', null, ev.location || 'Not set'),
      h('dt', null, 'Notes'), h('dd', { class: 'prewrap' }, ev.notes || 'None')),
    h('h3', null, 'Budget'),
    h('dl', { class: 'facts' },
      h('dt', null, 'Total budget'), h('dd', null, money(b.totalCents)),
      h('dt', null, 'Spent'), h('dd', null, money(b.spentCents)),
      h('dt', null, 'Remaining'), h('dd', null, b.overBudget ? `⛔ Over budget by ${money(-b.remainingCents)}` : `✔ ${money(b.remainingCents)} left`)),
    b.overAllocated ? h('p', { class: 'alert warn', role: 'status' }, `⚠ Category budgets add up to ${money(b.allocatedCents)}, more than your total budget.`) : null,
    h('h3', null, 'Progress'),
    h('dl', { class: 'facts' },
      h('dt', null, 'Tasks done'), h('dd', null, `${s.tasks.done} of ${s.tasks.total}`),
      h('dt', null, 'Overdue tasks'), h('dd', null, s.tasks.overdue ? `⚠ ${s.tasks.overdue}` : '0'),
      h('dt', null, 'Blocked tasks'), h('dd', null, s.tasks.blocked ? `⛔ ${s.tasks.blocked}` : '0'),
      h('dt', null, 'Vendors booked'), h('dd', null, `${s.vendors.booked} of ${s.vendors.total}`)),
    s.tasks.total === 0 ? emptyState('No tasks yet. Generate a timeline from a template, ask the AI assistant for a draft, or add tasks yourself.', h('a', { class: 'btn', href: `#/events/${ev.id}/timeline` }, 'Go to timeline')) : null,
    h('details', null, h('summary', null, 'Edit event details'), editForm),
    h('h3', null, 'Danger zone'),
    button('Delete this event', {
      variant: 'danger',
      onClick: async () => {
        if (!confirmAction(`Delete “${ev.title}” and everything in it? This cannot be undone.`)) return;
        await del(`/events/${ev.id}`);
        navigate('#/events');
      },
    }),
  );
}

export function exportSection(ev) {
  const base = `/api/v1/events/${ev.id}/export`;
  const link = (text, query) => h('li', null, h('a', { href: `${base}?${query}`, download: '' }, text));
  return h(
    'div',
    null,
    h('h2', null, 'Export'),
    h('p', null, 'Download your plan to share or keep a copy. Spreadsheet files are safe to open: cells that could be run as formulas are neutralised.'),
    h('ul', null,
      link('Everything (JSON)', 'format=json'),
      link('Tasks (CSV)', 'format=csv&section=tasks'),
      link('Expenses (CSV)', 'format=csv&section=expenses'),
      link('Vendors (CSV)', 'format=csv&section=vendors')),
  );
}
