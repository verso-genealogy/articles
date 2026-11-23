"""Builds the site into docs/ (what GitHub Pages serves), in Russian at its root and in English under en/:
the article, and the page of the interactive chart and the full table.

    uv run --no-project --with markdown python build.py

Sources: content/models.md and content/models.en.md (the article and its translation), content/img (its charts;
content/img/en holds the pictures that carry words, in English), data/arms.json (every configuration's rates, from
the benchmark's `charts data`), data/results.json (the rows of the interactive chart, from its `dashboard`),
data/main-table.json (the model names and the rows of the article's table).
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
REPO = "https://github.com/verso-genealogy/verso"
#: Where the site is served: the address a link to a page is shared with.
URL = "https://verso-genealogy.github.io/articles/"
PROFILE = "https://github.com/dmalch"
#: The date each article was published.
PUBLISHED = {"models": date(2026, 11, 23)}
#: Where an article's preview on the home page ends: a line of its own in the article's text.
CUT = "<!--more-->"
GOATCOUNTER = ""   # the site's code at goatcounter.com (<code>.goatcounter.com); empty: no counter on the pages
GITHUB_MARK = ('<svg class="gh" viewBox="0 0 16 16" aria-hidden="true"><path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59'
               '.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53'
               '.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15'
               '-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16'
               ' 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46'
               '.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z"/></svg>')
#: A vendor by the start of a run's name, and its mark: the shape and the colour the chart draws it with.
VENDORS = (("gemini", "google"), ("gpt", "openai"), ("grok", "xai"), ("qwen", "alibaba"))
MARKS = {"claude": '<circle r="5"/>', "google": '<path d="M0,-5.5L5.5,4.5L-5.5,4.5Z"/>', "openai": '<rect x="-4.5" y="-4.5" width="9" height="9"/>',
         "xai": '<path d="M0,-5.5L4.5,0L0,5.5L-4.5,0Z"/>', "alibaba": '<path d="M-4.5,-1.5H-1.5V-4.5H1.5V-1.5H4.5V1.5H1.5V4.5H-1.5V1.5H-4.5Z"/>'}
VENDOR_NAMES = {"claude": "Anthropic", "google": "Google", "openai": "OpenAI", "xai": "xAI", "alibaba": "Alibaba"}




#: What the site says in each language, and where that language's pages live (`prefix`, under the site's root).
LANGS: dict[str, dict] = {
    "ru": {
        "prefix": "", "locale": "ru_RU", "content": "models.md", "chart_page": "chart.html",
        "site": "Чтение старинных документов моделями", "nav": (("models/", "Какой моделью читать"), ("chart/", "Диаграмма и таблица")),
        "author": "Дмитрий Мальчиков", "license": "https://creativecommons.org/licenses/by/4.0/deed.ru",
        "months": ("января", "февраля", "марта", "апреля", "мая", "июня", "июля", "августа", "сентября", "октября", "ноября", "декабря"),
        "date": "{day} {month} {year}", "share": "Поделиться", "more": "Читать далее", "other": ("en", "English", "EN"),
        "theme": ("Тема", "Светлая тема", "Темная тема", "Как в системе", "Тема как в системе"),
        "foot": ('Набор взят из корпуса, записи которого хранятся как код. Инструменты для него собраны в библиотеке <a href="{repo}">verso</a>.',
                 'Текст, диаграммы и данные: © {author}, <a href="{license}" rel="license">CC BY 4.0</a>. Кадры архивных документов в лицензию не входят.'),
        "head": ("№", "Модель", "effort", "Тихих ошибок", "Всех ошибок", "Полей под вопросом", "$ за 100 записей", "Прогонов"),
        "none": "без рассуждений", "frames": ", кадры в высоком разрешении", "comma": ",", "percent": " %",
        "cover_alt": "Ревизская сказка 1850 года: дважды написано Настасья, модели читают Наталья",
        "chart_title": "Диаграмма: цена и качество чтения",
        "chart_about": "Цена и ошибки чтения для каждой из конфигураций LLM: диаграмма с фильтрами и полная таблица.",
        "embed_note": ('Каждая точка это конфигурация: правее дороже, выше больше ошибок. Наведите на точку, чтобы увидеть числа,\n'
                       'кнопками выберите модели и меру. Здесь все {n} конфигурации; та же диаграмма с отладочной выборкой и таблицей\n'
                       'стоит <a href="../chart/">на отдельной странице</a>.'),
        "embed_alt": "Цена и тихие ошибки: все конфигурации",
        "moved": "Таблица теперь стоит на странице диаграммы",
    },
    "en": {
        "prefix": "en/", "locale": "en_US", "content": "models.en.md", "chart_page": "chart.en.html",
        "site": "How models read old documents", "nav": (("models/", "Which model to read with"), ("chart/", "Chart and table")),
        "author": "Dmitry Malchikov", "license": "https://creativecommons.org/licenses/by/4.0/",
        "months": ("January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"),
        "date": "{day} {month} {year}", "share": "Share", "more": "Read more", "other": ("ru", "Русский", "RU"),
        "theme": ("Theme", "Light theme", "Dark theme", "As the system", "Theme as the system has it"),
        "foot": ('The set comes from a corpus whose records are stored as code. The tools for it are collected in the <a href="{repo}">verso</a> library.',
                 'Text, charts and data: © {author}, <a href="{license}" rel="license">CC BY 4.0</a>. The frames of archival documents are not covered by the licence.'),
        "head": ("#", "Model", "effort", "Silent errors", "All errors", "Flagged fields", "$ per 100 records", "Runs"),
        "none": "no reasoning", "frames": ", high-resolution frames", "comma": ".", "percent": "%",
        "cover_alt": "A revision list of 1850: Nastasya is written twice, the models read Natalya",
        "chart_title": "Chart: price and reading quality",
        "chart_about": "Price and reading errors for every LLM configuration: a chart with filters and the full table.",
        "embed_note": ('Each point is a configuration: further right is more expensive, higher is more errors. Hover over a point to see the numbers,\n'
                       'use the buttons to choose the models and the measure. All {n} configurations are here; the same chart with the debug sample\n'
                       'and the table is <a href="../chart/">on a separate page</a>.'),
        "embed_alt": "Price and silent errors: all configurations",
        "moved": "",
    },
}


def mark(run: str) -> str:
    vendor = next((name for prefix, name in VENDORS if run.startswith(prefix)), "claude")
    return (f'<svg class="mark mark-{vendor}" viewBox="-6 -6 12 12" role="img" aria-label="{VENDOR_NAMES[vendor]}">'
            f"<title>{VENDOR_NAMES[vendor]}</title>{MARKS[vendor]}</svg>")


def num(value: float, lang: str, digits: int = 1) -> str:
    """A figure as the language prints it: a decimal comma in Russian, a point in English."""
    return f"{value + 1e-9:.{digits}f}".replace(".", LANGS[lang]["comma"])


def up(lang: str, depth: int) -> str:
    """From a page `depth` folders deep in its language's part of the site, the way up to the site's root."""
    return "../" * (depth + LANGS[lang]["prefix"].count("/"))


def picture(name: str, lang: str) -> str:
    """A picture's path under the site's root: the language's own copy where it has one (a chart's words)."""
    own = f"img/{lang}/{name}"
    return own if (ROOT / "content" / own).exists() else f"img/{name}"


def theme_switch(lang: str) -> str:
    """The theme switch in the header: light, dark, as the system has it (theme.js keeps the choice)."""
    group, light, dark, system, system_label = LANGS[lang]["theme"]
    return (f'<div class="theme" role="group" aria-label="{group}">'
            f'<button type="button" data-theme="light" aria-pressed="false" title="{light}" aria-label="{light}">'
            '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></svg></button>'
            f'<button type="button" data-theme="dark" aria-pressed="false" title="{dark}" aria-label="{dark}">'
            '<svg viewBox="0 0 24 24"><path d="M20 14.5A8 8 0 1 1 9.5 4a6.5 6.5 0 0 0 10.5 10.5z"/></svg></button>'
            f'<button type="button" data-theme="" aria-pressed="true" title="{system}" aria-label="{system_label}">'
            '<svg viewBox="0 0 24 24"><rect x="3" y="4" width="18" height="12" rx="2"/><path d="M8 20h8M12 16v4"/></svg></button></div>')


def counter() -> str:
    """The visit counter's script (GoatCounter: no cookies); nothing until the site has a code."""
    if not GOATCOUNTER:
        return ""
    return f'<script data-goatcounter="https://{GOATCOUNTER}.goatcounter.com/count" async src="https://gc.zgo.at/count.js"></script>\n'


