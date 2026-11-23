// The share button: the system's own sheet where there is one (phones), else a menu of a few places and a copied link.
(() => {
  // What a button shares: the article it names (data-url), else this page.
  const page = document.querySelector('link[rel=canonical]')?.href || location.href.split('#')[0];
  const target = (button) => ({url: button.dataset.url || page, title: button.dataset.title || document.title});
  const T = document.documentElement.lang === 'en'
    ? {copy: 'Copy link', copied: 'Link copied', prompt: 'Link to the article', vk: 'VK'}
    : {copy: 'Скопировать ссылку', copied: 'Ссылка скопирована', prompt: 'Ссылка на статью', vk: 'ВКонтакте'};
  const places = ({url, title}) => [
    ['Telegram', `https://t.me/share/url?url=${encodeURIComponent(url)}&text=${encodeURIComponent(title)}`],
    [T.vk, `https://vk.com/share.php?url=${encodeURIComponent(url)}`],
    ['X', `https://x.com/intent/post?url=${encodeURIComponent(url)}&text=${encodeURIComponent(title)}`],
  ];
  const close = () => document.querySelectorAll('.share-menu').forEach((m) => {
    m.previousElementSibling?.setAttribute('aria-expanded', 'false'); m.remove();
  });
  const copy = async (item, url) => {
    try { await navigator.clipboard.writeText(url); item.textContent = T.copied; }
    catch { window.prompt(T.prompt, url); }
    setTimeout(close, 1200);
  };
  document.querySelectorAll('button.share').forEach((button) => {
    button.addEventListener('click', async (event) => {
      event.stopPropagation();
      const what = target(button);
      if (navigator.share && matchMedia('(pointer: coarse)').matches) {
        try { await navigator.share(what); } catch { /* the reader closed the sheet */ }
        return;
      }
      const open = button.getAttribute('aria-expanded') === 'true';
      close();
      if (open) return;
      const menu = document.createElement('div');
      menu.className = 'share-menu'; menu.setAttribute('role', 'menu');
      const link = document.createElement('button');
      link.type = 'button'; link.setAttribute('role', 'menuitem'); link.textContent = T.copy;
      link.addEventListener('click', (e) => { e.stopPropagation(); copy(link, what.url); });
      menu.append(link);
      for (const [name, href] of places(what)) {
        const a = document.createElement('a');
        a.href = href; a.target = '_blank'; a.rel = 'noopener'; a.setAttribute('role', 'menuitem'); a.textContent = name;
        menu.append(a);
      }
      button.after(menu);
      button.setAttribute('aria-expanded', 'true');
      link.focus();
    });
  });
  document.addEventListener('click', close);
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape') close(); });
})();
