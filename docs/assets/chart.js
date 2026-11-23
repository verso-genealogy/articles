// The data layer of the page: the rows of data/results.json, the filters' state, and a redraw whenever either
// or the width changes. The chart code below asks it for rows (data), registers what it draws (draw) and
// what follows the filters (onData).
const dash = (() => {
  let rows = [], status = 'loading', params = {};
  const draws = [], listeners = [];
  const render = () => {
    listeners.forEach((fn) => fn());
    draws.forEach(([name, fn]) => document.querySelectorAll(`[data-draw="${name}"]`).forEach((el) => fn(el)));
  };
  let timer = 0;
  window.addEventListener('resize', () => { clearTimeout(timer); timer = setTimeout(render, 120); });
  window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', render);
  document.addEventListener('DOMContentLoaded', () => {
    render();
    fetch('../data/results.json').then((r) => { if (!r.ok) throw new Error(r.status); return r.json(); })
      .then((data) => { rows = data; status = 'ok'; render(); })
      .catch(() => { status = 'error'; render(); });
  });
  return {
    data: () => ({status, data: rows}),
    draw: (name, fn) => { draws.push([name, fn]); },
    onData: (fn) => { listeners.push(fn); },
    params: () => params,
    setParams: (next) => { params = {...params, ...next}; render(); },
  };
})();

