# Notes for Anand: agentic reproduction demo

Open `report/index.html` (single file, works offline, no external calls; the only links are the two papers' DOIs and Dryad DOIs). Three tabs: Method, Paper A, Paper B. Nothing runs live; every number is a cached result.

The pitch line: *agents are given only a paper's Methods and its original data, never the code or the results. They rebuild a results table, and every cell is graded against the published one. Applied here to two Wiley papers.*

## What was run

| | Paper A | Paper B |
|---|---|---|
| Paper | Murphy et al. 2019, *Ann Clin Transl Neurol* (LGMD R9, 6-year natural history) | Mohamed & Laprairie 2025, *Pharmacol Res Perspect* (cannabinoid and orexin receptors) |
| Table | Table 1: median change in functional assessments (14 rows x 4 columns) | Table 1: CB1-OX1 curve parameters, cAMP and βarrestin2 (4 rows x 14 columns incl. ± and EC50) |
| Graded cells | 55 (the chair-rise SRM is "N/A" in the paper) | 52 (4 cells print no number: "n.d." and blank ±) |
| Why this table | All inputs in the Dryad file, and several analyst choices (who counts as a pair, how "unable" enters medians, Wilcoxon variant, SRM convention) | Fitted EC50/Emax/Hill, so many unstated fitting choices |

Pipeline: extract the Methods and blank the table; three independent blind reproducer runs per paper; deterministic grading (`scripts/grade.py`, A to F by % deviation and sign, units normalised); then an explainer that tests alternative readings of the Methods. The three isolation audits are on each paper tab. Scripts are in `scripts/`; everything per paper is in `work/paper*/`.

Grader conventions: reproduced values are compared at the precision printed in the original (floating-point noise removed first, and a number printed like "3000" is read to 1 significant figure). A reproduced value that satisfies a published bound such as "<0.001" counts as a match.

## Grade distributions (median of 3 runs, per cell)

- **Paper A: 44 A, 8 B, 2 C, 1 E.** Table grade A in every run (4.71 out of 5 each). Sign agrees 55/55; within 20% on 52/55. All 55 cells came out identical in all three runs.
- **Paper B, first extraction (v1): 35 A, 4 B, 1 C, 2 D, 8 E, 2 F.** Table grade B, B, C across the runs (4.08, 3.92, 3.12).
- **Paper B, corrected extraction (v2, shown on the page): 49 A, 1 B, 2 E.** Table grade A in every run (4.92, 4.90, 4.83). All 21 estimates with a published ± are inside 1.96 SE.

Paper A comes out mostly A. That is the honest result. I did not pick a harder table to make it look worse.

## Something to know before the call: Paper B was run twice

The explainer traced **15 of the 17 missed cells in the first Paper B run to our own extraction**, not the paper:
1. The footnote saying "Hill slope constrained to 1" marks only the 0.50 µg cAMP row. We passed it on as a general rule, so agents fixed the slope on curves the authors fitted freely (10 cells).
2. We kept "minimum n=4" but dropped the "n=4-8" statement. Two runs used 4 of the 8 control columns (3 cells).
3. A gap note wrongly said a rule was absent from Table 1. The Table 1 footnote states it (2 cells).

I fixed those three things in the spec using only sentences quoted from the PDF, rebuilt the sandboxes, and ran three fresh agents (v2). Both extractions, all six sets of runs and both audits are kept, and the page shows v1 and v2 side by side ("Two extractions"). Say this plainly if asked: the extraction step is part of the method and it can be wrong, and it was the largest cause of misses here.

I changed the extraction after seeing grades, which a strict benchmark would not do. This is a demonstration of the loop, not a benchmark number.

## Best "underspecified Methods" example (Paper A, medians)

**One unstated choice: do medians use only participants with paired values, or every value available at each visit?**

The table footnotes give paired counts ("Paired values available in 22 participants"), so all three agents took medians over paired participants only. The authors took medians over everything available at each visit. That reading, run in `work/paperA/eval/sensitivity/best_reading.py`, reproduces **all 28 median cells**. It fixes the three cells that missed:

- FVC lying at 6 years: 56 -> 54 (published 54)
- Stair descent at 6 years: 0.52 -> 0.42, printed as 0.4 (published 0.4)
- Chair rise at 6 years: 7.8 s -> 9.8 s (published 9.8)

Suggested Methods wording (the line to read out):

> Medians at each visit were computed over all participants with a value at that visit (so n can exceed the number of paired values given in the footnotes), whereas Wilcoxon tests used only participants with paired values.

I re-ran this reading myself and it matches.

A second underspecified item in the same table: **missing-baseline handling in the velocity SRMs** (4 cells). The Methods give no missing-data rule. Using the 22 paired participants gives SRMs of -0.49, -1.16, -0.47 and -0.49. Counting the one participant with no baseline value as 0 (n = 23) gives -0.48, -1.02, -0.46 and -0.47, which are the published values.

Paper B has **no** cell I can honestly call underspecified: everything the agents needed was in the PDF. Its remaining misses are one sign-printing inconsistency in the paper and one bound the spec had to leave out (see below).

Other findings the explainer made:
- Paper B prints the constrained cAMP Hill slope as "-1" while its footnote says "constrained to 1". Fitting at +1 or -1 gives identical curves; only the printed sign differs, and the agents split 2-1.
- Paper A's footnote says 17 paired chair-rise values. The data give 22 (or 13 with real times at both visits). No reading gives 17.
- 4 of Paper A's Wilcoxon P values stay unexplained ("Unknown"). Nothing I tried reproduces them, and the page says so.

## Run-to-run variance

- **Paper A:** all 55 cells identical across the three runs. (An earlier version of my grader split one cell, a chair-rise median of 2.65 s, because two runs stored it with floating-point noise. I fixed the grader to remove that noise before comparing.)
- **Paper B v1:** large variance. Only 13 of 52 cells identical across runs and 19 of 52 with the same grade. One run (per-experiment fits) scored 3.12, the other two 4.08 and 3.92. The fitting strategy is exactly the unstated choice.
- **Paper B v2:** 48 of 52 identical, 49 of 52 with the same grade. Variance collapses once the spec says which curve each footnote marks.

The spread across the three runs is shown in the hover for every cell on the scorecard.

## Isolation and audits (all on the page)

- **Leak check:** zero hits for every published value in the files given to the reproducers. For Paper B, also zero hits for 541 full-precision values from the authors' Prism tabs. Two Paper B values are single digits ("<5", "-1") that cannot be searched meaningfully, and the page says so. Matches in the deposited raw data are listed separately because short numbers also occur there as ordinary measurements.
- **Path audit:** no web tools, no URLs, no access outside each run's folder. The scan flagged some items; each was checked by hand and the reasons are on the page (relative `../data` paths that resolve inside the sandbox, `cd ..` back to the sandbox root, and Claude Code saving oversized tool output to its own overflow file, which held only the agent's own sandbox files). Verdicts are in `work/*/eval/audit_review.json`.
- **Hard-coding audit:** no published value typed into any script. A few literals matched by coincidence (an optimiser start value, a column index, a search bound) and were reviewed.
- **Paper B's Dryad workbook contains the authors' Prism fit outputs, which are the published values.** Only the two raw concentration-response tabs went into the sandbox, as CSV. The README was withheld too. The explainer (which is not blind) used the Prism tabs as corroboration and says so wherever it does.
- Every `source_sentence` is verbatim in the PDF (15/15 for each v1 spec, 18/18 for the v2 spec; `scripts/verify_sources.py`, ignoring Greek letters and line breaks lost by the PDF text layer).
- Grades come from the script, never from an LLM. I spot-checked five cells against the raw data by hand (six-minute walk median, hip adduction median, chair-rise median, one cAMP Emax cell, one Hill slope), and the page headline counts equal `grades.json`.

