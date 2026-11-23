"""Builds the site into docs/ (what GitHub Pages serves): the article, the full table, the interactive chart.

    uv run --no-project --with markdown python build.py

Sources: content/models.md (the article), content/img (its charts), data/arms.json (every configuration's
rates, from the benchmark's `charts data`), data/results.json (the rows of the interactive chart, from its
`dashboard`), data/main-table.json (the model names and the rows of the first article's table).
"""
from __future__ import annotations

import html
import json
import re
import shutil
from pathlib import Path

import markdown

ROOT = Path(__file__).parent
OUT = ROOT / "docs"
SITE = "Чтение старинных документов моделями"
NAV = (("models/", "Какой моделью читать"), ("chart/", "Диаграмма"), ("table/", "Все конфигурации"))
REPO = "https://github.com/verso-genealogy/verso"
#: Where an article's preview on the home page ends: a line of its own in the article's text.
CUT = "<!--more-->"
HEAD = ("№", "Модель", "effort", "Тихих ошибок", "Всех ошибок", "Полей под вопросом", "$ за 100 записей", "Прогонов")
#: A vendor by the start of a run's name, and its mark: the shape and the colour the chart draws it with.
VENDORS = (("gemini", "google"), ("gpt", "openai"), ("grok", "xai"), ("qwen", "alibaba"))
MARKS = {"claude": '<circle r="5"/>', "google": '<path d="M0,-5.5L5.5,4.5L-5.5,4.5Z"/>', "openai": '<rect x="-4.5" y="-4.5" width="9" height="9"/>',
         "xai": '<path d="M0,-5.5L4.5,0L0,5.5L-4.5,0Z"/>', "alibaba": '<path d="M-4.5,-1.5H-1.5V-4.5H1.5V-1.5H4.5V1.5H1.5V4.5H-1.5V1.5H-4.5Z"/>'}
VENDOR_NAMES = {"claude": "Anthropic", "google": "Google", "openai": "OpenAI", "xai": "xAI", "alibaba": "Alibaba"}


def mark(run: str) -> str:
    vendor = next((name for prefix, name in VENDORS if run.startswith(prefix)), "claude")
    return (f'<svg class="mark mark-{vendor}" viewBox="-6 -6 12 12" role="img" aria-label="{VENDOR_NAMES[vendor]}">'
            f"<title>{VENDOR_NAMES[vendor]}</title>{MARKS[vendor]}</svg>")


def ru(value: float, digits: int = 1) -> str:
    return f"{value + 1e-9:.{digits}f}".replace(".", ",")


def page(title: str, body: str, depth: int, *, here: str = "", wide: bool = False, extra_head: str = "") -> str:
    up = "../" * depth
    nav = "".join(f'<a href="{up}{href}"{" aria-current=\"page\"" if href == here else ""}>{html.escape(label)}</a>'
                  for href, label in NAV)
    return f"""<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<link rel="stylesheet" href="{up}assets/site.css">
{extra_head}</head>
<body>
<header class="site-head">
  <a class="site-name" href="{up}">{html.escape(SITE)}</a>
  <nav>{nav}<a href="{REPO}">verso</a></nav>
</header>
<main class="{'wide' if wide else 'text'}">
{body}
</main>
<footer class="site-foot">Набор взят из корпуса, записи которого хранятся как код. Инструменты для него собраны в библиотеке <a href="{REPO}">verso</a>.</footer>
</body>
</html>
"""


def configurations() -> list[dict]:
    """Every configuration: its name, its rates — the mean of its runs where it was read more than once."""
    data = json.loads((ROOT / "data/arms.json").read_text(encoding="utf-8"))
    names = json.loads((ROOT / "data/main-table.json").read_text(encoding="utf-8"))["names"]
    out = []
    for run, arm in data["arms"].items():
        media = run.endswith("-ultrahigh")
        model, _, effort = run.removesuffix("-ultrahigh").rpartition("-")
        pooled = data.get("twice", {}).get(run)
        rates = pooled or arm
        out.append({"run": run, "variant": media,
                    "model": names.get(model, model) + (", кадры в высоком разрешении" if media else ""),
                    "effort": "без рассуждений" if effort in ("none", "off") else effort,
                    "silent": rates["silent"], "all": rates["all"], "flagged": rates["flagged"], "cost": rates["cost"],
                    "runs": int(pooled["runs"]) if pooled else 1})
    out.sort(key=lambda a: a["silent"])
    place = 0
    for a in out:                      # the place among models at a level; a variant of one stands beside them, unnumbered
        place += not a["variant"]
        a["place"] = None if a["variant"] else place
    return out


def table(rows: list[dict], *, ident: str = "") -> str:
    """The rows as a table; the count of runs is a column only where it differs between the rows."""
    runs = len({a["runs"] for a in rows}) > 1
    head = "".join(f"<th{' class=\"n\"' if n == 0 or n > 2 else ''}>{html.escape(h)}</th>"
                   for n, h in enumerate(HEAD if runs else HEAD[:-1]))
    body = "".join(
        "<tr>" + f'<td class="n place" data-v="{a["place"] or 999}">{a["place"] or "–"}</td>'
        + f"<td>{mark(a['run'])}{html.escape(a['model'])}</td><td>{html.escape(a['effort'])}</td>"
        + "".join(f'<td class="n" data-v="{v}">{text}</td>' for v, text in (
            (a["silent"], ru(a["silent"])), (a["all"], ru(a["all"])), (a["flagged"], ru(a["flagged"]) + " %"),
            (a["cost"], ru(a["cost"], 2)), *([(a["runs"], str(a["runs"]))] if runs else []))) + "</tr>"
        for a in rows)
    return (f'<div class="table-box"><table{f" id={ident!r}" if ident else ""} class="data">'
            f"<thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>")


