# Task: explain why reproduced numbers differ from the published table

Two AI runs (one Claude Opus 5.5, one Claude Sonnet 5.5) each rebuilt one published results table **blind**, from a
summary of the Methods (`extract/methods.json`) and the authors' data. A fixed script graded every cell against
the published value. You are **not** blind: your job is to find out, for every cell that missed, why it missed, and
to prove it by re-running the alternative reading.

## Where things are (paper folder = C:\Users\e417152\code\reverify_research\elsevier\work\paperB)
- `source/paper.txt`: the full paper text (Methods, Results, tables, footnotes). `source/*.pdf` is the PDF.
- `source/data/`: everything the authors deposited (including files withheld from the blind runs).
- `extract/methods.json`, `extract/template.json`: exactly what the blind runs got. `extract/tables_full.json`: published values.
- `sandbox/r_opus/out/` and `sandbox/r_sonnet/out/`: each run's `repro_table.py`, `filled.json`, `assumptions.md`, `run.log`.
- `eval/grades.json`: per-cell grades for both runs (A within 2%, B within 20%, C 20-40%, D 40-60%, E >60% or sign flipped).
- Python: `C:\Users\e417152\code\reverify_research\elsevier\.venv\Scripts\python.exe` (numpy, pandas, scipy, statsmodels, openpyxl, lmfit). Always run it with `-I`.

## What to do
1. List every graded cell that is not grade A in either run. Group them by cause: one cause usually explains many cells.
2. For each cause, find what the paper leaves open (or gets wrong), what each run did, and what the authors evidently
   did. **Test it**: write a script in `eval/explain/` that re-computes the affected cells under the alternative reading
   and shows whether it moves them to the published values. Run it and keep the output (`eval/explain/*.log`).
3. Categorise each cause as one of:
   - `Original: underspecified`: the Methods leave a choice open, and a re-run under another reasonable reading matches.
   - `Original: inconsistent`: the paper contradicts itself or its own data (e.g. a printed p-value no test on the data gives).
   - `Data: not shared`: the deposit lacks what the cell needs (e.g. values given only as ranges).
   - `Extraction`: our Methods summary lost or distorted something the paper says.
   - `Reproducer choice`: the Methods were clear and a run deviated.
   - `Unknown`: nothing you tried reproduces the published value. Say so; do not stretch a label.
   Only use `underspecified` when a re-run moves the cells to (or very near) the published values.
4. Do not modify anything outside `eval/explain/` and `eval/story.json`. Do not use the web.

## Output: `eval/story.json` (UTF-8 JSON, exactly these keys)
Write for a non-specialist reader: short sentences, plain words, no jargon without a gloss, no exclamation marks.
```json
{
  "short": "3-6 word topic of the paper, e.g. 'Laparoscopic knot-tying trial'",
  "what": "One or two sentences: what the table shows, in plain words.",
  "verdict": "One sentence answering 'could the table be rebuilt from the Methods and data?' that holds for both runs.",
  "verdict_note": "One or two sentences on where the differences come from.",
  "implication": "One or two sentences: what this means for the journal/publisher (e.g. which sentence in the Methods would have prevented most misses).",
  "model_note": "One or two sentences comparing the Opus and Sonnet runs: where they made different choices and what that did. Be fair: one run per model, so a difference can be chance.",
  "headline_cause": "id of the single most instructive cause (the 'moment it went wrong')",
  "causes": [
    {
      "id": "c1",
      "title": "Short plain title",
      "category": "Original: underspecified",
      "cells": {"r_opus": ["row|col", "..."], "r_sonnet": ["row|col", "..."]},
      "left_unsaid": "What the paper leaves open or gets wrong.",
      "ai_did": {"r_opus": "What the Opus run did.", "r_sonnet": "What the Sonnet run did."},
      "authors_did": "What the authors evidently did (or 'Unknown').",
      "fix": "The one sentence that, added to the Methods, would have prevented it (or the correction needed).",
      "evidence": "What your re-run showed, with numbers (e.g. 'arithmetic means give 386.6 / 279.5 / 255.7, the published values').",
      "example": {"cell": "row|col", "published": "386.6", "ai": {"r_opus": "328.9", "r_sonnet": "382.3"}, "alternative": "386.6"},
      "script": "eval/explain/<file>.py"
    }
  ],
  "notes": ["Other observations worth one line each (e.g. a contradiction in the paper's text)."]
}
```
Every non-A cell of each run must appear in exactly one cause's `cells` list for that run. Cells that are B only through
rounding of a correct method may share one cause titled e.g. "Small rounding and fitting differences".

When done, reply with a short summary of the causes and how many cells each explains.