def page(title: str, body: str, lang: str, depth: int, *, here: str = "", wide: bool = False, extra_head: str = "") -> str:
    """A page of the site in `lang`; `here` is its path within the language's part ("" the home page)."""
    words = LANGS[lang]
    root = up(lang, depth)
    home = root + words["prefix"]
    nav = "".join(f'<a href="{home}{href}"{" aria-current=\"page\"" if href == here else ""}>{html.escape(label)}</a>'
                  for href, label in words["nav"])
    other, other_name, other_short = words["other"]
    switch = (f'<a class="lang" href="{root}{LANGS[other]["prefix"]}{here}" hreflang="{other}" lang="{other}" '
              f'title="{other_name}" aria-label="{other_name}">{other_short}</a>')
    alternates = "".join(f'<link rel="alternate" hreflang="{code}" href="{URL}{LANGS[code]["prefix"]}{here}">\n' for code in LANGS)
    foot = "".join(f"<p>{line}</p>" for line in words["foot"]).format(repo=REPO, author=html.escape(words["author"]), license=words["license"])
    return f"""<!doctype html>
<html lang="{lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<script>try{{var t=localStorage.getItem("theme");if(t==="light"||t==="dark")document.documentElement.dataset.theme=t}}catch(e){{}}</script>
<link rel="license" href="{words["license"]}">
{alternates}<link rel="stylesheet" href="{root}assets/site.css">
{extra_head}{counter()}</head>
<body>
<header class="site-head">
  <a class="site-name" href="{home or "./"}">{html.escape(words["site"])}</a>
  <nav>{nav}<a href="{REPO}">verso</a></nav>
  <div class="tools">{switch}{theme_switch(lang)}</div>
</header>
<main class="{'wide' if wide else 'text'}">
{body}
</main>
<footer class="site-foot">{foot}</footer>
<script src="{root}assets/theme.js"></script>
</body>
</html>
"""


