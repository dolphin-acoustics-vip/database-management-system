/*
Page helpers used by every OCEAN page (loaded by base.html, after Bootstrap and jQuery).
*/

/**
 * Ask the user to confirm an action in a dialog, instead of the browser's confirm().
 * Resolves to true if they confirm and false if they cancel or close the dialog.
 *
 *   oceanConfirm("Delete this selection?").then(ok => { if (ok) ... });
 *
 * @param {string} message - The question (plain text; new lines are kept).
 * @param {Object} options - {title, confirmText, danger}. danger (default true) makes the button red.
 */
function oceanConfirm(message, options = {}) {
  const modalElement = document.getElementById('ocean-confirm-modal');
  const okButton = document.getElementById('ocean-confirm-ok');
  document.getElementById('ocean-confirm-title').textContent = options.title || 'Are you sure?';
  const body = document.getElementById('ocean-confirm-body');
  body.textContent = message;
  body.style.whiteSpace = 'pre-line';
  okButton.textContent = options.confirmText || 'Confirm';
  okButton.className = 'btn ' + (options.danger === false ? 'btn-primary' : 'btn-danger');
  const modal = bootstrap.Modal.getOrCreateInstance(modalElement);
  return new Promise(resolve => {
    let confirmed = false;
    const onOk = () => { confirmed = true; modal.hide(); };
    okButton.addEventListener('click', onOk, { once: true });
    modalElement.addEventListener('hidden.bs.modal', () => {
      okButton.removeEventListener('click', onOk);
      resolve(confirmed);
    }, { once: true });
    modal.show();
  });
}

/** Show a toast message: icon is 'success', 'info', 'warning' or 'error'. */
function oceanToast(heading, icon = 'info', text = '') {
  $.toast({ heading: heading, text: text, icon: icon, showHideTransition: 'slide', position: 'top-right', hideAfter: 6000, loader: false });
}

/**
 * Keep messages to show on the next page, for when the current page is about to be
 * replaced by a redirect (a toast shown now would disappear with the page).
 */
function oceanToastAfterRedirect(heading, icon = 'info', text = '') {
  const pending = JSON.parse(sessionStorage.getItem('ocean-pending-toasts') || '[]');
  pending.push({ heading: heading, icon: icon, text: text });
  sessionStorage.setItem('ocean-pending-toasts', JSON.stringify(pending));
}

/** Show or hide a loading spinner on a button and disable it while loading. */
function setButtonLoading(button, loading) {
  if (!button) return;
  button.disabled = loading;
  const spinner = button.querySelector('.ocean-spinner');
  if (loading && !spinner) {
    button.insertAdjacentHTML('afterbegin', '<span class="ocean-spinner spinner-border spinner-border-sm" aria-hidden="true"></span>');
  } else if (!loading && spinner) {
    spinner.remove();
  }
}

$(document).ready(function () {
  // Messages flashed by the server (flask.flash) and messages kept from the previous page
  const flashed = JSON.parse(document.getElementById('flash-messages').textContent || '[]');
  flashed.forEach(([category, message]) => oceanToast(message, category === 'message' ? 'info' : category));
  const pending = JSON.parse(sessionStorage.getItem('ocean-pending-toasts') || '[]');
  sessionStorage.removeItem('ocean-pending-toasts');
  pending.forEach(t => oceanToast(t.heading, t.icon, t.text));

  // <form data-confirm="Question?"> asks for confirmation before it is submitted normally
  // (forms submitted with ajaxifyForm handle data-confirm themselves)
  document.querySelectorAll('form[data-confirm]:not([data-ajaxified])').forEach(form => {
    form.addEventListener('submit', event => {
      if (form.dataset.confirmed) return;
      event.preventDefault();
      oceanConfirm(form.dataset.confirm, { confirmText: form.dataset.confirmText }).then(ok => {
        if (!ok) return;
        form.dataset.confirmed = 'true';
        form.requestSubmit ? form.requestSubmit() : form.submit();
      });
    });
  });

  // Enable Bootstrap tooltips (title shown on hover) on elements with data-bs-toggle="tooltip"
  document.querySelectorAll('[data-bs-toggle="tooltip"]').forEach(el => new bootstrap.Tooltip(el));
});

/**
 * Page a table in the browser, for tables that JavaScript fills in from data it has already
 * fetched (lists rendered by the server are paged by the server: see pagination.py).
 * Shows `perPage` rows at a time, with page links underneath. Safe to call again after rows
 * are added or removed.
 */
function oceanPaginateTable(table, perPage = 50) {
  const rows = Array.from(table.querySelectorAll('tr')).filter(row => !row.querySelector('th') && !row.classList.contains('generated-row'));
  const anchor = table.parentElement && table.parentElement.classList.contains('table-responsive') ? table.parentElement : table;
  let pager = table._oceanPager;
  if (!pager) {
    pager = document.createElement('div');
    pager.className = 'ocean-pagination';
    anchor.after(pager);
    table._oceanPager = pager;
    table._oceanPage = 1;
  }
  const pages = Math.max(1, Math.ceil(rows.length / perPage));
  if (rows.length <= perPage) {
    rows.forEach(row => row.hidden = false);
    pager.hidden = true;
    return;
  }
  const page = table._oceanPage = Math.min(Math.max(table._oceanPage, 1), pages);
  rows.forEach((row, i) => row.hidden = i < (page - 1) * perPage || i >= page * perPage);
  const first = (page - 1) * perPage + 1, last = Math.min(page * perPage, rows.length);
  const links = [];
  for (let p = 1; p <= pages; p++) {
    if (p === 1 || p === pages || Math.abs(p - page) <= 2) links.push(p);
    else if (Math.abs(p - page) === 3) links.push('…');
  }
  pager.hidden = false;
  pager.innerHTML = `<span class="text-body-secondary small">${first}–${last} of ${rows.length}</span>
    <nav><ul class="pagination pagination-sm mb-0">
      <li class="page-item ${page === 1 ? 'disabled' : ''}"><a class="page-link" href="#" data-page="${page - 1}" aria-label="Previous page">‹</a></li>
      ${links.map(p => p === '…' ? '<li class="page-item disabled"><span class="page-link">…</span></li>'
        : `<li class="page-item ${p === page ? 'active' : ''}"><a class="page-link" href="#" data-page="${p}">${p}</a></li>`).join('')}
      <li class="page-item ${page === pages ? 'disabled' : ''}"><a class="page-link" href="#" data-page="${page + 1}" aria-label="Next page">›</a></li>
    </ul></nav>`;
  pager.querySelectorAll('a[data-page]').forEach(link => link.addEventListener('click', event => {
    event.preventDefault();
    table._oceanPage = parseInt(link.dataset.page);
    oceanPaginateTable(table, perPage);
  }));
}

// Page every table inside an element with data-paginate-tables, including tables that are
// added or filled in later by the page's scripts.
$(document).ready(function () {
  document.querySelectorAll('[data-paginate-tables]').forEach(container => {
    let scheduled = false;
    const update = () => {
      scheduled = false;
      container.querySelectorAll('table').forEach(table => oceanPaginateTable(table));
    };
    new MutationObserver(mutations => {
      // Ignore the pagers' own changes
      if (mutations.every(m => m.target.closest && m.target.closest('.ocean-pagination'))) return;
      if (!scheduled) { scheduled = true; setTimeout(update, 50); }
    }).observe(container, { childList: true, subtree: true });
    update();
  });
});
