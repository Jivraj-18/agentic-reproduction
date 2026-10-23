# Task: reproduce one results table from its methods description

You are reproducing a published results table **blind**. You get a structured description of the
methods and an empty copy of the table. You do not get the paper, its results or its code.

## Your world
Your working directory is this folder:

    C:\Users\e417152\code\reverify_research\springer-nature\work\paperB\sandbox\r_sonnet

Everything you need is inside it:
- `methods.json`: the methods, extracted from the paper. Each item quotes the source sentence. Items
  with `"gap": true` are places where the paper leaves a decision open.
- `template.json`: the target table. Same rows and columns as the published one, with every
  `value` and `stars` set to null.
- `data/`: the original data deposited by the authors (one CSV, aorta_crc.csv: for each extract group (CSE, EVE, HTE) and treatment as labelled in the deposit, the tension remaining as % of the U-46619 precontraction at each agonist concentration, for each of 5 experiments).

## Rules
1. Read and write **only inside this folder**. Do not open, list or search any path outside it.
   The single exception is the Python interpreter below.
2. **No web access** of any kind (no WebSearch, no WebFetch, no curl or pip downloads).
3. Do not try to find the paper, its results or the authors' code. Work from `methods.json` only.
4. Use only this interpreter, always with `-I`, passing paths as arguments:

       "C:\Users\e417152\code\reverify_research\springer-nature\.venv\Scripts\python.exe" -I out/repro_table.py data out

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
