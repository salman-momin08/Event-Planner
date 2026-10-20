import { get, post } from '../api.js';
import { announce, button, confirmAction, emptyState, formView, formatMoney, h } from '../dom.js';

const STATUS = { draft: 'Draft (not applied)', applied: '✔ Applied', discarded: 'Discarded' };

function planDetails(p) {
  const plan = p.plan;
  return h(
    'div',
    null,
    h('p', null, plan.summary),
    plan.assumptions.length ? h('div', null, h('h5', null, 'Assumptions the AI made'), h('ul', null, plan.assumptions.map((a) => h('li', null, a)))) : null,
    h('h5', null, 'Theme ideas'),
    h('ul', null, plan.themes.map((t) => h('li', null, h('strong', null, t.name), t.description ? ` — ${t.description}` : ''))),
    h('h5', null, 'Suggested budget split'),
    h('ul', null, plan.budgetAllocations.map((b) => h('li', null, `${b.category}: ${b.percent}%`))),
    h('p', { class: 'hint' }, 'Amounts are calculated from your total budget when you apply the plan.'),
    h('h5', null, `Suggested tasks (${plan.tasks.length})`),
    h('ul', null, plan.tasks.map((t) => h('li', null, h('strong', null, t.title), ` — ${t.daysBeforeEvent} day${t.daysBeforeEvent === 1 ? '' : 's'} before the event`, t.description ? `. ${t.description}` : ''))),
    plan.vendorSuggestions.length
      ? h('div', null, h('h5', null, 'What to look for in vendors'), h('ul', null, plan.vendorSuggestions.map((v) => h('li', null, h('strong', null, `${v.category}: `), v.guidance))))
      : null,
  );
}

export async function aiSection(ev, { refresh }) {
  const [status, plans] = await Promise.all([get('/ai/status'), get(`/events/${ev.id}/ai/plans`)]);
  const base = `/events/${ev.id}/ai/plans`;

  const generate = status.available
    ? formView({
        fields: [{ name: 'preferences', label: 'What are you looking for?', kind: 'textarea', max: 1000, rows: 4, hint: 'For example: outdoor, vegetarian menu, relaxed atmosphere, under budget on decor.' }],
        submitLabel: 'Generate draft plan',
        onSubmit: async (v) => {
          announce('Generating a draft. This can take up to 30 seconds.');
          await post(base, v);
          await refresh('Draft plan created. It has not been applied.');
        },
      })
    : h('div', { class: 'alert warn', role: 'status' },
        h('p', null, 'The AI assistant is not available right now. Everything else works without it.'),
        h('p', null, h('a', { href: `#/events/${ev.id}/timeline` }, 'Generate a template timeline'), ' · ', h('a', { href: `#/events/${ev.id}/budget` }, 'Plan your budget manually')));

  return h(
    'div',
    null,
    h('h2', null, 'AI assistant'),
    h('p', null, 'The assistant drafts themes, a budget split and a task list. It never changes your plan by itself: you review a draft, then choose to apply it. Dates and amounts are always calculated by the app, not the AI.'),
    h('details', null, h('summary', null, 'What is shared with the AI provider?'),
      h('p', null, `Event type, date, expected attendance, location, total budget (${ev.currency}), your request text and, for revisions, the previous draft. Your name, email, notes, vendors and expenses are not sent. Please do not include personal information in your request.`)),
    h('h3', null, 'New draft'),
    generate,
    h('h3', null, 'Drafts'),
    plans.length
      ? h('div', null, plans.map((p) => draftCard(ev, p, base, refresh, status.available)))
      : emptyState('No drafts yet.'),
  );
}

function draftCard(ev, p, base, refresh, aiAvailable) {
  const actions = [];
  if (p.status === 'draft') {
    actions.push(
      button('Apply to my plan', {
        variant: 'primary',
        onClick: async () => {
          if (!confirmAction('Add this draft’s budget categories and tasks to your plan? Existing items with the same names are kept.')) return;
          const r = await post(`${base}/${p.id}/apply`);
          await refresh(`Plan applied: ${r.categoriesCreated} categories and ${r.tasksCreated} tasks added; ${r.categoriesSkipped + r.tasksSkipped} duplicates skipped. Unallocated budget: ${formatMoney(r.unallocatedCents, ev.currency)}.`);
        },
      }),
      button('Discard', { onClick: async () => (await post(`${base}/${p.id}/discard`), refresh('Draft discarded.')) }),
    );
  }
  const revise = aiAvailable
    ? h('details', null, h('summary', null, 'Revise this draft'),
        formView({
          fields: [{ name: 'instruction', label: 'What should change?', kind: 'textarea', required: true, max: 1000, hint: 'For example: spend less on decor and add a rehearsal dinner.' }],
          submitLabel: 'Create revised draft',
          onSubmit: async (v) => {
            announce('Revising the draft. This can take up to 30 seconds.');
            await post(base, { instruction: v.instruction, parentId: p.id });
            await refresh('Revised draft created. It has not been applied.');
          },
        }))
    : null;
  return h(
    'article',
    { class: 'card' },
    h('h4', null, `Draft #${p.id}`, p.parentId ? ` (revision of #${p.parentId})` : ''),
    h('p', { class: 'sub' }, `${STATUS[p.status]} · AI-generated, please review`, p.instruction ? ` · Request: “${p.instruction}”` : p.preferences ? ` · Request: “${p.preferences}”` : ''),
    planDetails(p),
    h('div', { class: 'actions' }, actions),
    revise,
  );
}
