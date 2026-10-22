"""Write methods.json, template.json and tables_full.json for Paper A (Heliyon 2024, knot tying, Table 1).

Every source_sentence is copied from source/paper.txt (checked by scripts/verify_sources.py).
tables_full.json holds the published values and never goes into a sandbox.

Usage: python -I build_extract.py <extract_dir>
"""
import json
import sys
from pathlib import Path

CITATION = ("Labrosse KB et al. Intracorporeal vs. extracorporeal open and closed knot tying techniques in laparoscopy: "
            "A randomized, controlled study. Heliyon 2024;10:e25178. doi:10.1016/j.heliyon.2024.e25178")

METHODS = {
    "paper": "A",
    "citation": CITATION,
    "research_question": {
        "id": "RQ",
        "text": "Compare one intracorporeal and two extracorporeal (open and closed jaw-type knot pusher) laparoscopic knot-tying techniques for time, knot strength, knot-spread ability and mistakes, in novices.",
        "source_sentence": "The present study’s aim was to compare laparoscopic extracorporeal and intracorporeal knot-tying techniques with respect to time, knot strength, and knot-spread ability when performing a square-to-slip knot.",
        "gap": False,
    },
    "setting": {
        "id": "SET",
        "population": "57 medical students with no laparoscopic experience.",
        "period": "Single session per participant (2021-2022).",
        "site": "Pelvic trainer (GESEA certified), Switzerland.",
        "source_sentence": "The study participants were medical students (average age of 22 years) with no experience of laparoscopic surgery.",
        "gap": False,
    },
    "data_sources": [
        {
            "id": "D1",
            "name": "Dryad dataset deposited by the authors",
            "summary": "Per-subject, per-technique, per-run measurements: times, knot strength before/after 15 N and their difference, knot-spread ability, mistakes. Plus a questionnaire sheet.",
            "source_sentence": "The datasets analyzed for this study are available at",
            "gap": False,
        }
    ],
    "general_manipulations": [
        {
            "id": "M1",
            "description": "Design: each participant performed all three techniques (A intracorporeal; B extracorporeal, open jaw-type pusher; C extracorporeal, closed jaw-type pusher) in a randomised order (six sequences), three runs (knots) per technique.",
            "source_sentence": "Fifty-seven participants were divided into randomized blocks of three knotting techniques with six different sequences of knot tying.",
            "gap": False,
        },
        {
            "id": "M2",
            "description": "Three knots (runs) per technique per participant.",
            "source_sentence": "According to their randomization, they performed three knots of each technique.",
            "gap": False,
        },
        {
            "id": "M3",
            "description": "Invalid runs: 513 measurements per variable from 57 students; 86 measurements excluded across all variables because of irreversible errors. Excluded runs are N/A in the data.",
            "source_sentence": "We excluded 86 measurements across all variables due to participants making irreversible errors that included pulling the thread out of the stitch, irreversibly knotting the threads together or being unable to perform the knot after watching instructional videos.",
            "gap": True,
            "gap_note": "The paper does not say how a run with some but not all variables missing is handled, or whether a participant with missing runs stays in the model with the runs they have.",
        },
        {
            "id": "M4",
            "description": "Time: task completion time, from the marked starting position until the thread remnants were removed, recorded in seconds.",
            "source_sentence": "The task commenced in this position and was completed once the remains of the thread had been completely removed.",
            "gap": False,
        },
        {
            "id": "M5",
            "description": "Knot strength: elongation of the loop. Thread length measured, loop pulled at 15 N, length measured again; the length difference in mm is the knot strength.",
            "source_sentence": "Next, the thread was measured again, and the length difference was recorded in mm.",
            "gap": False,
        },
        {
            "id": "M6",
            "description": "Knot-spread ability: dilatation of the loop (mm) after spreading with curved scissors.",
            "source_sentence": "Knot-spread ability was determined by measuring the loop’s dilatation after it was spread using curved scissors.",
            "gap": False,
        },
        {
            "id": "M7",
            "description": "Mistakes: counted manually per run.",
            "source_sentence": "Mistakes were manually counted and recorded.",
            "gap": False,
        },
    ],
    "tables": [
        {
            "id": "T1",
            "name": "Table 1",
            "caption": "Comparison of different knot tying techniques by run time, knot strength and knot-spread ability.",
            "row_labels": [],
            "column_labels": [],
            "table_specific_filters": [],
            "specification": [
                {
                    "id": "S1",
                    "description": "Descriptive statistics: means with SD (and medians with IQR) for metric variables. Each row prints, in brackets after the effect, a value for each of the two techniques compared.",
                    "source_sentence": "For categorical data, counts and frequencies, and for ordinal or metric variables, means with standard deviations, medians and interquartile ranges (IQRs) are presented.",
                    "software": "R 4.1.3",
                    "gap": True,
                    "gap_note": "The bracketed per-technique values sit under the header 'means' but the paper does not say which mean (arithmetic or geometric, over all valid runs or per participant first), or, for Mistakes, whether it is the mean count or the share of runs with at least one mistake.",
                },
                {
                    "id": "S2",
                    "description": "Knot-spread ability: linear mixed-effects model with technique and run as predictors; effects are differences of means.",
                    "source_sentence": "For the prediction of spreading ability, linear mixed effects models were used.",
                    "software": "R 4.1.3",
                    "gap": True,
                    "gap_note": "The random-effects structure is not stated (random intercept per participant is the usual choice; sequence could also enter). Whether Table 1 (all runs together) uses the model with or without the technique x run interaction is not stated.",
                },
                {
                    "id": "S3",
                    "description": "Predictors: technique and run (first, second, third). A technique x run interaction is included for comparisons within runs.",
                    "source_sentence": "Predictor variables were technique and run (first, second, or third run).",
                    "gap": False,
                },
                {
                    "id": "S4",
                    "description": "Interaction only for comparisons within runs.",
                    "source_sentence": "For nested comparisons within runs, an interaction between technique and run was included in the models.",
                    "gap": False,
                },
                {
                    "id": "S5",
                    "description": "Total run time and delta knot strength are log-transformed and modelled the same way; effects are geometric mean ratios.",
                    "source_sentence": "For total run time and delta knot strength, these variables were log transformed.",
                    "gap": True,
                    "gap_note": "The log base and handling of zero or negative delta knot strength values are not stated.",
                },
                {
                    "id": "S6",
                    "description": "Mistakes: dichotomised as 0 vs 1 or more; generalised linear mixed-effects model with logit link; effects are odds ratios.",
                    "source_sentence": "For mistakes, values were dichotomized as 0, = /> 1 and a generalized linear mixed-effects model with logit link was applied.",
                    "gap": True,
                    "gap_note": "The estimation method (Laplace or adaptive quadrature) and random-effects structure are not stated.",
                },
                {
                    "id": "S7",
                    "description": "All mixed-model estimates are given with 95% confidence intervals and p-values.",
                    "source_sentence": "All estimators of the mixed models are presented with 95 % confidence intervals (CIs) and p-values.",
                    "gap": True,
                    "gap_note": "How CIs and p-values are computed (Wald z, t with Satterthwaite or Kenward-Roger df, profile likelihood) is not stated; the R package is not named.",
                },
                {
                    "id": "S8",
                    "description": "Effect types by row (table footnote a): Time and Knot strength = geometric mean ratios; Knot-spread ability = differences of means; Mistakes = odds ratios. Contrast 'X: Y' is X relative to Y.",
                    "source_sentence": "For ‘Time’ and ‘Knot strength’, ratios correspond to geometric mean ratios.",
                    "gap": False,
                },
                {
                    "id": "S9",
                    "description": "p-values come from the mixed-effects models; no adjustment for multiple comparisons; significance at p < 0.05.",
                    "source_sentence": "No adjustments were made for multiple comparisons.",
                    "gap": False,
                },
            ],
        }
    ],
}

