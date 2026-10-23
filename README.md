# Agentic reproduction

An AI gets only a paper's Methods and the authors' deposited data, never their code or results. It rebuilds one results table, and a fixed script grades every cell against the published one. Misses are then traced to their cause.

Live page: `index.html` (GitHub Pages). It lists all six papers and compares Claude Opus 5.5 with Claude Sonnet 5.5.

| Folder | Papers | Runs |
|---|---|---|
| `elsevier/` | Heliyon 2024 (knot-tying RCT); Toxicology Reports 2025 (mixture toxicity) | one Opus 5.5 run, one Sonnet 5.5 run |
| `springer-nature/` | BMC Pediatrics 2024 (HFNC vs NIV RCT); Scientific Reports 2023 (e-cigarette extracts, rat aorta) | one Opus 5.5 run, one Sonnet 5.5 run |
| `wiley/` | Ann Clin Transl Neurol 2019 (LGMD R9); Pharmacol Res Perspect 2025 (CB1-OX1 signalling) | three Opus 5.5 runs (first demo), one Sonnet 5.5 run |

Each folder holds its own pipeline (`scripts/`), per-paper work (`work/`), page (`docs/index.html`) and `NOTES.md`. The publisher names only say whose papers were used; nothing here is made for or endorsed by them.

The top page is built by `hub/build_hub.py` from each folder's grades (`eval/grades.json`, Wiley `eval/grades_all.json`), costs (`eval/cost_*.json`) and the model-choice tables (`eval/choices.json`):

    python -I hub/build_hub.py . index.html
