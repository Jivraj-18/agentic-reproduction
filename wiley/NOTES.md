# Notes for Anand: agentic reproduction demo

Open `report/index.html` (single file, works offline, no external calls; the only links are the two papers' DOIs and Dryad DOIs). Live copy: https://jivraj-18.github.io/agentic-reproduction-wiley/. Three tabs: Overview, Paper A, Paper B. Nothing runs live; every number is a cached result.

The pitch line: *agents are given only a paper's Methods and its original data, never the code or the results. They rebuild a results table, and every cell is graded against the published one. Applied here to two Wiley papers.*

## What was run

| | Paper A | Paper B |
|---|---|---|
| Paper | Murphy et al. 2019, *Ann Clin Transl Neurol* (LGMD R9, 6-year natural history) | Mohamed & Laprairie 2025, *Pharmacol Res Perspect* (cannabinoid and orexin receptors) |
| Table | Table 1: median change in functional assessments (14 rows x 4 columns) | Table 1: CB1-OX1 curve parameters, cAMP and βarrestin2 (4 rows x 14 columns incl. ± and EC50) |
| Graded cells | 55 (the chair-rise SRM is "N/A" in the paper) | 52 (4 cells print no number: "n.d." and blank ±) |
| Why this table | All inputs in the Dryad file, and several analyst choices (who counts as a pair, how "unable" enters medians, Wilcoxon variant, SRM convention) | Fitted EC50/Emax/Hill, so many unstated fitting choices |

Pipeline: extract the Methods and blank the table; three independent blind reproducer runs per paper; deterministic grading (`scripts/grade.py`, A to F by % deviation and sign, units normalised); then an explainer that tests alternative readings of the Methods. The three isolation audits are on each paper tab. Scripts are in `scripts/`; everything per paper is in `work/paper*/`.

Grader conventions: reproduced values are compared at the precision printed in the original (floating-point noise removed first, and a number printed like "3000" is read to 1 significant figure). A reproduced value that satisfies a published limit such as "<0.001" counts as a match, and a limit that is not satisfied is compared as printed.

## Grade distributions (median of 3 runs, per cell)

- **Paper A: 44 A, 8 B, 2 C, 1 E.** Table grade A in every run (4.71 out of 5 each). Sign agrees 55/55; within 20% on 52/55. All 55 cells came out identical in all three runs.
- **Paper B, first extraction (v1): 35 A, 3 B, 2 C, 2 D, 8 E, 2 F.** Table grade B, B, C across the runs (4.08, 3.90, 3.10). 73% of numbers within 20%.
- **Paper B, corrected extraction (v2, shown on the page): 49 A, 1 B, 2 E.** Table grade A in every run (4.92, 4.90, 4.83). All 21 estimates with a published ± are inside 1.96 SE.

Paper A comes out mostly A. That is the honest result. I did not pick a harder table to make it look worse.

## Changes after the call with Anand

Anand asked for three things, all done in `report/index.html`:

1. **Percentages instead of letter grades.** Each paper tab opens with a one-sentence answer and three percentages: almost exactly right (within 2%), close enough (within 20%) and same direction. The A to F grades are still there, in the detail section.
2. **Click to see what differed.** Each percentage is a button. Selecting it lists the numbers that missed first, biggest gap first, each with its published value, the AI's value and a link to the reason. The numbers that matched are one click further down.
3. **Plain English.** Every sentence on the page was rewritten in short, plain wording. Each paper has a one-sentence answer, a one-sentence "what this means", and a card per reason a number differed. Each card says what the paper leaves unsaid, what the AI did, what the authors did, and the one sentence that would have prevented it. The wording lives in `work/plain_language.json`.

Detail that used to be at the top (the full side-by-side table, the Methods checklist, the three isolation checks, run-to-run agreement) is now in collapsed sections under "The evidence". The page also shows what it cost, and that the first Paper B attempt was our own mistake.

## Which model ran what (checked against the agents' own records)

- All 12 AI agents that rebuilt or explained a table (3 runs per attempt, three attempts, plus 3 explainers) ran on **Claude Opus 5.5**. None ran on Sonnet.
- The session that built the pipeline, graded, and assembled the page started on Opus 5.5 and was switched to **Sonnet 5.5** part-way through (the last part of the work: the final page fixes, the notes, and the GitHub publishing). So the correct line is "Opus 5.5 for the agents that did the reproducing; Sonnet 5.5 only for part of the orchestration". It is not "sub-agents on Sonnet".
- The agents ran in their own folders with only the Methods and data, checked afterwards by three audits. That is not an operating-system sandbox.

## Added 23 Oct 2026: one Sonnet 5.5 run per paper, and corrected run costs

For the Opus vs Sonnet comparison on the combined page (`../index.html`), each paper got one Claude Sonnet 5.5 run (`sandbox/r_sonnet`) from the same frozen inputs as the Opus runs (copied from `r1`; only the paths in TASK.md changed, plus a `tmp/` folder for scratch files). The Wiley page itself still shows the three Opus runs.

| | Opus 5.5 runs r1 / r2 / r3 | Sonnet 5.5 |
|---|---|---|
| Paper A, within 2% / within 20% (of 55) | 44 / 52 each | 44 / 52 |
| Paper B, within 2% / within 20% (of 52) | 51/51, 50/51, 49/50 | 52 / 52 |
| Stars agree | A 14/14, B 8/8 | A 14/14, B 6/8 |
| Rebuild cost per run, at least | A $0.41 / $0.38 / $0.37; B $0.46 / $0.55 / $0.47 | A $0.22; B $0.25 |

- Grades for all four runs: `eval/grades_all.json` (`grades.json` stays the Opus-only file the page uses). Sonnet audits: `eval/audit_r_sonnet.json` (no path outside the sandbox; two fit bounds, 1e4 and -12, reviewed in `audit_review.json`). Leak check over all four sandboxes: `eval/leak_all.json`, pass.
- Costs above are re-measured per run with `elsevier/scripts/agent_cost.py` (`eval/cost_*.json`). The earlier Cost section below undercounts output the same way (559 output tokens logged for three runs), so treat its figures as lower bounds too.

## Cost (estimates from token counts in the agents' records, at published prices)

| | Estimated cost | Range |
|---|---|---|
| Paper A: 3 runs + explainer | about $2 | $1.66 to $2.42 |
| Paper B: one clean pass (3 runs + explainer) | about $2.50 | $2.21 to $2.88 |
| Paper B: both attempts | about $6 | $5.31 to $7.02 |
| Orchestrating session so far (built the pipeline, grading, page, notes) | about $15 to $17 | $14.80 to $17.45 |

- The range is the difference between the standard and the one-hour price for writing to the prompt cache. Prices used: Opus 5.5 $4 in and $20 out per million tokens, cache reads $0.20.
- About 10 minutes of AI time per paper once set up (the three runs go in parallel, then the explainer).
- Summarising the Methods was done in the orchestrating session, so its cost sits in the last row, not in the per-paper rows. A production service would add roughly one more agent run per paper for that step.
- Anand's guess was $1 for neurology and $5 for pharmacology. Measured: about $2 and about $2.50 per clean pass. The pharmacology paper is only expensive if the first reading of the Methods is wrong.
- The per-agent figures are in `work/_cost.json`.

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
- **Paper B v1:** large variance. Only 12 of 52 cells identical across runs and 18 of 52 with the same grade. One run (per-experiment fits) scored 3.10, the other two 4.08 and 3.90. The fitting strategy is exactly the unstated choice.
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
