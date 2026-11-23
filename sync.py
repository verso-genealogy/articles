"""Brings the site's numbers and charts up to date from the corpus's checkout and the benchmark's report, then `build.py`.

    python sync.py CORPUS_CHECKOUT BENCH_SET_DIR

CORPUS_CHECKOUT/docs/articles/img holds the charts and arms.json; BENCH_SET_DIR/report holds dashboard.json.
Only what the article is about is taken: a model at a level of effort. Runs made under another condition
(a context in the prompt, a changed prompt, another route) stay out, and so does everything but the rates.
The article, content/models.md, is the author's text and is edited here by hand: only its table is drawn
from the data.
"""
import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).parent
CHARTS = ("leaders", "leaders-price", "leaders-flagged", "effort-levels", "generations", "cost-vs-silent")
OTHER_CONDITION = re.compile(r"-(e\d+|priors|ctx|places|example|people\d+|openrouter|noblank)(-r\d+)?$")


def main(corpus: Path, bench: Path) -> None:
    img = corpus / "docs/articles/img"
    for name in CHARTS:
        shutil.copy(img / f"{name}.png", ROOT / "content/img" / f"{name}.png")
    arms = json.loads((img / "arms.json").read_text(encoding="utf-8"))
    kept = {"records": arms["records"], "arms": arms["arms"], "twice": arms.get("twice", {})}
    (ROOT / "data/arms.json").write_text(json.dumps(kept, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    rows = json.loads((bench / "report/dashboard.json").read_text(encoding="utf-8"))
    rows = [r for r in rows if not OTHER_CONDITION.search(r["arm"])]
    (ROOT / "data/results.json").write_text(json.dumps(rows, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]))
