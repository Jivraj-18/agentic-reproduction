"""Write methods.json, template.json and tables_full.json for Paper B (Toxicology Reports 2025, M2CA mixtures, Table 2).

Every source_sentence is copied from source/paper.txt (checked by scripts/verify_sources.py).
tables_full.json holds the published values and never goes into a sandbox.

Usage: python -I build_extract.py <extract_dir>
"""
import json
import sys
from pathlib import Path

CITATION = ("Dawson DA, Schultz TW. Equations for estimating binary mixture toxicity: Methyl-2-chloroacetoacetate-containing "
            "combinations. Toxicology Reports 2025;14:101939. doi:10.1016/j.toxrep.2025.101939")

METHODS = {
    "paper": "B",
    "citation": CITATION,
    "research_question": {
        "id": "RQ",
        "text": "Characterise the toxicity of binary mixtures containing methyl-2-chloroacetoacetate (M2CA) in the Microtox assay; Table 2 reports how repeatable the 31 tests of M2CA alone were.",
        "source_sentence": "The repeatability of the M2CA tests was assessed by calculating the mean, standard deviation, coefficient of variation (CV), range, and Shapiro-Wilk W values for each ECx, slope, s, r2, and TDT value.",
        "gap": False,
    },
    "setting": {
        "id": "SET",
        "population": "Bioluminescence inhibition in the marine bacterium Allovibrio fischeri (Microtox).",
        "period": "Exposure readings at 15, 30 and 45 minutes.",
        "site": "Laboratory (Microtox analyzer, 15 °C).",
        "source_sentence": "The marine bacterium Allovibrio fischeri was the model organism for testing.",
        "gap": False,
    },
    "data_sources": [
        {
            "id": "D1",
            "name": "OSF raw data deposited by the authors",
            "summary": "For each of 30 binary combinations (M2CA = chemical A), three tests: A alone, B alone and the mixture, each with seven duplicated concentrations and % effect at 15, 30 and 45 min.",
            "source_sentence": "Chemical A was always M2CA, while chemical B was one of the 30 chemicals noted in Table 1.",
            "gap": False,
        }
    ],
    "general_manipulations": [
        {
            "id": "M1",
            "description": "Each test: seven concentrations in duplicate plus a duplicated control; % effect is already computed from the light readings by the instrument software.",
            "source_sentence": "Each test within a given combination had seven duplicated concentrations and a duplicated control.",
            "gap": False,
        },
        {
            "id": "M2",
            "description": "Readings after 15, 30 and 45 minutes of exposure.",
            "source_sentence": "Toxicity assessments were made after 15-, 30-, and 45-minutes of chemical exposure.",
            "gap": False,
        },
        {
            "id": "M3",
            "description": "The 31 tests of M2CA alone: the A-alone test of each of the 30 combinations, plus the sham combination M2CA-M2CA, where chemical B is also M2CA.",
            "source_sentence": "One combination was a sham (M2CA-M2CA), giving 31 tests of M2CA alone.",
            "gap": True,
            "gap_note": "Which test of the sham combination supplies the 31st M2CA-alone value is not stated (its B-alone test is M2CA tested alone).",
        },
    ],
    "tables": [
        {
            "id": "T2",
            "name": "Table 2",
            "caption": "Summary statistics for methyl-2-chloroacetoacetate (M2CA) tested alone (n = 31).",
            "row_labels": [],
            "column_labels": [],
            "table_specific_filters": [],
            "specification": [
                {
                    "id": "S1",
                    "description": "Each test's concentration-response data (y = % effect vs concentration x, in µM) are fitted separately at each exposure time with the 5PL-1P function: the five-parameter logistic without its minimum-effect parameter. Parameters: maximum effect, EC50, Hill slope, asymmetry s.",
                    "source_sentence": "User-developed program files fitted the raw data to sigmoid curves using the five-parameter logistic function from which the minimum effect parameter had been removed [14].",
                    "software": "SigmaPlot 15",
                    "gap": True,
                    "gap_note": "Whether the duplicate replicates are fitted as separate points or averaged first, and the least-squares weighting, are not stated.",
                },
                {
                    "id": "S2",
                    "description": "Equation 1: y = max / (1 + (xb/x)^Hillslope)^s. Equation 2: xb = EC50 × 10^((1/Hillslope) × log10(2^(1/s) − 1)), so that y = max/2 at x = EC50.",
                    "source_sentence": "in which y = % effect, max = maximum effect, x = concentration, and s = asymmetry.",
                    "gap": True,
                    "gap_note": "The equations are printed with garbled layout. This reading (the standard 5PL with the minimum removed, parameterised by EC50) is the extractor's reconstruction.",
                },
                {
                    "id": "S3",
                    "description": "Fitting constraints: EC50 > 0; 0.1 < s < 10; max fixed at 100. Initial values estimated automatically.",
                    "source_sentence": "The constraints used for fitting were: a) EC50 > 0, b) 0.1 < s < 10, c) max = 100.",
                    "gap": False,
                },
                {
                    "id": "S4",
                    "description": "From each fit: EC25, EC50, EC75 (concentrations giving 25, 50 and 75 % effect on the fitted curve), slope, s, maximum effect and r2 (coefficient of determination).",
                    "source_sentence": "The following values were calculated for A, B and MX at each exposure duration: EC25, EC50, EC75, slope, s, maximum effect, and coefficient of determination (r2).",
                    "gap": True,
                    "gap_note": "'Slope' is not defined further; the Hill slope parameter of Eq. 1 is the natural reading. The r2 definition (1 − SSres/SStot over all points) is not stated.",
                },
                {
                    "id": "S5",
                    "description": "Time-dependent toxicity per test, from its 15- and 45-min EC50s: TDT = ((EC50_15 − EC50_45) / (EC50_15 × 0.667)) × 100.",
                    "source_sentence": "TDT = ((15minEC50 − 45minEC50)/(15minEC50 × 0.667)) × 100",
                    "gap": False,
                },
                {
                    "id": "S6",
                    "description": "Across the 31 M2CA-alone tests, for each quantity and time: mean, standard deviation, CV = SD/mean × 100, range, and Shapiro-Wilk W.",
                    "source_sentence": "The repeatability of the M2CA tests was assessed by calculating the mean, standard deviation, coefficient of variation (CV), range, and Shapiro-Wilk W values for each ECx, slope, s, r2, and TDT value.",
                    "gap": True,
                    "gap_note": "The SD denominator (n − 1 or n) is not stated, and neither is whether 'range' is max − min or the min-max interval (the table prints one number).",
                },
            ],
        }
    ],
}