ROWS = [  # id, label, published: effect, mean1, mean2, lower, upper, p
    ("time_io", "Time (sec): Intracorporeal : Extracorporeal, open", "1.33", "386.6", "279.5", "1.244", "1.429", "<0.001"),
    ("time_ic", "Time (sec): Intracorporeal : Extracorporeal, closed", "1.361", "386.6", "255.7", "1.27", "1.458", "<0.001"),
    ("time_oc", "Time (sec): Extracorporeal, open : Extracorporeal, closed", "1.02", "279.5", "255.7", "0.953", "1.093", "0.563"),
    ("ks_io", "Knot strength (mm): Intracorporeal : Extracorporeal, open", "0.827", "3.80", "4.92", "0.688", "0.994", "0.043"),
    ("ks_ic", "Knot strength (mm): Intracorporeal : Extracorporeal, closed", "0.966", "3.80", "4.96", "0.805", "1.159", "0.709"),
    ("ks_oc", "Knot strength (mm): Extracorporeal, open : Extracorporeal, closed", "1.168", "4.92", "4.96", "0.975", "1.4", "0.092"),
    ("sp_io", "Knot-spread ability (mm): Intracorporeal : Extracorporeal, open", "1.328", "11.72", "10.46", "0.782", "1.875", "<0.001"),
    ("sp_ic", "Knot-spread ability (mm): Intracorporeal : Extracorporeal, closed", "1.519", "11.77", "10.26", "0.976", "2.063", "<0.001"),
    ("sp_oc", "Knot-spread ability (mm): Extracorporeal, open : Extracorporeal, closed", "0.191", "10.46", "10.26", "-0.347", "0.729", "0.486"),
    ("mi_io", "Mistakes: Intracorporeal : Extracorporeal, open", "2.294", "0.36", "0.28", "1.261", "4.17", "0.007"),
    ("mi_ic", "Mistakes: Intracorporeal : Extracorporeal, closed", "2.453", "0.36", "0.22", "1.353", "4.447", "0.003"),
    ("mi_oc", "Mistakes: Extracorporeal, open : Extracorporeal, closed", "1.07", "0.28", "0.22", "0.578", "1.981", "0.831"),
]
COLUMNS = [
    {"id": "eff", "label": "Ratio (a): geometric mean ratio, difference of means or odds ratio", "metric_type": "effect"},
    {"id": "m1", "label": "Mean, first technique of the contrast (in brackets)", "metric_type": "mean"},
    {"id": "m2", "label": "Mean, second technique of the contrast (in brackets)", "metric_type": "mean"},
    {"id": "lo", "label": "95% CI lower", "metric_type": "CI"},
    {"id": "hi", "label": "95% CI upper", "metric_type": "CI"},
    {"id": "p", "label": "p-value (b)", "metric_type": "p"},
]
UNITS = {"time": "s", "ks": "mm", "sp": "mm", "mi": None}


