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
#: Runs of the debug sample that did not answer: nearly every reply was cut at the length limit of the answer
#: (5, 12, 2 and 0 records of 20 answered), so their points say nothing of reading.
CUT_SHORT = {("dev", "gemini-4-carbon-high"), ("dev", "gemini-4-neon-high"), ("dev", "gemini-4-neon-xhigh"),
             ("dev", "gemini-4-hydrogen-xhigh")}


def main(corpus: Path, bench: Path) -> None:
    img = corpus / "docs/articles/img"
    for name in CHARTS:
        shutil.copy(img / f"{name}.png", ROOT / "content/img" / f"{name}.png")
    arms = json.loads((img / "arms.json").read_text(encoding="utf-8"))
    kept = {"records": arms["records"], "arms": arms["arms"], "twice": arms.get("twice", {})}
    (ROOT / "data/arms.json").write_text(json.dumps(kept, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    rows = json.loads((bench / "report/dashboard.json").read_text(encoding="utf-8"))
    rows = [r for r in rows if not OTHER_CONDITION.search(r["arm"]) and (r["split"], r["arm"]) not in CUT_SHORT]
    for r in rows:                      # a configuration read more than once stands as the mean of its runs, as in the tables
        pooled = kept["twice"].get(r["arm"]) if r["split"] == "test" else None
        if pooled:
            r.update(silent_per_100=round(pooled["silent"], 2), errors_per_100=round(pooled["all"], 2),
                     loud_per_100=round(pooled["all"] - pooled["silent"], 2), review_per_100=round(pooled["review"], 2),
                     flagged_pct=round(pooled["flagged"], 1), usd_per_100_batch=round(pooled["cost"], 3),
                     silent_ci=[round(pooled["lo"], 2), round(pooled["hi"], 2)],
                     errors_ci=[round(pooled["all_lo"], 2), round(pooled["all_hi"], 2)],
                     review_ci=[round(pooled["review_lo"], 2), round(pooled["review_hi"], 2)], runs=int(pooled["runs"]))
    (ROOT / "data/results.json").write_text(json.dumps(rows, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]))
