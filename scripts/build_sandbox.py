"""Step 1.4 + Step 2 setup: write data_manifest.json and build one isolated sandbox per run.

Each sandbox is the reproducer's whole world:
  sandbox/rN/TASK.md, methods.json, template.json, data/, out/
Data are copied, not symlinked (Windows symlinks need admin rights).

One sandbox per model (sandbox/r_opus, sandbox/r_sonnet); each is run by its own Claude Code session.

Paper A (BMC Pediatrics HFNC vs NIV): the data workbook and its Dryad README (a column dictionary
with no analysis or results) go in.
Paper B (Scientific Reports, e-cigarette vapour): see manifest_b.

Usage: python -I build_sandbox.py <work_dir> <python_exe> <paper> <run_names, comma-separated>
"""
import csv
import json
import shutil
import sys

import openpyxl
from pathlib import Path


TASK = """# Task: reproduce one results table from its methods description

You are reproducing a published results table **blind**. You get a structured description of the
methods and an empty copy of the table. You do not get the paper, its results or its code.

## Your world
Your working directory is this folder:

    {root}

Everything you need is inside it:
- `methods.json`: the methods, extracted from the paper. Each item quotes the source sentence. Items
  with `"gap": true` are places where the paper leaves a decision open.
- `template.json`: the target table. Same rows and columns as the published one, with every
  `value` and `stars` set to null.
- `data/`: the original data deposited by the authors{data_note}.

## Rules
1. Read and write **only inside this folder**. Do not open, list or search any path outside it.
   The single exception is the Python interpreter below.
2. **No web access** of any kind (no WebSearch, no WebFetch, no curl or pip downloads).
3. Do not try to find the paper, its results or the authors' code. Work from `methods.json` only.
4. Use only this interpreter, always with `-I`, passing paths as arguments:

       "{python}" -I out/repro_table.py data out

   Available packages: numpy, pandas, scipy, statsmodels, openpyxl, lmfit.
5. Where the methods are ambiguous, choose the most reasonable reading, record the choice in
   `out/assumptions.md` (one bullet per choice: the methods item id, what you chose, why, and the
   alternative you rejected), and keep going. Do not stop to ask.
6. Compute every number from the data. Do not type statistics in by hand.

## Deliverables (all in `out/`)
- `repro_table.py`: one script that reads `data/` and writes `out/filled.json`. It must run
  end-to-end from a clean `out/` folder.
- `filled.json`: a copy of `template.json` with every cell's `value` and `stars` filled. Keep the
  same keys. In each cell also add `"source": "<function or code section that produced it>"` and,
  if you changed units, `"unit"` to the unit you used. Use a number where you can; use a string such
  as "<x" or ">x" (a bound), "n.d." or "N/A" only where the methods say a value is a bound or not determined.
  Report values to at least 4 significant digits; the grader rounds.
- `run.log`: the console output of the final run (capture stdout and stderr).
- `assumptions.md`: as described in rule 5.

When done, reply with a short summary: the choices you made for each `gap: true` item and anything
you could not compute.
"""


def manifest_a(src):
    return {
        "paper": "A",
        "files": [{"name": "repository_HFNC_x_NIV.xlsx", "role": "one row per analysed patient (252)", "given_to_reproducer": True},
                  {"name": "README.md", "role": "column dictionary and coding (md, nc, pf); no results", "given_to_reproducer": True}],
        "required_inputs": [
            {"input": "Group, sex, history, viral panel, device duration, 0 h vital signs, sedation and enteral tube days, ventilation days, antibiotics, PIM 2", "availability": "full"},
            {"input": "Age, weight, PICU and hospital length of stay", "availability": "partial",
             "note": "De-identified into ranges (e.g. 6-8), so medians, IQRs, z scores and tests on them cannot be recomputed. Those rows are not graded."},
            {"input": "Ventilator-associated pneumonia", "availability": "missing"},
        ],
        "withheld_from_sandbox": [],
    }


