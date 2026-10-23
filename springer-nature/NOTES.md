# Notes: agentic reproduction of two Springer Nature papers

Same method as the Wiley demo, extended to a second client after the 22 Oct 2026 call with Anand. The publisher's name says whose papers were used; the page is not made for or presented as from Springer Nature. Page: `docs/index.html` (GitHub Pages), in the same layout as the Wiley page, with a switch between Claude Opus 5.5 and Claude Sonnet 5.5 inside each paper tab.

## What was run

| | Paper A | Paper B |
|---|---|---|
| Paper | Santos et al. 2024, *BMC Pediatrics* (HFNC vs NIV in bronchiolitis, RCT) | Wölkart et al. 2023, *Scientific Reports* (tobacco smoke, e-cigarette and heated-tobacco extracts on rat aorta) |
| Table | Table 1: demographic and clinical characteristics (N (%), mean (SD), median (IQR), p) | Table 2: Emax ± SEM and EC50 (95% CI) for 12 treatments × 2 agonists, with significance stars |
| Graded cells | 101 of 131 printed (30 not graded, see below) | 120, plus 24 significance markers |
| Data | Dryad, one row per patient (with its column dictionary) | Zenodo workbook; only the raw concentration-response rows were given |
| Withheld from the AI | nothing; but age, weight and lengths of stay were deposited only as ranges | the authors' per-experiment EC50/Emax rows, log-EC50/CI rows and mean/SEM columns (they contain the published values) |

One run per model (Opus 5.5 and Sonnet 5.5), then a non-blind explainer (Opus 5.5) that tests each cause on the data and writes `eval/story.json`.

## Results

| | Opus 5.5 | Sonnet 5.5 |
|---|---|---|
| Paper A, within 2% / within 20% | 75 / 88 of 101 (74% / 87%) | 74 / 87 of 101 (73% / 86%) |
| Paper B, within 2% / within 20% | 63 / 112 of 120 (53% / 93%) | 67 / 110 of 120 (56% / 92%) |
| Paper B, significance stars agree | 24 / 24 | 22 / 24 |

**Paper A (BMC Pediatrics).** The two runs agree on 98 of 101 cells. The misses are mostly the paper's own problems:
1. **Chi-square with or without Yates' correction (3 p-values).** R applies the correction by default; the authors evidently did not. Without it: 0.151, 0.327, 0.213, printed as 0.15, 0.3, 0.2. Suggested sentence: *"Chi-square tests were computed without Yates' continuity correction."*
2. **Antibiotic p-value printed as <0.001 (1 cell).** 62 vs 49 of 126 gives p between 0.06 and 0.16 under every test. The same wrong value is repeated in the Discussion.
3. **Virus counts do not match the deposited spreadsheet (12 cells).** Only 10 HFNC babies have bocavirus in the data, so the published 11 is impossible; no counting rule gives the published NIV counts.
4. **Truncation instead of rounding (4 cells).**
5. Six cells remain unexplained (two skewed duration rows, the initial breathing-score SDs and p). One cell (Sonnet only) is a reproducer choice: a duration typed as "17h".
- **Not graded (30 cells):** age, weight z score, PICU and hospital length of stay were deposited only as ranges (e.g. "6-8"), and ventilator-associated pneumonia has no column. Data-sharing choices limit reproducibility here, independently of the Methods.

**Paper B (Scientific Reports).** The authors' own fitted rows, left in the deposit, rebuild 115 of 120 published cells, so the pipeline and grading are sound. The blind runs miss for reasons the Methods leave open:
1. **"Hill-type model" with a free baseline (38 cells per run).** Both runs fixed the curve's bottom at 0%; the authors fitted it freely (4 parameters). Re-running with a free baseline moves all 38 to grade A. Suggested sentence: *"Each experiment's curve was fitted to a four-parameter Hill equation with free bottom, top (Emax), EC50 and slope."*
2. **Emax above 100% (Opus only, 4 cells).** The authors set such Emax to 100%; Sonnet capped it, Opus refitted with a fixed slope.
3. **Flat CSE 1:3 acetylcholine curves (5 cells).** Curves without a plateau need an unstated limit on EC50.
4. **Wrong entries in the authors' worksheet (4 cells).** In the heated-tobacco undiluted DEA/NO row, experiment 4's values duplicate another treatment's, and experiment 5's EC50 contradicts its own curve. The published 87 nM (21-362) comes from those entries; the deposited curves give about 56 nM (29-108), which both runs reported.
5. Rounding (6 cells).

## Opus vs Sonnet

One run per model per paper. On both papers the two models made nearly the same choices: same cells, same misses, within a handful of cells of each other. The only real difference was in curves that never level off (Paper B), where Sonnet capped Emax at 100% and Opus refitted with a fixed slope; Opus matched all 24 significance stars and Sonnet 22. This is not evidence that either model is better.

## Cost

List prices (Opus 5.5 $4 / $20 per million tokens in / out, Sonnet 5.5 $2 / $10, cache reads $0.20, cache writes 1.25x input).

| | Opus 5.5 run | Sonnet 5.5 run | Explainer (Opus) |
|---|---|---|---|
| Paper A | $0.29 or more | $0.12 or more | $0.77 or more |
| Paper B | $0.39 or more | $0.13 or more | $1.42 or more |

- **Lower bounds**, for the same reason as in the Elsevier notes: subagent run records log most responses with a placeholder output count. The "or more" figure adds the visible output; hidden reasoning tokens are not counted. As-logged figures are in `work/*/eval/cost_*.json`. Exact figures need `scripts/run_session.sh` (separate `claude -p` sessions), which has to be launched by the user.
- The orchestrating session is not included. Rebuild runs took 1 to 2.5 minutes; explainers 5 to 12 minutes.

## Isolation and audits

- **Leak check:** zero published values in any file given to the runs. The short-number hits are Methods wording ("24 h", "96 h", "10 were excluded"; "EC50", "95% CI", "~90%"), reviewed in `eval/leak_review.json`. Before any run, the Paper A template's example bound "<0.001" was replaced with "<x" because it matched two published p-values.
- **Path audit, one real finding:** the Opus run on Paper B wrote one throw-away test script to the orchestrating session's scratchpad folder (outside its sandbox) and ran it on its own sandbox data. Its record shows nothing in that folder was listed, searched or read. That folder does hold the paper's full text from the paper search, so this is reported on the page, not waved through. The likely cause is Claude Code's standing instruction to subagents to use the session scratchpad for temporary files, which overrode the TASK.md rule. Fix for next time: put a `tmp/` folder inside each sandbox and say so in TASK.md.
- **Hard-coding audit:** no published value typed into any script; the matches are a quartile (0.25) and a grid step (0.5), reviewed in `eval/audit_review.json`.
- Every `source_sentence` is verbatim in the PDF (8/8 and 9/9).
- The extraction was frozen before any run and not changed after grading.
