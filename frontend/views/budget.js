import { del, get, patch, post } from '../api.js';
import { BUDGET_STATUS, alertBox, dataTable, emptyState, formView, formatDate, formatMoney, h } from '../dom.js';
import { deleteButton, editButton } from '../crud.js';

export async function budgetSection(ev, { refresh }) {
  const [summary, expenses, vendors] = await Promise.all([get(`/events/${ev.id}/summary`), get(`/events/${ev.id}/expenses`), get(`/events/${ev.id}/vendors`)]);
  const b = summary.budget;
  const categories = b.categories;
  const money = (c) => formatMoney(c, ev.currency);
  const catName = new Map(categories.map((c) => [c.id, c.name]));
  const vendorName = new Map(vendors.map((v) => [v.id, v.name]));
  const base = `/events/${ev.id}`;

  const categoryFields = [
    { name: 'name', label: 'Category name', required: true, max: 80 },
    { name: 'plannedCents', label: 'Planned amount', kind: 'money', hint: 'Leave empty for 0' },
    { name: 'spentCents', label: 'Spent amount', kind: 'money', hint: 'Leave empty for 0' },
  ];
  const expenseFields = [
    { name: 'description', label: 'What was it for?', required: true, max: 200 },
    { name: 'amountCents', label: 'Amount', kind: 'money', required: true },
    { name: 'spentOn', label: 'Date', kind: 'date', required: true, hint: 'YYYY-MM-DD' },
    { name: 'categoryId', label: 'Category', kind: 'select', required: true, numeric: true, options: categories.map((c) => [c.id, c.name]) },
    {
      name: 'vendorId',
      label: 'Vendor (optional)',
      kind: 'select',
      numeric: true,
      nullable: true,
      options: [['', 'None'], ...vendors.map((v) => [v.id, v.name])],
    },
  ];

  const spentPct = b.totalCents > 0 ? Math.round((b.spentCents / b.totalCents) * 100) : 0;

  return h(
    'div',
    null,
    h('h2', null, 'Budget'),
    b.totalCents === 0 ? alertBox('Set a total budget in the event details to see spending progress.') : null,
    h(
      'dl',
      { class: 'facts' },
      h('dt', null, 'Spending progress'),
      h(
        'dd',
        { class: 'progress-row' },
        h(
          'progress',
          { max: b.totalCents || 1, value: b.totalCents > 0 ? Math.min(b.spentCents, b.totalCents) : 0, 'aria-label': 'Share of total budget spent' },
          `${spentPct}%`,
        ),
        h('span', { class: 'progress-pct' }, `${spentPct}%`),
      ),
      h('dt', null, 'Total budget'),
      h('dd', null, money(b.totalCents)),
      h('dt', null, 'Allocated to categories'),
      h('dd', null, money(b.allocatedCents)),
      h('dt', null, 'Not yet allocated'),
      h('dd', null, b.overAllocated ? `Over-allocated by ${money(-b.unallocatedCents)}` : money(b.unallocatedCents)),
      h('dt', null, 'Spent'),
      h('dd', null, money(b.spentCents)),
      h('dt', null, 'Remaining'),
      h('dd', null, b.overBudget ? `Over budget by ${money(-b.remainingCents)}` : money(b.remainingCents)),
    ),

    h('h3', null, 'Categories'),
    dataTable({
      caption: 'Budget categories',
      columns: [
        { header: 'Category', cell: (c) => c.name },
        { header: 'Planned', cell: (c) => money(c.plannedCents) },
        { header: 'Spent', cell: (c) => money(c.spentCents) },
        { header: 'Remaining', cell: (c) => (c.varianceCents < 0 ? `-${money(-c.varianceCents)}` : money(c.varianceCents)) },
        { header: 'Status', cell: (c) => BUDGET_STATUS[c.status] },
      ],
      rows: b.categories,
      actions: (c) => [
        editButton({
          fields: categoryFields,
          initial: c,
          save: async (v) => (await patch(`${base}/budget-categories/${c.id}`, v), refresh('Category saved.')),
        }),
        deleteButton({
          what: `category “${c.name}”`,
          remove: async () => {
            try {
              await del(`${base}/budget-categories/${c.id}`);
              await refresh('Category deleted.');
            } catch (e) {
              await refresh(`Could not delete: ${e.message}`);
            }
          },
        }),
      ],
      empty: emptyState('No categories yet. Split your budget into categories such as Venue, Catering and Decor to see where money goes.'),
    }),
    h(
      'details',
      null,
      h('summary', null, 'Add a category'),
      formView({
        fields: categoryFields,
        submitLabel: 'Add category',
        onSubmit: async (v) => (await post(`${base}/budget-categories`, v), refresh('Category added.')),
      }),
    ),

    h('h3', null, 'Expenses'),
    dataTable({
      caption: 'Expenses',
      columns: [
        { header: 'Description', cell: (x) => x.description },
        { header: 'Date', cell: (x) => formatDate(x.spentOn) },
        { header: 'Category', cell: (x) => catName.get(x.categoryId) },
        { header: 'Vendor', cell: (x) => vendorName.get(x.vendorId) ?? '' },
        { header: 'Amount', cell: (x) => money(x.amountCents) },
      ],
      rows: expenses,
      actions: (x) => [
        editButton({ fields: expenseFields, initial: x, save: async (v) => (await patch(`${base}/expenses/${x.id}`, v), refresh('Expense saved.')) }),
        deleteButton({ what: `expense “${x.description}”`, remove: async () => (await del(`${base}/expenses/${x.id}`), refresh('Expense deleted.')) }),
      ],
      empty: emptyState('No expenses logged yet.'),
    }),
    categories.length
      ? h(
          'details',
          null,
          h('summary', null, 'Add an expense'),
          formView({
            fields: expenseFields,
            initial: { spentOn: new Date().toISOString().slice(0, 10) },
            submitLabel: 'Add expense',
            onSubmit: async (v) => (await post(`${base}/expenses`, v), refresh('Expense added.')),
          }),
        )
      : h('p', { class: 'hint' }, 'Add a category before logging expenses.'),
  );
}