CHART_HEAD = ('<script src="https://cdnjs.cloudflare.com/ajax/libs/d3/7.9.0/d3.min.js"></script>\n'
              '<link rel="stylesheet" href="../assets/chart.css">\n')


def chart_embed() -> str:
    """The chart of the test set inside an article: the filters, the legend and the plot of the chart page, and
    the picture it replaces for a reader without scripts."""
    page_text = (ROOT / "static/chart.html").read_text(encoding="utf-8")

    def block(start: str, end: str) -> str:
        i = page_text.index(start)
        return page_text[i:page_text.index(end, i) + len(end)]

    filters = block('<div class="hb-filter" id="filter"', "</div>") + "\n" + block('<div class="hb-filter" id="metric"', "</div>")
    legend = block('<div class="hb-legend" id="legend-test"', "</div>")
    return f"""<div class="hb hb-embed">
{filters}
<div class="hb-card">
{legend}
<div class="hb-chart dash-skeleton" data-draw="chart-test" data-source="results"></div>
</div>
<p class="hb-note">Каждая точка это конфигурация: правее дороже, выше больше ошибок. Наведите на точку, чтобы увидеть числа,
кнопками выберите модели и меру. Здесь все {len(configurations())} конфигурации; та же диаграмма с отладочной выборкой и таблицей
стоит <a href="../chart/">на отдельной странице</a>.</p>
<noscript><img src="../img/cost-vs-silent.png" alt="Цена и тихие ошибки: все конфигурации"></noscript>
</div>
<script src="../assets/chart.js"></script>"""


def article(name: str, slug: str) -> None:
    text = (ROOT / "content" / f"{name}.md").read_text(encoding="utf-8")
    main = json.loads((ROOT / "data/main-table.json").read_text(encoding="utf-8"))["main"]
    rows = [a for a in configurations() if a["run"] in main]
    title = re.search(r"^# (.+)$", text, re.M).group(1)
    body = markdown.markdown(text.replace(CUT, '<div id="more"></div>'), extensions=["tables", "fenced_code"])
    body = body.replace("<p>{{TABLE}}</p>", table(rows))
    charted = "<p>{{CHART}}</p>" in body
    body = body.replace("<p>{{CHART}}</p>", chart_embed())
    body = re.sub(r"<table>", '<div class="table-box"><table class="data">', body).replace("</table>", "</table></div>")
    body = re.sub(r'<p>(<img [^>]+>)</p>', r'<figure>\1</figure>', body)
    (OUT / slug).mkdir(parents=True, exist_ok=True)
    (OUT / slug / "index.html").write_text(
        page(title, f"<article>{body}</article>", 1, here=f"{slug}/", extra_head=CHART_HEAD if charted else ""), encoding="utf-8")


def full_table() -> None:
    rows = configurations()
    body = f"""<h1>Все конфигурации</h1>
<p class="lead">{len(rows)} конфигураций на 167 записях. Ошибки на 100 полей имен (имя, отчество, фамилия). Тихая ошибка: неверное имя,
которое модель не поставила под вопрос. Цена: чтение 100 записей через пакетный API по ноябрьским ценам. Там, где
конфигурация прочитана дважды, стоит среднее двух прогонов. Заголовок столбца сортирует таблицу.</p>
{table(rows, ident="all")}
<script src="../assets/sort.js"></script>"""
    (OUT / "table").mkdir(parents=True, exist_ok=True)
    (OUT / "table" / "index.html").write_text(page("Все конфигурации", body, 1, here="table/", wide=True), encoding="utf-8")


def chart() -> None:
    body = (ROOT / "static/chart.html").read_text(encoding="utf-8")
    (OUT / "chart").mkdir(parents=True, exist_ok=True)
    (OUT / "chart" / "index.html").write_text(
        page("Диаграмма: цена и качество чтения", body + '\n<script src="../assets/chart.js"></script>', 1, here="chart/",
             wide=True, extra_head=CHART_HEAD), encoding="utf-8")


def home() -> None:
    """The home page: the article's title and its opening, up to the cut, and the way on into the article."""
    text = (ROOT / "content/models.md").read_text(encoding="utf-8")
    title = re.search(r"^# (.+)$", text, re.M).group(1)
    opening = text[:text.index(CUT)].split("\n", 1)[1].replace("](../", "](")
    body = f"""<article>
<h1><a class="title" href="models/">{html.escape(title)}</a></h1>
{markdown.markdown(opening, extensions=["tables", "fenced_code"])}
<p><a class="more" href="models/#more">Читать далее</a></p>
</article>"""
    (OUT / "index.html").write_text(page(SITE, body, 0), encoding="utf-8")


def build() -> None:
    if OUT.exists():
        shutil.rmtree(OUT)
    (OUT / "assets").mkdir(parents=True)
    for name in ("site.css", "chart.css", "chart.js", "sort.js"):
        shutil.copy(ROOT / "static" / name, OUT / "assets" / name)
    shutil.copytree(ROOT / "content/img", OUT / "img")
    (OUT / "data").mkdir()
    shutil.copy(ROOT / "data/results.json", OUT / "data/results.json")
    (OUT / ".nojekyll").write_text("", encoding="utf-8")
    home()
    article("models", "models")
    full_table()
    chart()
    print(f"{OUT}: {sum(1 for p in OUT.rglob('*') if p.is_file())} files")


if __name__ == "__main__":
    build()