PARAMS = [("ec25", "EC25 (µM)", "µM"), ("ec50", "EC50 (µM)", "µM"), ("ec75", "EC75 (µM)", "µM"),
          ("slope", "Slope", None), ("s", "s (asymmetry)", None), ("r2", "r2", None)]
PUBLISHED = {  # mean, sd, cv, range, sw
    ("ec25", 15): ("4.07", "0.836", "20.6", "3.0", "0.942"), ("ec25", 30): ("1.84", "0.334", "18.1", "1.2", "0.956"),
    ("ec25", 45): ("1.11", "0.179", "16.1", "0.6", "0.964"),
    ("ec50", 15): ("9.64", "1.885", "19.5", "6.6", "0.937"), ("ec50", 30): ("4.48", "0.787", "17.6", "2.6", "0.941"),
    ("ec50", 45): ("2.74", "0.439", "16.0", "1.6", "0.959"),
    ("ec75", 15): ("21.16", "4.573", "21.6", "16.6", "0.932"), ("ec75", 30): ("9.59", "1.803", "18.8", "6.0", "0.933"),
    ("ec75", 45): ("5.93", "1.022", "17.2", "3.4", "0.934"),
    ("slope", 15): ("1.59", "0.172", "10.8", "0.73", "0.984"), ("slope", 30): ("1.75", "0.147", "8.4", "0.61", "0.981"),
    ("slope", 45): ("1.74", "0.155", "8.8", "0.71", "0.970"),
    ("s", 15): ("0.69", "0.210", "30.3", "1.03", "0.906"), ("s", 30): ("0.55", "0.084", "15.7", "0.34", "0.953"),
    ("s", 45): ("0.52", "0.079", "15.1", "0.30", "0.946"),
    ("r2", 15): ("0.9977", "0.002", "0.17", "0.009", "0.659"), ("r2", 30): ("0.9988", "0.001", "0.07", "0.004", "0.830"),
    ("r2", 45): ("0.9991", "0.001", "0.06", "0.003", "0.875"),
    ("tdt", "15-45"): ("107.1", "2.441", "2.3", "10.5", "0.990"),
}
COLUMNS = [
    {"id": "mean", "label": "Mean", "metric_type": "mean"},
    {"id": "sd", "label": "Std. dev.", "metric_type": "SD"},
    {"id": "cv", "label": "CV (%)", "metric_type": "CV"},
    {"id": "range", "label": "Range", "metric_type": "range"},
    {"id": "sw", "label": "SW-W (Shapiro-Wilk W)", "metric_type": "W"},
]


def decimals(raw):
    return len(raw.split(".")[1]) if "." in raw else 0


def main(out):
    out = Path(out)
    rows, tmpl, full = [], {}, {}
    for (pid, t), vals in PUBLISHED.items():
        label = dict((p[0], p[1]) for p in PARAMS).get(pid, "TDT (%)")
        unit = dict((p[0], p[2]) for p in PARAMS).get(pid)
        rid = f"{pid}_{t}".replace("-", "_")
        rows.append({"id": rid, "label": f"{label}, {t} min"})
        for col, raw in zip(COLUMNS, vals):
            u = unit if col["id"] in ("mean", "sd", "range") else None
            key = f"{rid}|{col['id']}"
            tmpl[key] = {"metric_type": col["metric_type"], "unit": u, "link_to": None, "value": None, "stars": None}
            full[key] = {"raw": raw, "metric_type": col["metric_type"], "unit": u, "stars": None, "link_to": None,
                         "comparator": None, "value": float(raw), "decimals": decimals(raw), "graded": True}
    caption = "Table 2. " + METHODS["tables"][0]["caption"]
    template = {"paper": "B", "table_id": "Table 2", "caption": caption, "rows": rows, "columns": COLUMNS,
                "star_legend": None, "cells": tmpl,
                "instructions": "Fill `value` (a number) for every cell and set `stars` to '' (the table prints none). `unit` gives the unit the table uses for that cell; concentrations are M2CA in µM."}
    tables_full = {"paper": "B", "table_id": "Table 2", "caption": caption, "rows": rows, "columns": COLUMNS,
                   "excluded_columns": [],
                   "footnotes": ["a CV: coefficient of variation = std. dev./mean * 100 b SW-W: Shapiro-Wilk test c concentrations are M2CA-equivalent in µM d s: asymmetry e TDT: time-dependent toxicity value at EC50"],
                   "star_legend": None, "cells": full}
    for name, obj in (("methods.json", METHODS), ("template.json", template), ("tables_full.json", tables_full)):
        (out / name).write_text(json.dumps(obj, indent=1, ensure_ascii=False), encoding="utf-8")
    print(len(full), "cells")


if __name__ == "__main__":
    main(sys.argv[1])
