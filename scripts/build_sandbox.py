"""Step 1.4 + Step 2 setup: write data_manifest.json and build one isolated sandbox per run.

Each sandbox is the reproducer's whole world:
  sandbox/rN/TASK.md, methods.json, template.json, data/, out/
Data are copied, not symlinked (Windows symlinks need admin rights).

One sandbox per model (sandbox/r_opus, sandbox/r_sonnet); each is run by its own Claude Code session.

Paper A (Heliyon knot tying): only the data workbook goes in. The Dryad README describes the
authors' analysis, and the questionnaire forms are not needed for Table 1, so both are withheld.

Usage: python -I build_sandbox.py <work_dir> <python_exe> <paper> <run_names, comma-separated>
"""
import csv
import json
import shutil
import sys
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
        "files": [{"name": "DATA_Knot-tying_FINAL.xlsx",
                   "role": "sheet 'Knot-Tying_Data': one row per subject x technique x run (times as mm:ss, knot strength before/after 15 N and delta, knot-spread ability, mistakes); also a questionnaire sheet and a short-version sheet",
                   "given_to_reproducer": True}],
        "required_inputs": [
            {"input": "Total time per run", "availability": "full", "note": "Stored as mm:ss text."},
            {"input": "Delta knot strength per run (mm)", "availability": "full"},
            {"input": "Knot-spread ability per run (mm)", "availability": "full"},
            {"input": "Mistakes per run", "availability": "full"},
        ],
        "withheld_from_sandbox": [
            {"name": "README.md", "reason": "describes the authors' analysis beyond the Methods"},
            {"name": "Questionnaire_before/after_exercise_ENG.docx", "reason": "blank questionnaire forms, not needed for Table 1"},
        ],
    }


def manifest_b(src):
    return {
        "paper": "B",
        "files": [{"name": "raw_crc.csv",
                   "role": "every table of 'M2CA Study - Raw Data.docx' in long form: combination, test (1-3 in the order deposited), concentrations, time, replicate, % effect",
                   "given_to_reproducer": True}],
        "required_inputs": [
            {"input": "M2CA-alone concentration-response, duplicates, 15/30/45 min, 30 combinations", "availability": "full"},
        ],
        "withheld_from_sandbox": [
            {"name": "M2CA Study - Supplemental Table - Endpoint Values.docx", "reason": "authors' fitted ECx, slope, s and r2 per test: the answers"},
            {"name": "M2CA Study - CA and IA slope and asymmetry values.docx", "reason": "authors' fitted model outputs"},
            {"name": "Table of TDT Analyses - M2CA-containing Binary Mixtures.docx", "reason": "authors' TDT results"},
            {"name": "SigmaPlot 15 - Mixture Toxicity Transforms and Procedures.docx", "reason": "the authors' software procedures, beyond the Methods"},
        ],
    }


def export_b(src, dest):
    """Flatten the raw-data docx (header paragraphs + one table per test) into one long CSV."""
    import zipfile
    import xml.etree.ElementTree as ET
    w = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
    text = lambda el: "".join(x.text or "" for x in el.iter(w + "t")).strip()
    body = ET.fromstring(zipfile.ZipFile(src / "M2CA Study - Raw Data.docx").read("word/document.xml")).find(w + "body")
    combo, test = None, 0
    with open(dest / "raw_crc.csv", "w", newline="", encoding="utf-8") as f:
        out = csv.writer(f)
        out.writerow(["combination", "test", "chem_A", "chem_B", "conc_A_uM", "conc_B_uM", "time_min", "replicate", "effect_pct"])
        for el in body:
            if el.tag == w + "p" and text(el).startswith("Combination:"):
                combo, test = text(el).split(":", 1)[1].strip(), 0
            elif el.tag == w + "tbl" and combo:
                test += 1
                rows = [[text(c) for c in r.iter(w + "tc")] for r in el.iter(w + "tr")]
                chem_a, chem_b = (h.split("[")[0].strip() for h in rows[0][:2])
                for r in rows[1:]:
                    conc = ["" if set(v) <= {"-"} else v for v in r[:2]]
                    for i, v in enumerate(r[2:8]):
                        out.writerow([combo, test, chem_a, chem_b, *conc, (15, 30, 45)[i // 2], i % 2 + 1, v])


MANIFESTS = {"paperA": manifest_a, "paperB": manifest_b}
DATA = {"paperA": (["DATA_Knot-tying_FINAL.xlsx"],
                   " (one Excel workbook; sheet 'Knot-Tying_Data' has one row per subject x technique x run)"),
        "paperB": (export_b,
                   " (one CSV, raw_crc.csv: every concentration-response table of the deposit in long form. Each "
                   "combination has three tests in the order deposited: chemical A alone, chemical B alone, and the "
                   "mixture; an empty concentration means that chemical is absent from the test)")}


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
