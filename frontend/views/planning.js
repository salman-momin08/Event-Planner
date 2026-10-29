import { del, get, patch, post } from '../api.js';
import { TASK_STATUS, VENDOR_STATUS, button, dataTable, emptyState, formView, formatDate, formatMoney, h } from '../dom.js';
import { deleteButton, editButton } from '../crud.js';

const flags = (t) => [t.overdue ? '⚠ Overdue' : null, t.blocked ? '⛔ Blocked' : null].filter(Boolean).join(' · ');

export async function tasksSection(ev, { refresh }) {
  const [tasks, vendors] = await Promise.all([get(`/events/${ev.id}/tasks`), get(`/events/${ev.id}/vendors`)]);
  const base = `/events/${ev.id}`;
  const titleOf = new Map(tasks.map((t) => [t.id, t.title]));
  const fields = (self) => [
    { name: 'title', label: 'Task', required: true, max: 120 },
    { name: 'description', label: 'Details', kind: 'textarea', max: 1000 },
    { name: 'dueDate', label: 'Due date', kind: 'date', nullable: true, hint: 'YYYY-MM-DD. Leave empty for no deadline.' },
    { name: 'status', label: 'Status', kind: 'select', options: Object.entries(TASK_STATUS) },
    { name: 'category', label: 'Category', max: 80 },
    {
      name: 'vendorId',
      label: 'Related vendor',
      kind: 'select',
      numeric: true,
      nullable: true,
      options: [['', 'None'], ...vendors.map((v) => [v.id, v.name])],
    },
    {
      name: 'dependsOn',
      label: 'Must be done first',
      kind: 'multiselect',
      hint: 'Optional. Check any tasks that need to finish before this one.',
      options: tasks.filter((t) => t.id !== self?.id).map((t) => [t.id, t.title]),
    },
  ];
  return h(
    'div',
    null,
    h('h2', null, 'Tasks'),
    dataTable({
      caption: 'Tasks',
      columns: [
        { header: 'Task', cell: (t) => [t.title, t.description ? h('span', { class: 'sub' }, t.description) : null] },
        { header: 'Due', cell: (t) => (t.dueDate ? formatDate(t.dueDate) : 'No date') },
        { header: 'Status', cell: (t) => [TASK_STATUS[t.status], flags(t) ? h('span', { class: 'flag' }, ` ${flags(t)}`) : null] },
        { header: 'Needs first', cell: (t) => t.dependsOn.map((id) => titleOf.get(id)).join(', ') },
      ],
      rows: tasks,
      actions: (t) => [
        button(t.status === 'done' ? 'Reopen' : 'Mark done', {
          onClick: async () => (
            await patch(`${base}/tasks/${t.id}`, { status: t.status === 'done' ? 'todo' : 'done' }),
            refresh(t.status === 'done' ? `“${t.title}” reopened.` : `“${t.title}” marked done.`)
          ),
        }),
        editButton({ fields: fields(t), initial: t, save: async (v) => (await patch(`${base}/tasks/${t.id}`, v), refresh('Task saved.')) }),
        deleteButton({ what: `task “${t.title}”`, remove: async () => (await del(`${base}/tasks/${t.id}`), refresh('Task deleted.')) }),
      ],
      empty: emptyState(
        'No tasks yet. Add one below, or generate a ready-made timeline.',
        h('a', { class: 'btn', href: `#/events/${ev.id}/timeline` }, 'Generate timeline'),
      ),
    }),
    h(
      'details',
      null,
      h('summary', null, 'Add a task'),
      formView({
        fields: fields(null),
        initial: { status: 'todo' },
        submitLabel: 'Add task',
        onSubmit: async (v) => (await post(`${base}/tasks`, v), refresh('Task added.')),
      }),
    ),
  );
}

