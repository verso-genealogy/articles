// The share button: the system's own sheet where there is one (phones), else a menu of a few places and a copied link.
(() => {
  const url = document.querySelector('link[rel=canonical]')?.href || location.href.split('#')[0];
  const title = document.title;
  const places = [
    ['Telegram', `https://t.me/share/url?url=${encodeURIComponent(url)}&text=${encodeURIComponent(title)}`],
    ['ВКонтакте', `https://vk.com/share.php?url=${encodeURIComponent(url)}`],
    ['X', `https://x.com/intent/post?url=${encodeURIComponent(url)}&text=${encodeURIComponent(title)}`],
  ];
  const close = () => document.querySelectorAll('.share-menu').forEach((m) => {
    m.previousElementSibling?.setAttribute('aria-expanded', 'false'); m.remove();
  });
  const copy = async (item) => {
    try { await navigator.clipboard.writeText(url); item.textContent = 'Ссылка скопирована'; }
    catch { window.prompt('Ссылка на статью', url); }
    setTimeout(close, 1200);
  };
  document.querySelectorAll('button.share').forEach((button) => {
    button.addEventListener('click', async (event) => {
      event.stopPropagation();
      if (navigator.share && matchMedia('(pointer: coarse)').matches) {
        try { await navigator.share({title, url}); } catch { /* the reader closed the sheet */ }
        return;
      }
      const open = button.getAttribute('aria-expanded') === 'true';
      close();
      if (open) return;
      const menu = document.createElement('div');
      menu.className = 'share-menu'; menu.setAttribute('role', 'menu');
      const link = document.createElement('button');
      link.type = 'button'; link.setAttribute('role', 'menuitem'); link.textContent = 'Скопировать ссылку';
      link.addEventListener('click', (e) => { e.stopPropagation(); copy(link); });
      menu.append(link);
      for (const [name, href] of places) {
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
