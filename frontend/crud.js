import { button, confirmAction, formView, h } from './dom.js';

/** Inline edit: inserts a form row under the clicked table row. */
export function editButton({ fields, initial, save }) {
  const btn = button('Edit', {
    onClick: () => {
      const row = btn.closest('tr');
      const open = row.nextElementSibling;
      if (open?.classList.contains('edit-row')) {
        open.remove();
        return;
      }
      const form = formView({
        fields,
        initial,
        submitLabel: 'Save changes',
        onSubmit: save,
        onCancel: () => {
          editRow.remove();
          btn.focus();
        },
      });
      const editRow = h('tr', { class: 'edit-row' }, h('td', { colspan: row.children.length }, form));
      row.after(editRow);
      form.querySelector('input, select, textarea')?.focus();
    },
  });
  return btn;
}

export function deleteButton({ what, remove }) {
  return button('Delete', {
    variant: 'danger',
    onClick: async () => {
      if (await confirmAction(`Delete ${what}? This cannot be undone.`, { title: 'Confirm deletion', confirmLabel: 'Delete', variant: 'danger' })) {
        await remove();
      }
    },
  });
}