(() => {

  const VENDORS = ['Claude', 'Google', 'OpenAI', 'xAI', 'Alibaba'];
  const SYMBOLS = [d3.symbolCircle, d3.symbolTriangle, d3.symbolSquare, d3.symbolDiamond, d3.symbolCross];
  const EFFORTS = ['none', 'off', 'low', 'medium', 'high', 'xhigh'];
  const LABELLED = new Set(['haiku-off', 'haiku-high', 'sonnet-high', 'opus-low', 'opus-medium', 'opus-high', 'opus-xhigh',
    'fable-low', 'fable-high', 'gemini-3.8-flash-low', 'gemini-3.8-flash-high', 'gemini-4-argon-high',
    'gemini-3.1-pro-preview-high', 'gpt-6.1-terra-high', 'gpt-6.1-sol-high', 'gpt-6-astra-high',
    'fable52-low', 'fable52-high', 'grok-4.7-high']);
  const VERSION = {haiku: '5.5', sonnet: '5.5', opus: '5.5', opus5: '5', fable: '5.1', fable52: '5.2'};
  // A configuration as the article names it: «Gemini 4 Carbon, low».
  const MODELS = {"gemini-4-argon": "Gemini 4 Argon", "gemini-4-neon": "Gemini 4 Neon", "gemini-4-carbon": "Gemini 4 Carbon", "gemini-4-hydrogen": "Gemini 4 Hydrogen", "fable52": "Claude Fable 5.2", "opus": "Claude Opus 5.5", "opus5": "Claude Opus 5", "fable": "Claude Fable 5.1", "gpt-6.2-sol": "GPT-6.2 Sol", "gpt-6.2-astra": "GPT-6.2 Astra", "gpt-6.1-terra": "GPT-6.1 Terra", "gemini-3.8-flash": "Gemini 3.8 Flash", "sonnet": "Claude Sonnet 5.5", "gpt-6.1-sol": "GPT-6.1 Sol", "qwen4-max": "Qwen4 Max", "grok-4.7": "Grok 4.7", "haiku": "Claude Haiku 5.5", "gpt-6-luna": "GPT-6 Luna", "gemini-3.1-pro-preview": "Gemini 3.1 Pro (preview)"};
  const LEVEL = /-(none|off|low|medium|high|xhigh)$/;
  const full = (arm) => { const base = arm.replace(/-ultrahigh$/, ''); const level = (base.match(LEVEL) || [])[1];
    const model = MODELS[base.replace(LEVEL, '')] || base.replace(LEVEL, '');
    return `${model}, ${level === 'none' || level === 'off' ? 'без рассуждений' : level}` + (arm.endsWith('-ultrahigh') ? ', кадры в высоком разрешении' : ''); };
  const RU = d3.formatLocale({decimal: ',', thousands: '\u00a0', grouping: [3], currency: ['$', '']});
  const SPLIT = {test: 'основной', dev: 'отладочный'};
  const MAKER = (vendor) => (vendor === 'Claude' ? 'Anthropic' : vendor);
  const named = (arm) => arm.replace(/^(haiku|sonnet|opus5|opus|fable52|fable)(?=-|$)/, (f) => `${f.replace(/\d+$/, '')}-${VERSION[f]}`);
  const short = (arm) => named(arm).replace('gemini-', '').replace('gpt-', '').replace('-preview', '');
  const color = (vendor) => `var(--hb-c${VENDORS.indexOf(vendor)})`;
  const family = (arm) => arm.replace(/-ultrahigh$/, '').replace(/-(none|off|low|medium|high|xhigh)$/, '');
  const picked = () => { const m = dash.params().models; return Array.isArray(m) ? m : []; };
  const shown = (arm) => { const p = picked(); return p.length === 0 || p.includes(family(arm)); };
  const METRICS = {review: 'review_per_100', silent: 'silent_per_100', loud: 'loud_per_100', all: 'errors_per_100'};
  const CI = {review: 'review_ci', silent: 'silent_ci', all: 'errors_ci'};
  const AXIS = {review: 'цена вычитки на 100 имен', silent: 'тихих ошибок на 100 имен', loud: 'ошибок под вопросом на 100 имен', all: 'всех ошибок на 100 имен'};
  const metric = () => (METRICS[dash.params().metric] ? dash.params().metric : 'silent');
  const ci = (r) => { const v = CI[metric()] && r[CI[metric()]]; const a = typeof v === 'string' ? JSON.parse(v) : v; return Array.isArray(a) ? a.map(Number) : null; };
  document.querySelectorAll('.hb-metric').forEach((chip) => chip.addEventListener('click', () => {
    dash.setParams({metric: chip.getAttribute('data-metric')});
  }));
  document.querySelectorAll('.hb-model').forEach((chip) => chip.addEventListener('click', () => {
    const m = chip.getAttribute('data-model');
    if (!m) { dash.setParams({models: []}); return; }
    const p = picked();
    dash.setParams({models: p.includes(m) ? p.filter((x) => x !== m) : [...p, m]});
  }));
  dash.onData(() => {
    const p = picked();
    document.querySelectorAll('.hb-metric').forEach((chip) => {
      chip.setAttribute('aria-pressed', String(chip.getAttribute('data-metric') === metric()));
    });
    document.querySelectorAll('.hb-model').forEach((chip) => {
      const m = chip.getAttribute('data-model');
      chip.setAttribute('aria-pressed', String(m ? p.includes(m) : p.length === 0));
    });
  });
  const fmtUsd = (v) => '$' + (v < 0.1 ? RU.format('.3f')(v) : v < 10 ? RU.format('.2f')(v) : RU.format('.1f')(v));

  function scatter(el, split) {
    const g = dash.data('results');
    el.replaceChildren();
    if (g.status === 'error') {
      el.classList.remove('dash-skeleton');
      el.style.display = 'flex'; el.style.alignItems = 'center'; el.style.justifyContent = 'center';
      el.textContent = 'Не удалось загрузить данные';
      return;
    }
    if (g.status !== 'ok') { el.classList.add('dash-skeleton'); el.textContent = '—'; return; }
    el.classList.remove('dash-skeleton'); el.style.display = '';
    const rows = g.data.filter((r) => r.split === split && r[METRICS[metric()]] != null)
      .map((r) => ({...r, silent: Number(r[METRICS[metric()]]), lohi: ci(r), usd: Number(r.usd_per_100_batch)}));
    const W = Math.max(320, el.clientWidth), H = 420, m = {top: 16, right: 24, bottom: 44, left: 52};
    const x = d3.scaleLog([0.02, Math.max(10, d3.max(rows, (r) => r.usd) * 1.6)], [m.left, W - m.right]);
    const lo = d3.min(rows, (r) => (r.lohi ? r.lohi[0] : r.silent)), hi = d3.max(rows, (r) => (r.lohi ? r.lohi[1] : r.silent));
    // As the article's chart: fewer errors lower, on a logarithmic scale that keeps the leaders apart.
    const y = d3.scaleLog([Math.max(0.5, lo * 0.85), hi * 1.12], [H - m.bottom, m.top]).clamp(true);
    const yticks = [0.5, 1, 2, 3, 4, 6, 8, 10, 15, 20, 30, 50, 80].filter((v) => v >= y.domain()[0] && v <= y.domain()[1]);
    const svg = d3.select(el).append('svg').attr('width', '100%').attr('viewBox', `0 0 ${W} ${H}`).attr('role', 'img')
      .attr('aria-label', `Тихие ошибки на 100 имен против цены, ${split}`);
    svg.append('g').selectAll('line').data(yticks).join('line')
      .attr('x1', m.left).attr('x2', W - m.right).attr('y1', y).attr('y2', y).style('stroke', 'var(--line)');
    const xticks = [0.03, 0.1, 0.3, 1, 3, 10, 30].filter((v) => v <= x.domain()[1]);
    const ax = svg.append('g').attr('transform', `translate(0,${H - m.bottom})`)
      .call(d3.axisBottom(x).tickValues(xticks).tickFormat((v) => '$' + RU.format('~g')(v)).tickSizeOuter(0));
    const ay = svg.append('g').attr('transform', `translate(${m.left},0)`).call(d3.axisLeft(y).tickValues(yticks).tickFormat(RU.format('~g')).tickSizeOuter(0));
    [ax, ay].forEach((a) => {
      a.attr('font-size', null).attr('font-family', null);
      a.selectAll('text').style('fill', 'var(--muted)').style('font-size', '13px');
      a.selectAll('line,path').style('stroke', 'var(--axis)');
    });
    svg.append('text').attr('x', W - m.right).attr('y', H - 6).attr('text-anchor', 'end')
      .style('fill', 'var(--muted)').style('font-size', '13px').text('$ за 100 записей, пакетом');
    svg.append('text').attr('transform', `translate(14,${m.top}) rotate(-90)`).attr('text-anchor', 'end')
      .style('fill', 'var(--muted)').style('font-size', '13px').text(AXIS[metric()]);
    const families = d3.groups(rows, (r) => r.arm.replace(/-(none|off|low|medium|high|xhigh)$/, ''))
      .map(([, rs]) => rs.sort((a, b) => EFFORTS.indexOf(a.arm.split('-').pop()) - EFFORTS.indexOf(b.arm.split('-').pop())))
      .filter((rs) => rs.length > 1);
    svg.append('g').selectAll('path').data(families).join('path')
      .attr('d', d3.line((r) => x(r.usd), (r) => y(r.silent)))
      .style('fill', 'none').style('stroke', (rs) => shown(rs[0].arm) ? color(rs[0].vendor) : 'var(--axis)')
      .style('stroke-width', 1.5).style('stroke-opacity', (rs) => shown(rs[0].arm) ? 0.55 : 0.3).style('stroke-linejoin', 'round').style('stroke-linecap', 'round');
    svg.append('g').selectAll('line').data(rows.filter((r) => r.lohi && shown(r.arm))).join('line')
      .attr('x1', (r) => x(r.usd)).attr('x2', (r) => x(r.usd)).attr('y1', (r) => y(r.lohi[0])).attr('y2', (r) => y(r.lohi[1]))
      .style('stroke', (r) => color(r.vendor)).style('stroke-width', 2).style('stroke-opacity', 0.3).style('stroke-linecap', 'round');
    svg.append('text').attr('x', m.left + 8).attr('y', H - m.bottom - 8)
      .style('fill', 'var(--muted)').style('font-size', '13px').text('↙ лучше: дешевле и меньше ошибок');
    const tip = document.createElement('div');
    tip.className = 'hb-tip'; tip.hidden = true; el.append(tip);
    const pts = svg.append('g').selectAll('path').data([...rows].sort((a, b) => shown(a.arm) - shown(b.arm))).join('path')
      .attr('transform', (r) => `translate(${x(r.usd)},${y(r.silent)})`)
      .attr('d', (r) => d3.symbol(SYMBOLS[VENDORS.indexOf(r.vendor)], 80)())
      .style('fill', (r) => shown(r.arm) ? color(r.vendor) : 'var(--axis)')
      .style('opacity', (r) => shown(r.arm) ? 1 : 0.45)
      .style('stroke', 'var(--panel)').style('stroke-width', 2);
    const EFFORT_TAG = {none: 'none', off: 'off', low: 'low', medium: 'med', high: 'high', xhigh: 'xh'};
    const fams = d3.groups(rows, (r) => r.arm.replace(/-(none|off|low|medium|high|xhigh)$/, ''));
    const want = [];
    for (const [fam, rs] of fams) {
      const on = picked().length ? shown(rs[0].arm) : true;
      if (!on) continue;
      if (rs.length === 1) { want.push({r: rs[0], text: short(rs[0].arm), strong: true}); continue; }
      const best = rs.reduce((a, b) => (b.silent < a.silent ? b : a));
      want.push({r: best, text: short(fam), strong: true});
      if (picked().length || LABELLED.has(best.arm)) rs.forEach((r) => want.push({r, text: EFFORT_TAG[r.arm.split('-').pop()] ?? '', strong: false}));
    }
    const boxes = rows.map((r) => ({x0: x(r.usd) - 6, x1: x(r.usd) + 6, y0: y(r.silent) - 6, y1: y(r.silent) + 6}));
    boxes.push({x0: m.left, x1: m.left + 230, y0: H - m.bottom - 22, y1: H - m.bottom});
    const hits = (b) => b.x0 < m.left || b.x1 > W - 2 || b.y0 < 0 || b.y1 > H - m.bottom
      || boxes.some((o) => b.x0 < o.x1 && b.x1 > o.x0 && b.y0 < o.y1 && b.y1 > o.y0);
    const lg = svg.append('g');
    for (const w of want.sort((a, b) => b.strong - a.strong)) {
      const t = lg.append('text').style('font-size', '13px')
        .style('fill', w.strong ? 'var(--fg)' : 'var(--muted)').text(w.text);
      const tw = t.node().getComputedTextLength(), th = 12, px = x(w.r.usd), py = y(w.r.silent);
      const spots = [[8, 4], [-8 - tw, 4], [-tw / 2, -9], [-tw / 2, 17], [8, -7], [8, 15], [-8 - tw, -7], [-8 - tw, 15],
        [14, -16], [14, 24], [-14 - tw, -16], [-14 - tw, 24]];
      const spot = spots.map(([dx, dy]) => ({dx, dy, b: {x0: px + dx - 2, x1: px + dx + tw + 2, y0: py + dy - th + 2, y1: py + dy + 2}}))
        .find((c) => !hits(c.b));
      if (!spot) { t.remove(); continue; }
      t.attr('x', px + spot.dx).attr('y', py + spot.dy);
      boxes.push(spot.b);
    }
    pts.on('pointerenter', (ev, r) => {
      tip.replaceChildren();
      const head = document.createElement('div'); const b = document.createElement('b'); b.textContent = full(r.arm); head.append(b);
      const sub = document.createElement('div'); sub.className = 'hb-sub'; sub.textContent = `${MAKER(r.vendor)} · ${r.records} записей` + (r.runs > 1 ? ` · среднее ${r.runs} прогонов` : '');
      const iv = r.lohi ? `, интервал ${RU.format('.1f')(r.lohi[0])}-${RU.format('.1f')(r.lohi[1])}` : '';
      const lr = document.createElement('div'); lr.textContent = `${RU.format('.2f')(r.silent)}: ${AXIS[metric()]}${iv}`;
      const l0 = document.createElement('div'); l0.textContent = `${RU.format('.2f')(Number(r.errors_per_100))} всех ошибок на 100 имен`;
      const l1 = document.createElement('div'); l1.textContent = `${RU.format('.2f')(Number(r.silent_per_100))} тихих, ${RU.format('.2f')(Number(r.loud_per_100))} под вопросом`;
      const l2 = document.createElement('div'); l2.textContent = `${RU.format('.1f')(Number(r.flagged_pct))} % полей под вопросом`;
      const l3 = document.createElement('div'); l3.textContent = `${fmtUsd(r.usd)} за 100 записей`;
      tip.append(head, sub, lr, l0, l1, l2, l3); tip.hidden = false;
      const px = x(r.usd) / W * el.clientWidth, py = y(r.silent) / H * el.clientHeight;
      const tw = tip.offsetWidth;
      tip.style.left = Math.min(Math.max(0, px + 12), el.clientWidth - tw) + 'px';
      tip.style.top = Math.max(0, py - 10 - tip.offsetHeight) + 'px';
    }).on('pointerleave', () => { tip.hidden = true; });
  }

  dash.draw('n', (el) => {
    const g = dash.data('results');
    const [split, arm] = [...new URLSearchParams(el.getAttribute('data-where'))].map(([, v]) => v);
    const row = g.status === 'ok' ? g.data.find((r) => r.split === split && r.arm === arm) : null;
    el.textContent = row ? String(row.records) : '—';
  });
  dash.draw('chart-test', (el) => scatter(el, 'test'));
  dash.draw('chart-dev', (el) => scatter(el, 'dev'));

  // The table of the main set, as the page of all configurations draws it: the place among models at a level
  // (a variant of one stands unnumbered), the vendor's mark, one decimal.
  const MARK = {Claude: '<circle r="5"/>', Google: '<path d="M0,-5.5L5.5,4.5L-5.5,4.5Z"/>', OpenAI: '<rect x="-4.5" y="-4.5" width="9" height="9"/>',
    xAI: '<path d="M0,-5.5L4.5,0L0,5.5L-4.5,0Z"/>', Alibaba: '<path d="M-4.5,-1.5H-1.5V-4.5H1.5V-1.5H4.5V1.5H1.5V4.5H-1.5V1.5H-4.5Z"/>'};
  const MARK_CLASS = {Claude: 'claude', Google: 'google', OpenAI: 'openai', xAI: 'xai', Alibaba: 'alibaba'};
  dash.draw('table', (tbody) => {
    const g = dash.data('results');
    tbody.replaceChildren();
    if (g.status !== 'ok') return;
    const all = g.data.filter((r) => r.split === 'test').sort((a, b) => Number(a.silent_per_100) - Number(b.silent_per_100));
    let place = 0;
    const places = new Map(all.map((r) => [r.arm, r.arm.endsWith('-ultrahigh') ? '–' : String(++place)]));
    const cell = (text, numeric) => { const td = document.createElement('td'); if (numeric) td.className = 'n'; td.textContent = text; return td; };
    for (const r of all.filter((x) => shown(x.arm))) {
      const [model, level, ...rest] = full(r.arm).split(', ');
      const name = cell('', false);
      const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
      svg.setAttribute('class', `mark mark-${MARK_CLASS[r.vendor] || 'claude'}`); svg.setAttribute('viewBox', '-6 -6 12 12');
      svg.setAttribute('role', 'img'); svg.setAttribute('aria-label', MAKER(r.vendor)); svg.innerHTML = MARK[r.vendor] || MARK.Claude;
      name.append(svg, document.createTextNode([model, ...rest].join(', ')));
      const first = cell(places.get(r.arm), true); first.classList.add('place');
      const tr = document.createElement('tr');
      tr.append(first, name, cell(level, false), cell(RU.format('.1f')(Number(r.silent_per_100)), true),
        cell(RU.format('.1f')(Number(r.errors_per_100)), true), cell(RU.format('.1f')(Number(r.flagged_pct)) + ' %', true),
        cell(RU.format('.2f')(Number(r.usd_per_100_batch)), true), cell(String(r.runs || 1), true));
      tbody.append(tr);
    }
  });
})();