## Deviations from the brief

- **Reproducers were Claude subagents** launched from this session (Opus 5.5) with a TASK.md and a clean folder, not separate Claude Code CLI sessions. Isolation was enforced by folder contents and rules, then audited from transcripts. It is not an OS-level sandbox.
- **Data copied, not symlinked** into each sandbox (Windows symlinks need admin).
- **No original code,** so the explainer's rule is: "underspecified" requires a flagged gap *and* a re-run showing the alternative reading moves the cell to the published value. When a cell met neither, I used "Unknown" or "Original: inconsistent" rather than stretch the label.
- **One operator note on the page:** it says the Paper B ">10000" miss is partly the cost of blinding. That bound is itself a published cell, so the spec had to omit it. The category follows the usual definition (the spec omits something the PDF says), but the note makes the trade-off visible.
- Grey cells on the scorecard print no number in the original and are not graded.
- I did not publish the page anywhere. It is a local file.

## Caveats to state if asked

- Evaluations of this kind are usually run on papers already known to be reproducible, which flatters headline numbers.
- Results vary across reruns. The page shows all three, not the best.
- The explainer's attributions are model judgements, not validated against human reviewers. We checked them by re-running the alternative readings, and I reclassified two by hand.
- Two papers, two tables, and Paper B's extraction was corrected once after seeing results. This shows the method. It is not a benchmark.
- The "At scale" section on each tab is a proposal, not something measured here. It flags issues for editors and does not judge papers.
