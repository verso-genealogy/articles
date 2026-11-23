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
HEAD = ("Модель", "effort", "Тихих ошибок", "Всех ошибок", "Полей под вопросом", "$ за 100 записей", "Прогонов")


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
        out.append({"run": run, "model": names.get(model, model) + (", кадры в высоком разрешении" if media else ""),
                    "effort": "без рассуждений" if effort in ("none", "off") else effort,
                    "silent": rates["silent"], "all": rates["all"], "flagged": rates["flagged"], "cost": rates["cost"],
                    "runs": int(pooled["runs"]) if pooled else 1})
    return sorted(out, key=lambda a: a["silent"])


def table(rows: list[dict], *, ident: str = "") -> str:
    head = "".join(f"<th{' class=\"n\"' if n > 1 else ''}>{html.escape(h)}</th>" for n, h in enumerate(HEAD))
    body = "".join(
        "<tr>" + f"<td>{html.escape(a['model'])}</td><td>{html.escape(a['effort'])}</td>"
        + "".join(f'<td class="n" data-v="{v}">{text}</td>' for v, text in (
            (a["silent"], ru(a["silent"])), (a["all"], ru(a["all"])), (a["flagged"], ru(a["flagged"]) + " %"),
            (a["cost"], ru(a["cost"], 2)), (a["runs"], str(a["runs"])))) + "</tr>"
        for a in rows)
    return (f'<div class="table-box"><table{f" id={ident!r}" if ident else ""} class="data">'
            f"<thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>")


def article(name: str, slug: str) -> None:
    text = (ROOT / "content" / f"{name}.md").read_text(encoding="utf-8")
    main = json.loads((ROOT / "data/main-table.json").read_text(encoding="utf-8"))["main"]
    rows = [a for a in configurations() if a["run"] in main]
    title = re.search(r"^# (.+)$", text, re.M).group(1)
    body = markdown.markdown(text, extensions=["tables", "fenced_code"])
    body = body.replace("<p>{{TABLE}}</p>", table(rows))
    body = re.sub(r"<table>", '<div class="table-box"><table class="data">', body).replace("</table>", "</table></div>")
    body = re.sub(r'<p>(<img [^>]+>)</p>', r'<figure>\1</figure>', body)
    (OUT / slug).mkdir(parents=True, exist_ok=True)
    (OUT / slug / "index.html").write_text(page(title, f"<article>{body}</article>", 1, here=f"{slug}/"), encoding="utf-8")


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
    head = ('<script src="https://cdnjs.cloudflare.com/ajax/libs/d3/7.9.0/d3.min.js"></script>\n'
            '<link rel="stylesheet" href="../assets/chart.css">\n')
    (OUT / "chart").mkdir(parents=True, exist_ok=True)
    (OUT / "chart" / "index.html").write_text(
        page("Диаграмма: цена и качество чтения", body + '\n<script src="../assets/chart.js"></script>', 1, here="chart/",
             wide=True, extra_head=head), encoding="utf-8")


def home() -> None:
    best = configurations()[:3]
    cards = "".join(f'<li><b>{html.escape(a["model"])}, {html.escape(a["effort"])}</b><span>{ru(a["silent"])} тихой ошибки на 100 имен, '
                    f'${ru(a["cost"], 2)} за 100 записей</span></li>' for a in best)
    body = f"""<h1>Какой моделью читать старинные документы</h1>
<p class="lead">Замер того, как большие языковые модели читают русские метрические книги и ревизские сказки XVIII-XIX веков:
53 конфигурации, 167 записей из четырех приходов и пяти архивов, оценка по именам, отчествам и фамилиям.</p>
<ul class="best">{cards}</ul>
<div class="doors">
  <a href="models/"><b>Какой моделью читать</b><span>Статья: сравнение моделей и уровней effort, цены, выводы.</span></a>
  <a href="chart/"><b>Диаграмма</b><span>Цена против качества для каждой конфигурации, с фильтрами по моделям и мерам.</span></a>
  <a href="table/"><b>Все конфигурации</b><span>Полная таблица, сортируется по любому столбцу.</span></a>
</div>"""
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
