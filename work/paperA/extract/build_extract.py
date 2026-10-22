"""Write methods.json, template.json and tables_full.json for Paper A (BMC Pediatrics 2024, HFNC vs NIV, Table 1).

Every source_sentence is copied from source/paper.txt (checked by scripts/verify_sources.py).
tables_full.json holds the published values and never goes into a sandbox.

Rows whose inputs were de-identified into ranges in the deposit (age, weight z score, PICU and hospital
length of stay) and the ventilator-associated pneumonia row (no column in the deposit) are kept in the
table but not graded.

Usage: python -I build_extract.py <extract_dir>
"""
import json
import sys
from pathlib import Path

CITATION = ("Santos ACEZ et al. Comparison between high-flow nasal cannula (HFNC) therapy and noninvasive ventilation (NIV) "
            "in children with acute respiratory failure by bronchiolitis: a randomized controlled trial. BMC Pediatr "
            "2024;24:595. doi:10.1186/s12887-024-05058-6")

METHODS = {
    "paper": "A",
    "citation": CITATION,
    "research_question": {
        "id": "RQ",
        "text": "Is high-flow nasal cannula (HFNC) therapy non-inferior to noninvasive ventilation (NIV) for children under 2 with bronchiolitis and mild to moderate respiratory distress? Table 1 compares the two randomised groups.",
        "source_sentence": "The primary outcome analyzed was invasive mechanical ventilation requirement.",
        "gap": False,
    },
    "setting": {
        "id": "SET",
        "population": "Children under 2 years admitted for bronchiolitis with mild to moderate respiratory distress (Wood-Downes-Férres score < 8), randomised to HFNC or NIV; 126 analysed per group.",
        "period": "February 2021 to May 2023.",
        "site": "Single tertiary centre, Brazil.",
        "source_sentence": "The inclusion criteria were children under 2 years of age admitted for bronchiolitis that progressed to mild to moderate respiratory distress (WDF score<8 points) during hospitalization.",
        "gap": False,
    },
    "data_sources": [
        {
            "id": "D1",
            "name": "Dryad dataset deposited by the authors",
            "summary": "One row per analysed patient (252): group, sex, history, viral panel, device duration, vital signs and settings at 0-96 h, sedation and enteral tube days, length of stay, ventilation days, antibiotics, PIM 2. Age, weight and lengths of stay are given only as ranges.",
            "source_sentence": "Vital signs, WDF score, peripheral oxygen saturation (SpO2), and FiO2 were recorded at 0 h, 2 h, 6 h, 12 h, 24 h, 48 h, 72 h and 96 h after HFNC therapy or NIV therapy initiation.",
            "gap": False,
        }
    ],
    "general_manipulations": [
        {
            "id": "M1",
            "description": "Analysed groups: 126 NIV and 126 HFNC after exclusions; every deposited row is an analysed patient.",
            "source_sentence": "Of these, six patients were excluded from the NIV group, and 10 were excluded from the HFNC group, totaling 126 patients in the NIV group and 126 patients in the HFNC group.",
            "gap": False,
        },
        {
            "id": "M2",
            "description": "Missing data: complete-case analysis, no imputation.",
            "source_sentence": "The standard method was applied for missing data, which is the analysis of complete cases not using any replacement or imputation technique [32].",
            "gap": True,
            "gap_note": "Percentages could use the whole group (126) or only patients with a recorded value as denominator; the paper does not say which.",
        },
        {
            "id": "M3",
            "description": "Variables recorded per patient include sex, previous respiratory hospitalization, PIM 2, viral panel, antibiotics, sedative usage, HFNC/NIV duration, invasive ventilation duration and lengths of stay.",
            "source_sentence": "The variables assessed included age, weight, sex, comorbidities, previous respiratory hospitalization, the Pediatric Index of Mortality – version 2 (PIM 2) score, viral panel results, the need for antibiotics, nasal septum injury status, sedative usage, HFNC/NIV duration, invasive mechanical ventilation duration, PICU length of stay (LOS), the hospital LOS, and the mortality rate [22–24].",
            "gap": True,
            "gap_note": "How 'sedation (N, %)' is derived is not stated (the deposit has sedation duration in days, not a yes/no flag). 'Initial' values are taken to be the 0 h readings.",
        },
    ],
    "tables": [
        {
            "id": "T1",
            "name": "Table 1",
            "caption": "Demographic and clinical characteristics",
            "row_labels": [],
            "column_labels": [],
            "table_specific_filters": [],
            "specification": [
                {
                    "id": "S1",
                    "description": "Distributions compared with the Wilcoxon/Mann-Whitney test.",
                    "source_sentence": "To compare distri­butions between groups, the Wilcoxon/Mann‒Whitney test was used, and the chi‒square test was used to com­pare frequencies between groups.",
                    "software": "R",
                    "gap": True,
                    "gap_note": "Exact or normal-approximation Mann-Whitney, continuity correction, and whether chi-square uses Yates' correction (R's chisq.test default for 2x2 tables) are not stated. The table footnote says p values come from chi-square or Wilcoxon 'as appropriate', so mean (SD) rows also use one of these.",
                },
                {
                    "id": "S2",
                    "description": "Summaries per row as printed in the table: N (%), mean (SD), or median (IQR, 25th-75th percentile).",
                    "source_sentence": "The statistical analyses were performed using R: A language and environment for statistical computing (R Foundation for Statistical Computing, Vienna, Austria) [31].",
                    "software": "R",
                    "gap": True,
                    "gap_note": "The quantile method for the IQR is not stated (R's default is type 7).",
                },
            ],
        }
    ],
}

