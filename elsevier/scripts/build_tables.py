"""Step 1.3: parse the published target tables into tables_full.json and blind them into template.json.

Published values were transcribed from the PDF tables (checked against a 200-dpi render of each page).
Each cell keeps the printed string (`raw`) so grading can round to the reported precision.

Usage: python -I build_tables.py <work_dir>
"""
import copy
import json
import re
import sys
from pathlib import Path


def cell(raw, metric_type, unit, stars=None, link_to=None, graded=True):
    """Build one cell from its printed string. Handles '<0.001', '>10000', 'N/A', 'n.d.'."""
    c = {"raw": raw, "metric_type": metric_type, "unit": unit, "stars": stars,
         "link_to": link_to, "comparator": None, "value": None, "decimals": None, "graded": graded}
    if raw is None:  # nothing printed in this slot
        c["graded"] = False
        return c
    m = re.fullmatch(r"([<>])?\s*(-?[\d.]+)", raw.replace("−", "-"))
    if m:
        c["comparator"] = m.group(1)
        num = m.group(2)
        c["value"] = float(num)
        c["decimals"] = len(num.split(".")[1]) if "." in num else 0
    else:
        c["graded"] = False  # 'N/A', 'n.d.' etc.
    return c


def paper_a():
    cols = [("med_b", "Median baseline", "median"), ("med_f", "Median 6 years", "median"),
            ("p", "P value", "p"), ("srm", "SRM", "SRM")]
    # id, label, unit, footnote marks, median baseline, median 6y, P, P-mark, SRM
    rows = [
        ("fvc_sit", "Forced vital capacity sitting (%)", "%", "c", "77", "64", "0.001", "a", "-1.29"),
        ("fvc_lie", "Forced vital capacity lying (%)", "%", "d", "70", "54", "0.002", "a", "-1.06"),
        ("hip_flex", "Hip flexion (kg)", "kg", "", "7.7", "6.4", "0.13", None, "-0.35"),
        ("hip_add", "Hip adduction (kg)", "kg", "", "6.1", "4.2", "0.02", "a", "-0.59"),
        ("hip_abd", "Hip abduction (kg)", "kg", "", "8.3", "7.2", "0.76", None, "-0.01"),
        ("knee_ext", "Knee extension (kg)", "kg", "", "11.1", "12.0", "0.15", None, "-0.26"),
        ("knee_flex", "Knee flexion (kg)", "kg", "", "8.4", "4.8", "0.21", None, "-0.12"),
        ("ankle_df", "Ankle dorsiflexion (kg)", "kg", "", "14.7", "13.9", "0.07", None, "-0.42"),
        ("smwt", "Six-minute walk (meters)", "m", "", "391", "286", "0.001", "a", "-0.85"),
        ("tug", "Timed up and go velocity (msec-1)", "m/s", "e", "0.5", "0.3", "0.007", "a", "-0.48"),
        ("tmwr", "Ten-meter walk or run velocity (msec-1)", "m/s", "e", "1.2", "0.8", "<0.001", "a", "-1.02"),
        ("stair_up", "Stair ascent velocity (steps/sec)", "steps/s", "e", "0.7", "0.4", "0.001", "a", "-0.46"),
        ("stair_down", "Stair descent velocity (steps/sec)", "steps/s", "e", "1.2", "0.4", "0.008", "a", "-0.47"),
        ("chair", "Chair rise (sec)", "s", "bc", "2.6", "9.8", "0.001", "a", "N/A"),
    ]
    cells = {}
    for rid, _, unit, _, mb, mf, p, pmark, srm in rows:
        cells[f"{rid}|med_b"] = cell(mb, "median", unit)
        cells[f"{rid}|med_f"] = cell(mf, "median", unit)
        cells[f"{rid}|p"] = cell(p, "p", None, stars=pmark or "")
        cells[f"{rid}|srm"] = cell(srm, "SRM", None)
    return {
        "paper": "A",
        "table_id": "Table 1",
        "caption": "Table 1. The median change in functional assessments over the follow-up of 6 years.",
        "rows": [{"id": r[0], "label": r[1], "footnote_marks": r[3]} for r in rows],
        "columns": [{"id": c[0], "label": c[1], "metric_type": c[2]} for c in cols],
        "excluded_columns": ["(range) under each median: not part of the graded grid"],
        "footnotes": {
            "general": "P values calculated using Wilcoxon nonparametric rank signed test. SRM - standardized response mean.",
            "a": "P value <0.05.",
            "b": "Participants unable to perform the chair rise were given a value of 10,000 (effectively infinity) for the purposes of the Wilcoxon nonparametric rank signed test.",
            "c": "Paired values available in 17 participants.",
            "d": "Paired values available in 16 participants.",
            "e": "Paired values available in 22 participants.",
        },
        "star_legend": {"a": "P < 0.05"},
        "cells": cells,
    }


