"""Builds the site into docs/ (what GitHub Pages serves): the article and the page of the interactive chart and the full table.

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
from datetime import date
from pathlib import Path

import markdown

ROOT = Path(__file__).parent
OUT = ROOT / "docs"
SITE = "Чтение старинных документов моделями"
NAV = (("models/", "Какой моделью читать"), ("chart/", "Диаграмма и таблица"))
REPO = "https://github.com/verso-genealogy/verso"
#: Where the site is served: the address a link to a page is shared with.
URL = "https://verso-genealogy.github.io/articles/"
AUTHOR = ("Дмитрий Мальчиков", "https://github.com/dmalch")
#: The date each article was published.
PUBLISHED = {"models": date(2026, 11, 23)}
MONTHS = ("января", "февраля", "марта", "апреля", "мая", "июня", "июля", "августа", "сентября", "октября", "ноября", "декабря")
GITHUB_MARK = ('<svg class="gh" viewBox="0 0 16 16" aria-hidden="true"><path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59'
               '.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53'
               '.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15'
               '-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16'
               ' 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46'
               '.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z"/></svg>')
#: The theme switch in the header: light, dark, as the system has it (theme.js keeps the choice).
THEME = ('<div class="theme" role="group" aria-label="Тема">'
         '<button type="button" data-theme="light" aria-pressed="false" title="Светлая тема" aria-label="Светлая тема">'
         '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></svg></button>'
         '<button type="button" data-theme="dark" aria-pressed="false" title="Темная тема" aria-label="Темная тема">'
         '<svg viewBox="0 0 24 24"><path d="M20 14.5A8 8 0 1 1 9.5 4a6.5 6.5 0 0 0 10.5 10.5z"/></svg></button>'
         '<button type="button" data-theme="" aria-pressed="true" title="Как в системе" aria-label="Тема как в системе">'
         '<svg viewBox="0 0 24 24"><rect x="3" y="4" width="18" height="12" rx="2"/><path d="M8 20h8M12 16v4"/></svg></button></div>')
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
<script>try{{var t=localStorage.getItem("theme");if(t==="light"||t==="dark")document.documentElement.dataset.theme=t}}catch(e){{}}</script>
<link rel="stylesheet" href="{up}assets/site.css">
{extra_head}</head>
<body>
<header class="site-head">
  <a class="site-name" href="{up}">{html.escape(SITE)}</a>
  <nav>{nav}<a href="{REPO}">verso</a></nav>
  {THEME}
</header>
<main class="{'wide' if wide else 'text'}">
{body}
</main>
<footer class="site-foot">Набор взят из корпуса, записи которого хранятся как код. Инструменты для него собраны в библиотеке <a href="{REPO}">verso</a>.</footer>
<script src="{up}assets/theme.js"></script>
</body>
</html>
"""


def byline(name: str, *, share: bool) -> str:
    """The author, linked to his profile, the date of the article, and (on the article itself) the share button."""
    day = PUBLISHED[name]
    button = ('<button type="button" class="share" aria-haspopup="menu" aria-expanded="false">Поделиться</button>'
              if share else "")
    return (f'<div class="byline"><a class="author" href="{AUTHOR[1]}">{GITHUB_MARK}{html.escape(AUTHOR[0])}</a>'
            f'<time datetime="{day.isoformat()}">{day.day} {MONTHS[day.month - 1]} {day.year}</time>{button}</div>')


def summary(text: str) -> str:
    """An article's first paragraph as plain text: what a shared link shows under its title."""
    first = next(b for b in text.split("\n\n")[1:] if b.strip() and not b.startswith(("#", "!", "{{", "<!--")))
    return re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", first).replace("**", "").replace("*", "").strip()


def meta(title: str, description: str, path: str, published: date | None = None) -> str:
    """What a link to the page shows when shared: its title, its first lines, its address."""
    tags = [("og:type", "article" if published else "website"), ("og:title", title), ("og:description", description),
            ("og:url", URL + path), ("og:site_name", SITE), ("og:locale", "ru_RU")]
    tags += [("og:image", URL + "img/cover.jpg"), ("og:image:width", "1200"), ("og:image:height", "675"),
             ("og:image:alt", "Ревизская сказка 1850 года: дважды написано Настасья, модели читают Наталья")]
    if published:
        tags.append(("article:published_time", published.isoformat()))
    out = "".join(f'<meta property="{k}" content="{html.escape(v)}">\n' for k, v in tags)
    return (out + f'<meta name="description" content="{html.escape(description)}">\n'
            f'<meta name="author" content="{html.escape(AUTHOR[0])}">\n<meta name="twitter:card" content="summary_large_image">\n'
            f'<link rel="canonical" href="{URL + path}">\n')


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


def table(rows: list[dict]) -> str:
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
    return (f'<div class="table-box"><table class="data">'
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
    body = body.replace("</h1>", "</h1>\n" + byline(name, share=True), 1)
    end = f'<div class="byline byline-end">{byline(name, share=True).split("</time>")[1].removesuffix("</div>")}</div>'
    head = meta(title, summary(text), f"{slug}/", PUBLISHED[name]) + (CHART_HEAD if charted else "")
    (OUT / slug).mkdir(parents=True, exist_ok=True)
    (OUT / slug / "index.html").write_text(
        page(title, f"<article>{body}\n{end}</article>\n" + '<script src="../assets/share.js"></script>', 1,
             here=f"{slug}/", extra_head=head), encoding="utf-8")


def moved(old: str, new: str) -> None:
    """A page that was folded into another: its address still leads there."""
    target = "../" + new
    (OUT / old).mkdir(parents=True, exist_ok=True)
    (OUT / old / "index.html").write_text(f"""<!doctype html>
<html lang="ru"><head><meta charset="utf-8"><title>{html.escape(SITE)}</title>
<meta http-equiv="refresh" content="0; url={target}"><link rel="canonical" href="{target}"></head>
<body><p><a href="{target}">Таблица теперь стоит на странице диаграммы</a></p></body></html>
""", encoding="utf-8")


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
{byline("models", share=False)}
{markdown.markdown(opening, extensions=["tables", "fenced_code"])}
<p><a class="more" href="models/#more">Читать далее</a></p>
</article>"""
    (OUT / "index.html").write_text(page(SITE, body, 0, extra_head=meta(SITE, summary(text), "")), encoding="utf-8")


def build() -> None:
    if OUT.exists():
        shutil.rmtree(OUT)
    (OUT / "assets").mkdir(parents=True)
    for name in ("site.css", "chart.css", "chart.js", "share.js", "theme.js"):
        shutil.copy(ROOT / "static" / name, OUT / "assets" / name)
    shutil.copytree(ROOT / "content/img", OUT / "img")
    (OUT / "data").mkdir()
    shutil.copy(ROOT / "data/results.json", OUT / "data/results.json")
    (OUT / ".nojekyll").write_text("", encoding="utf-8")
    home()
    article("models", "models")
    moved("table", "chart/#table")
    chart()
    print(f"{OUT}: {sum(1 for p in OUT.rglob('*') if p.is_file())} files")


if __name__ == "__main__":
    build()