# id, label, kind, NIV cells, HFNC cells, p, graded
#   kind n: (n, pct); mean: (mean, sd); median: (median, q1, q3); virus: (n, pct) without p
ROWS = [
    ("age", "Age (months), median (IQR)", "median", ("2.5", "1", "6"), ("3", "2", "7"), "0.07", False),
    ("wz", "Weight z score for age, mean (SD)", "mean", ("-0.18", "1.18"), ("-0.18", "1.11"), "0.95", False),
    ("female", "Female, N (%)", "n", ("52", "41"), ("41", "32.5"), "0.15", True),
    ("pw", "Previous wheezing, N (%)", "n", ("39", "31"), ("32", "25.3"), "0.3", True),
    ("prh", "Previous respiratory hospitalization, N (%)", "n", ("30", "23.8"), ("22", "17.4"), "0.2", True),
    ("dur", "NIV/HFNC duration (hours), median (IQR)", "median", ("48", "24", "78"), ("77.5", "46.5", "108"), "0.0003", True),
    ("fio2", "Initial FiO2, mean (SD)", "mean", ("40.8", "10.8"), ("36.2", "10.6"), "0.0002", True),
    ("wdf", "Initial WDF, mean (SD)", "mean", ("5.9", "0.9"), ("5.9", "1.1"), "0.9", True),
    ("spo2", "Initial SpO2, mean (SD)", "mean", ("97.6", "1.9"), ("97.4", "1.9"), "0.25", True),
    ("sed", "Sedation, N (%)", "n", ("121", "96"), ("54", "42.8"), "<0.001", True),
    ("sed_d", "Sedation (days), median (IQR)", "median", ("3", "2", "4"), ("2", "1", "4"), "0.08", True),
    ("ngt_d", "Nasogastric tube (days), median (IQR)", "median", ("3", "2", "4"), ("4", "2", "5"), "0.012", True),
    ("picu", "PICU LOS (days), median (IQR)", "median", ("5", "3", "10"), ("5", "4", "7"), "0.3", False),
    ("hosp", "Hospital LOS (days), median (IQR)", "median", ("9", "6", "14"), ("8", "6", "10"), "0.006", False),
    ("imv_d", "Invasive mechanical ventilation duration (days), median (IQR)", "median", ("5", "3.7", "7"), ("4", "2.5", "4.5"), "0.02", True),
    ("atb", "Antibiotic use, n (%)", "n", ("62", "49"), ("49", "38"), "<0.001", True),
    ("vap", "Ventilator-associated pneumonia, n (%)", "virus", ("1", "2"), ("1", "3.4"), None, False),
    ("pim", "PIM 2 score, mean (SD)", "mean", ("1.8", "1.7"), ("1.5", "1.4"), "0.49", True),
    ("v_rsv", "Virus: Respiratory syncytial virus, n (%)", "virus", ("91", "72.2"), ("90", "71.4"), None, True),
    ("v_bo", "Virus: Bocavirus, n (%)", "virus", ("4", "3.2"), ("11", "8.7"), None, True),
    ("v_ad", "Virus: Adenovirus, n (%)", "virus", ("6", "4.8"), ("9", "7.1"), None, True),
    ("v_sc", "Virus: Seasonal coronavirus, n (%)", "virus", ("4", "3.2"), ("8", "6.3"), None, True),
    ("v_pa", "Virus: Parainfluenza 3/4, n (%)", "virus", ("7", "5.6"), ("5", "4"), None, True),
    ("v_me", "Virus: Human metapneumovirus, n (%)", "virus", ("5", "4"), ("4", "3.2"), None, True),
    ("v_re", "Virus: Rhinovirus/enterovirus, n (%)", "virus", ("2", "1.6"), ("2", "1.6"), None, True),
]
SLOTS = {"n": (("n", "count", None), ("pct", "percent", "%")), "virus": (("n", "count", None), ("pct", "percent", "%")),
         "mean": (("mean", "mean", None), ("sd", "SD", None)),
         "median": (("med", "median", None), ("q1", "Q1", None), ("q3", "Q3", None))}