def byline(name: str, slug: str, title: str, lang: str) -> str:
    """The author, linked to his profile, the date of the article, and the button that shares the article."""
    words = LANGS[lang]
    day = PUBLISHED[name]
    when = words["date"].format(day=day.day, month=words["months"][day.month - 1], year=day.year)
    button = (f'<button type="button" class="share" aria-haspopup="menu" aria-expanded="false" '
              f'data-url="{URL}{words["prefix"]}{slug}/" data-title="{html.escape(title)}">{words["share"]}</button>')
    return (f'<div class="byline"><a class="author" href="{PROFILE}">{GITHUB_MARK}{html.escape(words["author"])}</a>'
            f'<time datetime="{day.isoformat()}">{when}</time>{button}</div>')


def summary(text: str) -> str:
    """An article's first paragraph as plain text: what a shared link shows under its title."""
    first = next(b for b in text.split("\n\n")[1:] if b.strip() and not b.startswith(("#", "!", "{{", "<!--")))
    return re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", first).replace("**", "").replace("*", "").strip()


def meta(title: str, description: str, path: str, lang: str, published: date | None = None) -> str:
    """What a link to the page shows when shared: its title, its first lines, its address, the cover."""
    words = LANGS[lang]
    address = URL + words["prefix"] + path
    tags = [("og:type", "article" if published else "website"), ("og:title", title), ("og:description", description),
            ("og:url", address), ("og:site_name", words["site"]), ("og:locale", words["locale"])]
    tags += [("og:image", URL + picture("cover.jpg", lang)), ("og:image:width", "1200"), ("og:image:height", "675"),
             ("og:image:alt", words["cover_alt"])]
    if published:
        tags.append(("article:published_time", published.isoformat()))
    out = "".join(f'<meta property="{k}" content="{html.escape(v)}">\n' for k, v in tags)
    return (out + f'<meta name="description" content="{html.escape(description)}">\n'
            f'<meta name="author" content="{html.escape(words["author"])}">\n<meta name="twitter:card" content="summary_large_image">\n'
            f'<link rel="canonical" href="{address}">\n')