def paper_b():
    cols = [("camp_pec50", "cAMP pEC50", "pEC50"), ("camp_pec50_se", "cAMP pEC50 ±", "pm"),
            ("camp_ec50", "cAMP EC50 (nM), in parentheses", "EC50"),
            ("camp_emax", "cAMP Emax (Fold)", "Emax"), ("camp_emax_se", "cAMP Emax ±", "pm"),
            ("camp_hill", "cAMP Hill slope", "Hill"), ("camp_hill_se", "cAMP Hill slope ±", "pm"),
            ("arr_pec50", "βarrestin2 pEC50", "pEC50"), ("arr_pec50_se", "βarrestin2 pEC50 ±", "pm"),
            ("arr_ec50", "βarrestin2 EC50 (nM), in parentheses", "EC50"),
            ("arr_emax", "βarrestin2 Emax (Fold)", "Emax"), ("arr_emax_se", "βarrestin2 Emax ±", "pm"),
            ("arr_hill", "βarrestin2 Hill slope", "Hill"), ("arr_hill_se", "βarrestin2 Hill slope ±", "pm")]
    units = {"pEC50": None, "EC50": "nM", "Emax": "fold", "Hill": None}
    # Printed table, row by row. None = slot empty in print (e.g. no +/- shown).
    printed = {
        "ox_000": ["8.8", "0.45", "1.5", "0.79", "0.03", "-1.7", "3.6",
                   "<5", None, ">10000", "17", "4.6", "n.d.", None],
        "ox_010": ["8.1", "0.24", "7.2", "0.57", "0.03", "-1.2", "0.90",
                   "5.5", "1.4", "3000", "5.7", "3.2", "0.41", "0.23"],
        "ox_025": ["7.9", "0.16", "12", "0.52", "0.03", "-0.77", "0.22",
                   "6.0", "0.26", "960", "5.6", "0.63", "0.46", "0.08"],
        "ox_050": ["7.9", "0.33", "11", "0.69", "0.03", "-1", None,
                   "6.4", "0.068", "400", "6.4", "0.21", "0.70", "0.06"],
    }
    stars = {("ox_010", "camp_emax"): "**", ("ox_025", "camp_emax"): "***"}
    # Footnote marks printed on cells (part of the published table, blinded in the template)
    marks = {("ox_050", "camp_pec50"): "a", ("ox_050", "camp_emax"): "a", ("ox_050", "camp_hill"): "a",
             ("ox_000", "arr_emax"): "b"}
    cells = {}
    for rid, vals in printed.items():
        for (cid, _, mt), raw in zip(cols, vals):
            if mt == "pm":
                est = cid[:-3]
                c = cell(raw, "pm", units[[m for k, _, m in cols if k == est][0]], link_to=f"{rid}|{est}")
            else:
                c = cell(raw, mt, units[mt])
            if mt in ("Emax",):
                c["stars"] = stars.get((rid, cid), "")
            c["footnote_mark"] = marks.get((rid, cid))
            cells[f"{rid}|{cid}"] = c
    return {
        "paper": "B",
        "table_id": "Table 1",
        "caption": "TABLE 1 | CB1-dependent inhibition of cAMP and recruitment of βarrestin2 in CB1-OX1 cells.",
        "rows": [{"id": "ox_000", "label": "[OX1] 0.00 µg"}, {"id": "ox_010", "label": "[OX1] 0.10 µg"},
                 {"id": "ox_025", "label": "[OX1] 0.25 µg"}, {"id": "ox_050", "label": "[OX1] 0.50 µg"}],
        "columns": [{"id": c[0], "label": c[1], "metric_type": c[2]} for c in cols],
        "printed_header": "[OX1] (µg) | cAMP: pEC50 (nM), Emax (Fold), Hill slope | βarrestin2: pEC50 (nM), Emax (Fold)b, Hill slope",
        "footnotes": {
            "note": "Data were fit to a 4-parameter non-linear regression to estimate potency (pEC50) and efficacy (Emax) values. Data are expressed as mean±SEM. n=4-8 independent experiments performed in triplicate. Statistical analyses were by one-way ANOVA followed by Tukey's post hoc test. Data presented in the Table relate to Figure 2.",
            "n.d.": "not determined",
            "**": "p < 0.01 relative to CP55,940.",
            "***": "p < 0.001 relative to CP55,940.",
            "a": "When fit to a 4-parameter model, pEC50 and Hill Slope could not be accurately estimated, data in table are for a Hill Slope constrained to 1.",
            "b": "Emax data represent the experimentally observed value because CRC did not reach a clearly defined maximum asymptote; for this reason EC50 is reported as >10000nM.",
        },
        "star_legend": {"**": "p < 0.01", "***": "p < 0.001"},
        "cells": cells,
    }


def blind(full):
    """Template: same grid and labels, every value/star/mark nulled. Footnotes that explain
    specific cells are dropped (they are part of the published result)."""
    t = copy.deepcopy(full)
    for c in t["cells"].values():
        for k in ("raw", "value", "decimals", "comparator", "stars", "footnote_mark", "graded"):
            c.pop(k, None)
        c["value"] = None
        c["stars"] = None
    t.pop("footnotes", None)
    t.pop("excluded_columns", None)
    t.pop("printed_header", None)
    for r in t["rows"]:
        r.pop("footnote_marks", None)
    t["instructions"] = ("Fill `value` (a number; or a string such as '<x' or '>x' for a bound, 'n.d.' or 'N/A' if a number "
                         "cannot be estimated) and `stars` (significance marker you would print, or '') for every "
                         "cell. `unit` gives the unit the table uses for that cell.")
    return t


def main(work):
    work = Path(work)
    for paper, build in (("paperA", paper_a), ("paperB", paper_b)):
        full = build()
        out = work / paper / "extract"
        (out / "tables_full.json").write_text(json.dumps(full, indent=1, ensure_ascii=False), encoding="utf-8")
        (out / "template.json").write_text(json.dumps(blind(full), indent=1, ensure_ascii=False), encoding="utf-8")
        n = sum(c["graded"] for c in full["cells"].values())
        print(paper, "cells:", len(full["cells"]), "graded:", n)


if __name__ == "__main__":
    main(sys.argv[1])