def manifest_b(src):
    return {
        "paper": "B",
        "files": [{"name": "aorta_crc.csv",
                   "role": "raw concentration-response rows of 'Data Fig 1+Tab 2.xlsx' (sheets CSE, EVE, HTE): % of precontraction remaining per experiment",
                   "given_to_reproducer": True}],
        "required_inputs": [
            {"input": "Rat aorta relaxation to acetylcholine and DEA/NO, 5 experiments per treatment, 9 concentrations", "availability": "full"},
        ],
        "withheld_from_sandbox": [
            {"name": "rows 'EC50 (mol/l)', 'Emax (%)', 'CI', 'logEC50', 'MW' under each block", "reason": "authors' fitted EC50/Emax per experiment, their means and CIs: the published values"},
            {"name": "columns 'Mittel' and 'SEM'", "reason": "authors' summaries of the curves"},
            {"name": "Data Fig 2+Tab 2.xlsx, Data Fig 3-7 workbooks", "reason": "other figures and Table 3, not needed for Table 2"},
        ],
    }


CONC = {"nM": 1e-9, "µM": 1e-6, "uM": 1e-6}


def export_b(src, dest):
    """Keep only the raw concentration rows (5 experiment columns per agonist) of each treatment block."""
    wb = openpyxl.load_workbook(src / "Data Fig 1+Tab 2.xlsx", data_only=True)
    with open(dest / "aorta_crc.csv", "w", newline="", encoding="utf-8") as f:
        out = csv.writer(f)
        out.writerow(["extract", "treatment", "agonist", "conc_M", "experiment", "pct_of_precontraction"])
        for ws in wb.worksheets:
            rows = list(ws.iter_rows(values_only=True))
            for i, r in enumerate(rows):
                if not any(isinstance(v, str) and "% of B" in v for v in r):
                    continue
                treatment = next(v for v in rows[i - 2] if isinstance(v, str)).strip()
                for row in rows[i + 1:]:
                    label = row[0]
                    if not (isinstance(label, str) and label.split()[-1] in CONC):
                        break
                    for agonist, start in (("acetylcholine", 1), ("DEA/NO", 14)):
                        lab = row[start - 1]
                        molar = float(lab.split()[0]) * CONC[lab.split()[-1]]
                        for e in range(5):
                            v = row[start + e]
                            out.writerow([ws.title, treatment, agonist, f"{molar:g}", e + 1, "" if v is None else v])


MANIFESTS = {"paperA": manifest_a, "paperB": manifest_b}
DATA = {"paperA": (["repository_HFNC_x_NIV.xlsx", "README.md"],
                   " (one Excel workbook, one row per analysed patient, plus README.md explaining every column and code)"),
        "paperB": (export_b,
                   " (one CSV, aorta_crc.csv: for each extract group (CSE, EVE, HTE) and treatment as labelled in the "
                   "deposit, the tension remaining as % of the U-46619 precontraction at each agonist concentration, "
                   "for each of 5 experiments)")}


def main(work, python, paper, runs):
    base = Path(work).resolve() / paper
    src = base / "source" / "data"
    (base / "extract" / "data_manifest.json").write_text(json.dumps(MANIFESTS[paper](src), indent=1, ensure_ascii=False), encoding="utf-8")
    files, note = DATA[paper]
    for run in runs.split(","):
        root = base / "sandbox" / run
        if root.exists():
            shutil.rmtree(root)
        (root / "data").mkdir(parents=True)
        (root / "out").mkdir()
        shutil.copy(base / "extract" / "template.json", root / "template.json")
        methods = json.loads((base / "extract" / "methods.json").read_text(encoding="utf-8"))
        methods.pop("citation", None)  # no title/DOI of the paper inside the sandbox
        (root / "methods.json").write_text(json.dumps(methods, indent=2, ensure_ascii=False), encoding="utf-8")
        if callable(files):
            files(src, root / "data")
        else:
            for f in files:
                shutil.copy(src / f, root / "data" / f)
        (root / "TASK.md").write_text(TASK.format(root=root, python=python, data_note=note), encoding="utf-8")
        print("built", root)


if __name__ == "__main__":
    main(*sys.argv[1:])
