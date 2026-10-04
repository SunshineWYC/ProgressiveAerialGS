"use strict";
(() => {
  const dialog = document.getElementById('figure-dialog');
  if (!dialog) return;
  const image = dialog.querySelector('img');
  const area = dialog.querySelector('.dialog-image-area');
  const zoom = dialog.querySelector('[data-zoom]');
  if (!image || !area || !zoom) return;
  document.querySelectorAll('[data-lightbox]').forEach(link => link.addEventListener('click', event => {
    if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey || !dialog.showModal) return;
    const source = link.querySelector('img');
    if (!source) return;
    event.preventDefault();
    image.src = link.href;
    image.alt = source.alt;
    dialog.querySelector('#figure-title').textContent = source.alt;
    dialog.querySelector('[data-original]').href = link.href;
    area.classList.remove('is-zoomed');
    area.scrollTop = 0;
    area.scrollLeft = 0;
    zoom.setAttribute('aria-pressed', 'false');
    zoom.textContent = 'Actual size';
    dialog.showModal();
  }));
  zoom.addEventListener('click', () => {
    const full = area.classList.toggle('is-zoomed');
    zoom.setAttribute('aria-pressed', String(full));
    zoom.textContent = full ? 'Fit to window' : 'Actual size';
  });
  dialog.querySelector('[data-close]')?.addEventListener('click', () => dialog.close());
  dialog.addEventListener('click', event => { if (event.target === dialog) dialog.close(); });
})();


// Keep citation copying independent from the optional image viewer.
(() => {
  const button = document.querySelector('[data-copy-citation]');
  const code = document.getElementById('citation-bibtex');
  const status = document.querySelector('[data-citation-status]');
  if (!button || !code || !status) return;
  button.hidden = false;
  button.addEventListener('click', async () => {
    button.disabled = true;
    try {
      if (!navigator.clipboard?.writeText) throw new Error('Clipboard unavailable');
      await navigator.clipboard.writeText(code.textContent);
      status.textContent = 'BibTeX copied.';
    } catch {
      const selection = window.getSelection();
      const range = document.createRange();
      range.selectNodeContents(code);
      selection?.removeAllRanges();
      selection?.addRange(range);
      status.textContent = 'BibTeX selected. Use your device’s copy command.';
    } finally {
      button.disabled = false;
    }
  });
})();
