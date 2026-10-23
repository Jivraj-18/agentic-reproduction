# Notes: agentic reproduction of two Elsevier papers

Same method as the Wiley demo, extended to a second client after the 22 Oct 2026 call with Anand. The publisher's name says whose papers were used; the page is not made for or presented as from Elsevier. Page: `docs/index.html` (GitHub Pages), in the same layout as the Wiley page, with a switch between Claude Opus 5.5 and Claude Sonnet 5.5 inside each paper tab.

The pitch line is unchanged: *the AI gets only a paper's Methods and its original data, never the code or the results. It rebuilds a results table, and a fixed script grades every cell against the published one.*

## What was run

| | Paper A | Paper B |
|---|---|---|
| Paper | Labrosse et al. 2024, *Heliyon* (laparoscopic knot-tying RCT) | Dawson & Schultz 2025, *Toxicology Reports* (M2CA mixture toxicity) |
| Table | Table 1: 12 mixed-model contrasts (ratio, two group means, 95% CI, p) | Table 2: summary statistics over 31 fitted 5PL-1P curves at 3 times (mean, SD, CV, range, Shapiro-Wilk W) |
| Graded cells | 72 | 95 |
| Data | Dryad, raw per-knot measurements | OSF, raw bioassay readings (exported from the docx to one CSV) |
| Withheld from the AI | Dryad README (describes the analysis), blank questionnaires | the authors' fitted endpoint values, CA/IA outputs, TDT table, SigmaPlot procedures |

Changes from Wiley, as agreed: **one run per model** (Opus 5.5 and Sonnet 5.5) instead of three Opus runs. The explainer (non-blind, Opus 5.5) is unchanged in spirit and now writes the plain-language cards directly (`eval/story.json`).

## Results

| | Opus 5.5 | Sonnet 5.5 |
|---|---|---|
| Paper A, within 2% / within 20% | 29 / 54 of 72 (40% / 75%) | 51 / 68 of 72 (71% / 94%) |
| Paper B, within 2% / within 20% | 91 / 95 of 95 (96% / 100%) | 91 / 95 of 95 (96% / 100%) |

**Paper A** is the interesting one. Every miss traces to four causes, each tested by re-running the alternative on the data (with all fixes, 69 of 72 cells land within 2%):

1. **An unstated model term (12-13 cells per run).** The authors' mixed models also adjust for the position of each technique in the participant's random sequence. The Methods name only technique and run; the only hint is a Discussion sentence. Adding the term gives the mistake odds ratios exactly (2.294 / 2.453 / 1.070).
2. **A zero before a log (6 cells).** One knot-strength change is exactly 0. Both runs dropped it; the authors set it to 0.1 mm. The paper's Table 2 independently confirms this (only the 0.1 reading gives its printed 5.59).
3. **Which average is in brackets (Opus 18 cells, Sonnet 2).** The bracketed "means" are the average of the three per-run plain means. Opus printed model-based geometric means instead; Sonnet averaged all knots at once.
4. **Opus dropped a recorded zero spread value (7 cells, Opus only).** A reproducer choice, not a paper problem.

The suggested Methods sentence for the headline: *"All mixed models included technique, run and the position of the technique within the participant's sequence (first, second or third block) as fixed effects, with a random intercept per participant."*

**Paper B** reproduces almost perfectly. Both runs agree with each other to about six digits, and the explainer confirmed their per-test fits match the authors' withheld endpoint values to 4 decimals. The 4 misses are the paper's own: one printed mean (0.55) contradicts its own SD and CV (the data give 0.535, likely a typo for 0.53), one CV does not follow from the data, and two cells sit on a rounding boundary.

## Opus vs Sonnet

Say this carefully: **one run per model per paper**. On Paper B the two models made identical choices and got identical numbers. On Paper A the whole gap is one open choice (what the bracketed "means" are) plus one Opus slip (dropping a recorded zero). Opus even listed the plain means as its rejected alternative. A second Opus run could well choose differently, so this is not evidence that Sonnet is the better model. The defensible finding is about the paper: one undefined statistic moved 16 numbers.

## Cost

Measured from each agent's run record at list prices (Opus 5.5 $4 / $20 per million tokens in / out, Sonnet 5.5 $2 / $10, cache reads $0.20, cache writes 1.25x input).

| | Opus 5.5 run | Sonnet 5.5 run | Explainer (Opus) |
|---|---|---|---|
| Paper A | $0.65 or more | $0.20 or more | $1.53 or more |
| Paper B | $0.36 or more | $0.18 or more | $0.69 or more |

- **These are lower bounds.** Subagent run records keep exact input and cache counts but log most responses with a placeholder output count (7-24 tokens). The "or more" figure replaces that with the output we can see (code and text, about 3.5 characters per token). Hidden reasoning tokens cannot be counted. The as-logged figures are in `work/*/eval/cost_*.json`.
- **The Wiley costs in `wiley/NOTES.md` have the same undercount** (e.g. 559 output tokens logged for three full runs), so they understate too.
- An exact figure needs each run as its own `claude -p` session, which reports `total_cost_usd`; `scripts/run_session.sh` does that. Claude Code's safety check blocks this session from starting unattended sessions with shell access, so those runs must be launched by the user.
- Not included: the orchestrating session (extraction, sandbox builds, grading, this page).
- Wall time: 1.5 to 4 minutes per rebuild run; the explainers took 4 to 12 minutes.

## Isolation and audits

- **Leak check:** zero published values in any file given to the runs. Paper B's 116 "data" hits are short numbers that also occur as raw measurements.
- **Path audit:** no access outside the sandbox. One flag in Paper A's Opus run was a regex for parsing mm:ss times, not a path.
- **Hard-coding audit:** no published value typed into any script. Three coincidental literals (0.975 for a 95% CI quantile; a fit bound 1e-3; a start value 0.3), each reviewed in `eval/audit_review.json`.
- Every `source_sentence` is verbatim in the PDF (19/19 and 12/12, `scripts/verify_sources.py`).
- Runs were Claude subagents launched from the orchestrating session with a TASK.md and a clean folder, checked afterwards by the audits. Not an OS-level sandbox.

## Extraction notes

- Paper B's Eq. 1-2 are printed with garbled layout. The extraction states the standard 5PL-minus-minimum reading and flags it as the extractor's reconstruction (S2, gap). Both runs used it and matched the authors' fits.
- The extraction was frozen before any run and not changed after grading.