def configurations(lang: str = "ru") -> list[dict]:
    """Every configuration: its name, its rates — the mean of its runs where it was read more than once."""
    words = LANGS[lang]
    data = json.loads((ROOT / "data/arms.json").read_text(encoding="utf-8"))
    names = json.loads((ROOT / "data/main-table.json").read_text(encoding="utf-8"))["names"]
    out = []
    for run, arm in data["arms"].items():
        media = run.endswith("-ultrahigh")
        model, _, effort = run.removesuffix("-ultrahigh").rpartition("-")
        pooled = data.get("twice", {}).get(run)
        rates = pooled or arm
        out.append({"run": run, "variant": media,
                    "model": names.get(model, model) + (words["frames"] if media else ""),
                    "effort": words["none"] if effort in ("none", "off") else effort,
                    "silent": rates["silent"], "all": rates["all"], "flagged": rates["flagged"], "cost": rates["cost"],
                    "runs": int(pooled["runs"]) if pooled else 1})
    out.sort(key=lambda a: a["silent"])
    place = 0
    for a in out:                      # the place among models at a level; a variant of one stands beside them, unnumbered
        place += not a["variant"]
        a["place"] = None if a["variant"] else place
    return out


def table(rows: list[dict], lang: str) -> str:
    """The rows as a table; the count of runs is a column only where it differs between the rows."""
    words = LANGS[lang]
    runs = len({a["runs"] for a in rows}) > 1
    head = "".join(f"<th{' class=\"n\"' if n == 0 or n > 2 else ''}>{html.escape(h)}</th>"
                   for n, h in enumerate(words["head"] if runs else words["head"][:-1]))
    body = "".join(
        "<tr>" + f'<td class="n place" data-v="{a["place"] or 999}">{a["place"] or "–"}</td>'
        + f"<td>{mark(a['run'])}{html.escape(a['model'])}</td><td>{html.escape(a['effort'])}</td>"
        + "".join(f'<td class="n" data-v="{v}">{text}</td>' for v, text in (
            (a["silent"], num(a["silent"], lang)), (a["all"], num(a["all"], lang)),
            (a["flagged"], num(a["flagged"], lang) + words["percent"]),
            (a["cost"], num(a["cost"], lang, 2)), *([(a["runs"], str(a["runs"]))] if runs else []))) + "</tr>"
        for a in rows)
    return (f'<div class="table-box"><table class="data">'
            f"<thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>")


def chart_head(lang: str, depth: int) -> str:
    return ('<script src="https://cdnjs.cloudflare.com/ajax/libs/d3/7.9.0/d3.min.js"></script>\n'
            f'<link rel="stylesheet" href="{up(lang, depth)}assets/chart.css">\n')


def chart_embed(lang: str) -> str:
    """The chart of the test set inside an article: the filters, the legend and the plot of the chart page, and
    the picture it replaces for a reader without scripts."""
    words = LANGS[lang]
    root = up(lang, 1)
    page_text = (ROOT / "static" / words["chart_page"]).read_text(encoding="utf-8")

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
<p class="hb-note">{words["embed_note"].format(n=len(configurations(lang)))}</p>
<noscript><img src="{root}{picture("cost-vs-silent.png", lang)}" alt="{words["embed_alt"]}"></noscript>
</div>
<script src="{root}assets/chart.js"></script>"""


def pictures(body: str, lang: str, depth: int) -> str:
    """An article's pictures (written `../img/<name>` in its text) as this page reaches them, each a figure."""
    root = up(lang, depth)
    body = re.sub(r'src="\.\./img/([^"]+)"', lambda m: f'src="{root}{picture(m.group(1), lang)}"', body)
    return re.sub(r'<p>(<img [^>]+>)</p>', r'<figure>\1</figure>', body)


def source(name: str, lang: str) -> tuple[str, str]:
    """An article's text in `lang` and its title."""
    text = (ROOT / "content" / (LANGS[lang]["content"] if name == "models" else f"{name}.md")).read_text(encoding="utf-8")
    return text, re.search(r"^# (.+)$", text, re.M).group(1)


