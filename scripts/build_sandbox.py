"""Step 1.4 + Step 2 setup: write data_manifest.json and build one isolated sandbox per run.

Each sandbox is the reproducer's whole world:
  sandbox/rN/TASK.md, methods.json, template.json, data/, out/
Data are copied, not symlinked (Windows symlinks need admin rights).

Paper B: the Dryad workbook also holds the authors' GraphPad Prism outputs (fitted
pEC50/Emax/Hill and ANOVA tabs) and a README describing those analyses. Those are the
answers, so only the raw concentration-response tabs are exported to the sandbox, as CSV.

Usage: python -I build_sandbox.py <work_dir> <python_exe> <n_runs>
"""
import csv
import json
import shutil
import sys
from pathlib import Path

import openpyxl

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
        "files": [{"name": "LGMD+R9+Murphy+Annals+Clin+Trans+Neurol+2019+public+200319.xlsx",
                   "role": "per-participant baseline (B) and 6-year (F) values for every Table 1 row",
                   "given_to_reproducer": True}],
        "required_inputs": [
            {"input": "FVC sitting/lying B and F (%)", "availability": "full"},
            {"input": "Myometry B and F (kg), incl. hip flexion", "availability": "full"},
            {"input": "Timed-test velocities B and F (m/s, steps/s)", "availability": "full",
             "note": "Already converted to velocities by the authors; raw times not deposited, so the conversion step (M4) cannot be re-done."},
            {"input": "6MWT B and F (m)", "availability": "full"},
            {"input": "Chair rise B and F (s), 10000 = unable", "availability": "full"},
            {"input": "Exact ages", "availability": "partial",
             "note": "Given in whole years in the deposit; not needed for Table 1."},
        ],
        "withheld_from_sandbox": [],
    }


def manifest_b(src):
    return {
        "paper": "B",
        "files": [
            {"name": "crc_cAMP_fold.csv", "role": "tab 'cAMP Fig 2B 3B 4B 5B': cAMP fold data per experiment, by log[CP55,940]", "given_to_reproducer": True},
            {"name": "crc_barr2_fold.csv", "role": "tab 'barr2 Fig 2D 3D 4D 5D': βarrestin2 fold data per experiment, by log[CP55,940]", "given_to_reproducer": True},
        ],
        "required_inputs": [
            {"input": "CB1-OX1 cAMP concentration-response, per experiment", "availability": "partial",
             "note": "Only the fold-transformed values (Y/K) are deposited, averaged over technical triplicates. Raw luminescence for the curves is not deposited, so the normalisation step (M4) cannot be re-done or checked."},
            {"input": "CB1-OX1 βarrestin2 concentration-response, per experiment", "availability": "partial",
             "note": "As above."},
            {"input": "Identity of the excluded experiment (M3)", "availability": "missing"},
        ],
        "withheld_from_sandbox": [
            {"name": "README.md", "reason": "describes the authors' analysis choices beyond the paper"},
            {"name": "workbook tabs 'Fig. 2B Table 1' ... 'Fig. 5D Table 4'", "reason": "authors' Prism fit outputs and ANOVA: contain the published values"},
            {"name": "workbook tabs 'Fig. 1', 'cAMP Fig 2A..', 'barr2 Fig 2C..'", "reason": "not needed for Table 1"},
        ],
    }


def export_b(xlsx, dest):
    wb = openpyxl.load_workbook(xlsx, data_only=True)
    for tab, name in (("cAMP Fig 2B 3B 4B 5B", "crc_cAMP_fold.csv"), ("barr2 Fig 2D 3D 4D 5D", "crc_barr2_fold.csv")):
        with open(dest / name, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            for row in wb[tab].iter_rows(values_only=True):
                w.writerow(["" if v is None else v for v in row])


def main(work, python, n_runs, papers="paperA,paperB"):
    work = Path(work).resolve()
    for paper in papers.split(","):
        base = work / paper
        src = base / "source" / "data"
        manifest = (manifest_a if paper == "paperA" else manifest_b)(src)
        if paper != "paperA" and not paper.endswith("B"):
            manifest["extraction_version"] = "v2"
        (base / "extract" / "data_manifest.json").write_text(json.dumps(manifest, indent=1, ensure_ascii=False), encoding="utf-8")
        for r in range(1, int(n_runs) + 1):
            root = base / "sandbox" / f"r{r}"
            if root.exists():
                shutil.rmtree(root)
            (root / "data").mkdir(parents=True)
            (root / "out").mkdir()
            shutil.copy(base / "extract" / "template.json", root / "template.json")
            methods = json.loads((base / "extract" / "methods.json").read_text(encoding="utf-8"))
            methods.pop("citation", None)  # no title/DOI of the paper inside the sandbox
            (root / "methods.json").write_text(json.dumps(methods, indent=2, ensure_ascii=False), encoding="utf-8")
            if paper == "paperA":
                for f in src.glob("*.xlsx"):
                    shutil.copy(f, root / "data" / f.name)
                note = " (one Excel workbook, one row per participant; see the NOTES rows at the bottom of the sheet)"
            else:
                export_b(next(src.glob("*.xlsx")), root / "data")
                note = (" (two CSV exports of the deposited workbook: concentration-response data already "
                        "expressed as fold, one column per independent experiment, rows = log10 molar CP55,940)")
            (root / "TASK.md").write_text(TASK.format(root=root, python=python, data_note=note), encoding="utf-8")
            print("built", root)


if __name__ == "__main__":
    main(*sys.argv[1:])
