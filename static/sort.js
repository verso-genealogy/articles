// Sorts a data table by the column whose header is pressed; numbers by their data-v.
document.querySelectorAll('table.data[id]').forEach((table) => {
  const heads = [...table.tHead.rows[0].cells];
  heads.forEach((th, col) => {
    th.setAttribute('data-sort', '');
    th.addEventListener('click', () => {
      const down = th.getAttribute('aria-sort') === 'ascending';
      heads.forEach((h) => h.removeAttribute('aria-sort'));
      th.setAttribute('aria-sort', down ? 'descending' : 'ascending');
      const value = (tr) => { const td = tr.cells[col]; return td.hasAttribute('data-v') ? Number(td.getAttribute('data-v')) : td.textContent; };
      const rows = [...table.tBodies[0].rows].sort((a, b) => {
        const x = value(a), y = value(b);
        return (typeof x === 'number' ? x - y : String(x).localeCompare(String(y), 'ru')) * (down ? -1 : 1);
      });
      table.tBodies[0].append(...rows);
    });
  });
});