def article(name: str, slug: str, lang: str) -> None:
    words = LANGS[lang]
    text, title = source(name, lang)
    main = json.loads((ROOT / "data/main-table.json").read_text(encoding="utf-8"))["main"]
    rows = [a for a in configurations(lang) if a["run"] in main]
    body = markdown.markdown(text.replace(CUT, '<div id="more"></div>'), extensions=["tables", "fenced_code"])
    body = body.replace("<p>{{TABLE}}</p>", table(rows, lang))
    charted = "<p>{{CHART}}</p>" in body
    body = body.replace("<p>{{CHART}}</p>", chart_embed(lang))
    body = re.sub(r"<table>", '<div class="table-box"><table class="data">', body).replace("</table>", "</table></div>")
    body = pictures(body, lang, 1)
    line = byline(name, slug, title, lang)
    body = body.replace("</h1>", "</h1>\n" + line, 1)
    end = f'<div class="byline byline-end">{line.split("</time>")[1].removesuffix("</div>")}</div>'
    head = meta(title, summary(text), f"{slug}/", lang, PUBLISHED[name]) + (chart_head(lang, 1) if charted else "")
    out = OUT / words["prefix"] / slug
    out.mkdir(parents=True, exist_ok=True)
    (out / "index.html").write_text(
        page(title, f"<article>{body}\n{end}</article>\n" + f'<script src="{up(lang, 1)}assets/share.js"></script>', lang, 1,
             here=f"{slug}/", extra_head=head), encoding="utf-8")


def moved(old: str, new: str) -> None:
    """A page that was folded into another: its address still leads there."""
    words = LANGS["ru"]
    target = "../" + new
    (OUT / old).mkdir(parents=True, exist_ok=True)
    (OUT / old / "index.html").write_text(f"""<!doctype html>
<html lang="ru"><head><meta charset="utf-8"><title>{html.escape(words["site"])}</title>
<meta http-equiv="refresh" content="0; url={target}"><link rel="canonical" href="{target}"></head>
<body><p><a href="{target}">{words["moved"]}</a></p></body></html>
""", encoding="utf-8")


def chart(lang: str) -> None:
    words = LANGS[lang]
    body = (ROOT / "static" / words["chart_page"]).read_text(encoding="utf-8")
    out = OUT / words["prefix"] / "chart"
    out.mkdir(parents=True, exist_ok=True)
    (out / "index.html").write_text(
        page(words["chart_title"], body + f'\n<script src="{up(lang, 1)}assets/chart.js"></script>', lang, 1, here="chart/",
             wide=True, extra_head=meta(words["chart_title"], words["chart_about"], "chart/", lang) + chart_head(lang, 1)),
        encoding="utf-8")


def home(lang: str) -> None:
    """The home page: the article's title and its opening, up to the cut, and the way on into the article."""
    words = LANGS[lang]
    text, title = source("models", lang)
    opening = text[:text.index(CUT)].split("\n", 1)[1]
    lead = pictures(markdown.markdown(opening, extensions=["tables", "fenced_code"]), lang, 0).replace('href="../', 'href="')
    body = f"""<article>
<h1><a class="title" href="models/">{html.escape(title)}</a></h1>
{byline("models", "models", title, lang)}
{lead}
<p><a class="more" href="models/#more">{words["more"]}</a></p>
</article>
<script src="{up(lang, 0)}assets/share.js"></script>"""
    out = OUT / words["prefix"]
    out.mkdir(parents=True, exist_ok=True)
    (out / "index.html").write_text(page(words["site"], body, lang, 0, extra_head=meta(words["site"], summary(text), "", lang)),
                                    encoding="utf-8")


def sitemap() -> None:
    """The pages a search engine should know, for Search Console and Yandex Webmaster: in each language the home
    page, each article (dated by its publication), the chart page; a moved page's address is left out."""
    pages = [("", max(PUBLISHED.values())), *((f"{slug}/", PUBLISHED[slug]) for slug in PUBLISHED), ("chart/", None)]
    urls = "".join(f"<url><loc>{URL}{words['prefix']}{path}</loc>{f'<lastmod>{day.isoformat()}</lastmod>' if day else ''}</url>\n"
                   for words in LANGS.values() for path, day in pages)
    (OUT / "sitemap.xml").write_text('<?xml version="1.0" encoding="UTF-8"?>\n'
                                     '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + urls + "</urlset>\n",
                                     encoding="utf-8")


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
    for lang in LANGS:
        home(lang)
        article("models", "models", lang)
        chart(lang)
    moved("table", "chart/#table")
    sitemap()
    print(f"{OUT}: {sum(1 for p in OUT.rglob('*') if p.is_file())} files")


if __name__ == "__main__":
    build()