def decimals(raw):
    s = raw.lstrip("<>-")
    return len(s.split(".")[1]) if "." in s else 0


def main(out):
    out = Path(out)
    rows = [{"id": r[0], "label": r[1]} for r in ROWS]
    tmpl_cells, full_cells = {}, {}
    for rid, _, *vals in ROWS:
        for col, raw in zip(COLUMNS, vals):
            unit = UNITS[rid.split("_")[0]] if col["id"] in ("m1", "m2") or (col["id"] in ("eff", "lo", "hi") and rid.startswith("sp")) else None
            key = f"{rid}|{col['id']}"
            tmpl_cells[key] = {"metric_type": col["metric_type"], "unit": unit, "link_to": None, "value": None, "stars": None}
            comp = "<" if raw.startswith("<") else None
            full_cells[key] = {"raw": raw, "metric_type": col["metric_type"], "unit": unit, "stars": None, "link_to": None,
                               "comparator": comp, "value": float(raw.lstrip("<")), "decimals": decimals(raw), "graded": True}
    caption = "Table 1. " + METHODS["tables"][0]["caption"]
    template = {"paper": "A", "table_id": "Table 1", "caption": caption, "rows": rows, "columns": COLUMNS,
                "star_legend": None, "cells": tmpl_cells,
                "instructions": "Fill `value` (a number; or a string such as '<x' for a bound) for every cell; set `stars` to '' (this table prints no significance markers). `unit` gives the unit the table uses for that cell."}
    full = {"paper": "A", "table_id": "Table 1", "caption": caption, "rows": rows, "columns": COLUMNS, "excluded_columns": [],
            "footnotes": ["a For ‘Time’ and ‘Knot strength’, ratios correspond to geometric mean ratios. For ‘Knot-spread ability, ratios correspond to differences of means. For ‘Mistakes’, ratios correspond to odds ratios.",
                          "b The p-values were calculated using a mixed-effects model. A p-value <0.05 was considered significant."],
            "star_legend": None, "cells": full_cells}
    for name, obj in (("methods.json", METHODS), ("template.json", template), ("tables_full.json", full)):
        (out / name).write_text(json.dumps(obj, indent=1, ensure_ascii=False), encoding="utf-8")
    print(len(full_cells), "cells")


if __name__ == "__main__":
    main(sys.argv[1])