COLUMNS = [{"id": f"{g}_{s}", "label": f"{g.upper()} {lab}", "metric_type": s}
           for g in ("niv", "hfnc") for s, lab in (("n", "N"), ("pct", "%"), ("mean", "mean"), ("sd", "SD"),
                                                   ("med", "median"), ("q1", "Q1 (25th pct)"), ("q3", "Q3 (75th pct)"))]
COLUMNS.append({"id": "p", "label": "p", "metric_type": "p"})
UNGRADED_REASON = {"age": "age deposited only as ranges", "wz": "weight deposited only as ranges",
                   "picu": "PICU LOS deposited only as ranges", "hosp": "hospital LOS deposited only as ranges",
                   "vap": "no ventilator-associated pneumonia column in the deposit"}


def decimals(raw):
    return len(raw.split(".")[1]) if "." in raw else 0


def main(out):
    out = Path(out)
    rows, tmpl, full = [], {}, {}
    for rid, label, kind, niv, hfnc, p, graded in ROWS:
        rows.append({"id": rid, "label": label})
        cells = [(f"{g}_{slot[0]}", slot, raw) for g, vals in (("niv", niv), ("hfnc", hfnc)) for slot, raw in zip(SLOTS[kind], vals)]
        if p is not None:
            cells.append(("p", ("p", "p", None), p))
        for col, slot, raw in cells:
            key = f"{rid}|{col}"
            if graded:
                tmpl[key] = {"metric_type": slot[1], "unit": slot[2], "link_to": None, "value": None, "stars": None}
            comp = "<" if raw.startswith("<") else None
            full[key] = {"raw": raw, "metric_type": slot[1], "unit": slot[2], "stars": None, "link_to": None,
                         "comparator": comp, "value": float(raw.lstrip("<")), "decimals": decimals(raw.lstrip("<")),
                         "graded": graded, **({} if graded else {"not_graded_reason": UNGRADED_REASON[rid]})}
    caption = "Table 1. " + METHODS["tables"][0]["caption"]
    template = {"paper": "A", "table_id": "Table 1", "caption": caption,
                "rows": [r for r in rows if any(k.startswith(r["id"] + "|") for k in tmpl)],
                "columns": COLUMNS, "star_legend": None, "cells": tmpl,
                "instructions": "Fill `value` (a number, or a string such as '<x' for a bound) for every cell listed and set `stars` to ''. Cell keys are '<row>|<group>_<statistic>' (group niv or hfnc; statistic n, pct, mean, sd, med, q1, q3) or '<row>|p'. `unit` '%' means a percentage of the group."}
    tables_full = {"paper": "A", "table_id": "Table 1", "caption": caption, "rows": rows, "columns": COLUMNS,
                   "excluded_columns": [],
                   "footnotes": ["SD: standard deviation", "IQR: interquartile range 0.25–0.75",
                                 "p values were calculated by chi-square or Wilcoxon tests, as appropriate"],
                   "star_legend": None, "cells": full}
    for name, obj in (("methods.json", METHODS), ("template.json", template), ("tables_full.json", tables_full)):
        (out / name).write_text(json.dumps(obj, indent=1, ensure_ascii=False), encoding="utf-8")
    print(len(full), "cells,", len(tmpl), "graded")


if __name__ == "__main__":
    main(sys.argv[1])
