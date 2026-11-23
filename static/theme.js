// The theme switch: light, dark, or as the system has it. The choice is kept in this browser; the page
// renders the same without it (an inline line in <head> applies it before the page is drawn).
(() => {
  const root = document.documentElement;
  const buttons = document.querySelectorAll('.theme button');
  const show = () => buttons.forEach((b) => b.setAttribute('aria-pressed', String((root.dataset.theme || '') === b.dataset.theme)));
  buttons.forEach((b) => b.addEventListener('click', () => {
    if (b.dataset.theme) root.dataset.theme = b.dataset.theme; else delete root.dataset.theme;
    try { if (b.dataset.theme) localStorage.setItem('theme', b.dataset.theme); else localStorage.removeItem('theme'); } catch { /* kept for this page only */ }
    show();
    window.dispatchEvent(new Event('themechange'));
  }));
  show();
})();