export async function timelineSection(ev, { refresh }) {
  const tl = await get(`/events/${ev.id}/timeline`);
  const groups = new Map();
  for (const t of tl.dated) {
    const key = t.dueDate.slice(0, 7);
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(t);
  }
  const item = (t) =>
    h(
      'li',
      null,
      h('strong', null, t.dueDate ? formatDate(t.dueDate) : 'No date'),
      ' — ',
      t.title,
      ' ',
      h('span', { class: 'sub' }, TASK_STATUS[t.status]),
      flags(t) ? h('span', { class: 'flag' }, ` ${flags(t)}`) : null,
    );
  return h(
    'div',
    null,
    h('h2', null, 'Timeline'),
    h('p', null, `Today is ${formatDate(tl.today)}. The event is on ${formatDate(ev.eventDate)}.`),
    h(
      'p',
      null,
      button('Generate timeline from template', {
        variant: 'primary',
        onClick: async () => {
          const r = await post(`/events/${ev.id}/timeline/generate-template`);
          await refresh(`${r.created} task${r.created === 1 ? '' : 's'} added, ${r.skipped} already existed.`);
        },
      }),
    ),
    h(
      'p',
      { class: 'hint' },
      'The template adds typical steps for this event type, dated backwards from the event date. Running it again never creates duplicates.',
    ),
    tl.dated.length || tl.undated.length
      ? [
          ...[...groups.entries()].map(([month, list]) =>
            h(
              'section',
              null,
              h('h3', null, new Date(`${month}-01T00:00:00Z`).toLocaleDateString(undefined, { timeZone: 'UTC', month: 'long', year: 'numeric' })),
              h('ol', { class: 'timeline' }, list.map(item)),
            ),
          ),
          tl.undated.length ? h('section', null, h('h3', null, 'No date'), h('ul', { class: 'timeline' }, tl.undated.map(item))) : null,
        ]
      : emptyState('Your timeline is empty. Generate one from a template, or add dated tasks on the Tasks page.'),
  );
}

export async function vendorsSection(ev, { refresh }) {
  const vendors = await get(`/events/${ev.id}/vendors`);
  const base = `/events/${ev.id}`;
  const money = (c) => formatMoney(c, ev.currency);
  const fields = [
    { name: 'name', label: 'Vendor name', required: true, max: 80 },
    { name: 'category', label: 'Type of service', max: 80, hint: 'For example Catering, Photography, Venue' },
    { name: 'status', label: 'Status', kind: 'select', options: Object.entries(VENDOR_STATUS) },
    { name: 'quoteCents', label: 'Quote', kind: 'money', nullable: true, hint: `In ${ev.currency}. Leave empty if none yet.` },
    { name: 'contact', label: 'Contact and notes', kind: 'textarea', max: 1000, hint: 'Visible only to you. Never shared with the AI assistant.' },
  ];
  return h(
    'div',
    null,
    h('h2', null, 'Vendors'),
    dataTable({
      caption: 'Vendors',
      columns: [
        { header: 'Vendor', cell: (v) => v.name },
        { header: 'Service', cell: (v) => v.category },
        { header: 'Status', cell: (v) => VENDOR_STATUS[v.status] },
        { header: 'Quote', cell: (v) => (v.quoteCents === null ? 'None yet' : money(v.quoteCents)) },
        { header: 'Notes', cell: (v) => h('span', { class: 'prewrap' }, v.contact) },
      ],
      rows: vendors,
      actions: (v) => [
        editButton({ fields, initial: v, save: async (b) => (await patch(`${base}/vendors/${v.id}`, b), refresh('Vendor saved.')) }),
        deleteButton({ what: `vendor “${v.name}”`, remove: async () => (await del(`${base}/vendors/${v.id}`), refresh('Vendor deleted.')) }),
      ],
      empty: emptyState('No vendors yet. Add the venues, caterers and other suppliers you are considering so quotes and decisions stay in one place.'),
    }),
    h(
      'details',
      null,
      h('summary', null, 'Add a vendor'),
      formView({
        fields,
        initial: { status: 'researching' },
        submitLabel: 'Add vendor',
        onSubmit: async (v) => (await post(`${base}/vendors`, v), refresh('Vendor added.')),
      }),
    ),
  );
}
