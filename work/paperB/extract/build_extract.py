"""Write methods.json, template.json and tables_full.json for Paper B (Scientific Reports 2023, aerosol extracts, Table 2).

Every source_sentence is copied from source/paper.txt (checked by scripts/verify_sources.py).
tables_full.json holds the published values and never goes into a sandbox.

Usage: python -I build_extract.py <extract_dir>
"""
import json
import sys
from pathlib import Path

CITATION = ("Varied effects of tobacco smoke and e-cigarette vapor suggest that nicotine does not affect endothelium-dependent "
            "relaxation. Scientific Reports 2023;13:15833. doi:10.1038/s41598-023-42750-6")

METHODS = {
    "paper": "B",
    "citation": CITATION,
    "research_question": {
        "id": "RQ",
        "text": "Do aqueous extracts of tobacco smoke (CSE), e-cigarette vapour (EVE) and heated tobacco aerosol (HTE) impair endothelium-dependent relaxation? Table 2: rat aorta relaxation to acetylcholine (endothelium-dependent) and DEA/NO (NO donor) after 24 h incubation with each extract.",
        "source_sentence": "Rings with intact endothelium obtained from one vessel were preincubated in DMEM alone or different CSE, EVE, or HTE dilutions for 24 h at 37 °C and 5% CO2.",
        "gap": False,
    },
    "setting": {
        "id": "SET",
        "population": "Rat aortic rings, 5 experiments per treatment; three extract series (CSE, EVE, HTE), each with its own DMEM control.",
        "period": "Not relevant.",
        "site": "Isometric tension, organ baths.",
        "source_sentence": "Rings were randomly assigned to the different incubation protocols to avoid any systematic effects due to the repeated use of similar vessel segments.",
        "gap": False,
    },
    "data_sources": [
        {
            "id": "D1",
            "name": "Zenodo deposit by the authors",
            "summary": "Per experiment: tension remaining (% of precontraction) at 9 concentrations of acetylcholine and of DEA/NO, for every treatment of the CSE, EVE and HTE series.",
            "source_sentence": "Cumulative concentration–response curves to acetylcholine (1 nM–10 µM) or DEA/NO (1 nM–10 µM) were performed with rings that had been pre-contracted with 9,11-dideoxy-9α,11α-epoxy-methanoprostaglandin F2α (U-46619;~90% of maximal contraction).",
            "gap": False,
        }
    ],
    "general_manipulations": [
        {
            "id": "M1",
            "description": "Relaxation is expressed as percent reversal of the U-46619 precontraction (relaxation % = 100 − tension remaining as % of precontraction).",
            "source_sentence": "Relaxation responses are expressed as percent reversal of U-46619 or K+-induced precontraction.",
            "gap": False,
        },
        {
            "id": "M2",
            "description": "Curves from different rings of one animal are averaged and counted as one experiment (the deposit already holds one curve per experiment).",
            "source_sentence": "Concentration–response curves of dif­ferent ring segments from a single animal were averaged and counted as an individual experiment.",
            "gap": False,
        },
    ],
    "tables": [
        {
            "id": "T2",
            "name": "Table 2",
            "caption": "Effects of CSE, EVE, and HTE on relaxation of rat aortas to acetylcholine and DEA/NO. Data shown are mean values±SEM (Emax) or mean values with 95% confidence interval (EC50) from 5 experiments. *p<0.05 vs. control as determined by ANOVA and Dunnett’s post hoc test.",
            "row_labels": [],
            "column_labels": [],
            "table_specific_filters": [],
            "specification": [
                {
                    "id": "S1",
                    "description": "Emax (maximal relaxation, %) and EC50 are obtained by fitting each concentration-response curve to a Hill-type model.",
                    "source_sentence": "Maximal effects (Emax and vmax) and half-maximal effective concentrations (EC50 values) were obtained by fitting concentration–response curves to a Hill-type model using Kaleidagraph (Synergy Software, version 4.5).",
                    "software": "Kaleidagraph 4.5",
                    "gap": True,
                    "gap_note": "The exact Hill-type equation (whether the baseline is fixed at 0 % relaxation, whether the Hill slope is free), and whether each experiment's curve is fitted separately or the mean curve is fitted, are not stated.",
                },
                {
                    "id": "S2",
                    "description": "Emax: mean ± SEM over the 5 experiments.",
                    "source_sentence": "Results are presented as mean values±SEM of n experiments.",
                    "gap": False,
                },
                {
                    "id": "S3",
                    "description": "EC50: geometric mean over the 5 experiments with its 95% confidence limits.",
                    "source_sentence": "EC50 values are reported as geometric means with 95% confidence limits.",
                    "gap": True,
                    "gap_note": "How the 95% limits are computed (t or normal quantile on the log EC50s, which log base) is not stated.",
                },
                {
                    "id": "S4",
                    "description": "Each treatment is compared with its series' control by one-way ANOVA with Dunnett's post hoc test; * marks p < 0.05.",
                    "source_sentence": "Paired Student’s t-test or analysis of variance (ANOVA) with Dunnett’s post hoc test was used to compare groups using Kaleidagraph software.",
                    "gap": True,
                    "gap_note": "Which test applies to which comparison is not stated beyond the table caption (ANOVA and Dunnett vs control).",
                },
            ],
        }
    ],
}

# row id, label, ACh Emax, ACh SEM, ACh EC50, lo, hi, DEA Emax, DEA SEM, DEA EC50, lo, hi, ACh star
ROWS = [
    ("cse_ctrl", "CSE series: Control", "59", "3.8", "170", "94", "307", "96", "2.1", "60", "38", "94", ""),
    ("cse_3", "CSE 1:3", "17", "3.8", "806", "233", "2790", "97", "1.7", "95", "49", "187", "*"),
    ("cse_20", "CSE 1:20", "34", "3.4", "190", "93", "390", "98", "1.2", "69", "29", "168", "*"),
    ("cse_200", "CSE 1:200", "56", "2.7", "335", "144", "777", "97", "0.9", "80", "43", "150", ""),
    ("eve_ctrl", "EVE series: Control", "57", "5.7", "150", "89", "251", "96", "1.9", "63", "28", "141", ""),
    ("eve_undil", "EVE undiluted", "50", "4.2", "190", "67", "537", "98", "0.9", "44", "26", "74", ""),
    ("eve_2", "EVE 1:2", "64", "8.1", "166", "131", "210", "95", "3.3", "53", "21", "135", ""),
    ("eve_20", "EVE 1:20", "60", "4.6", "180", "89", "365", "99", "0.5", "58", "34", "100", ""),
    ("hte_ctrl", "HTE series: Control", "63", "5.0", "109", "50", "238", "94", "1.6", "46", "19", "112", ""),
    ("hte_undil", "HTE (THP) undiluted", "37", "5.5", "278", "84", "925", "96", "1.4", "87", "21", "362", "*"),
    ("hte_2", "HTE (THP) 1:2", "49", "6.2", "146", "62", "345", "96", "1.6", "90", "41", "201", ""),
    ("hte_20", "HTE (THP) 1:20", "64", "4.7", "167", "54", "514", "95", "1.9", "76", "37", "159", ""),
]
COLS = [("ach_emax", "Acetylcholine Emax (%)", "Emax", "%"), ("ach_sem", "Acetylcholine Emax SEM", "SEM", "%"),
        ("ach_ec50", "Acetylcholine EC50 (nM)", "EC50", "nM"), ("ach_lo", "Acetylcholine EC50 95% CI lower (nM)", "CI", "nM"),
        ("ach_hi", "Acetylcholine EC50 95% CI upper (nM)", "CI", "nM"),
        ("dea_emax", "DEA/NO Emax (%)", "Emax", "%"), ("dea_sem", "DEA/NO Emax SEM", "SEM", "%"),
        ("dea_ec50", "DEA/NO EC50 (nM)", "EC50", "nM"), ("dea_lo", "DEA/NO EC50 95% CI lower (nM)", "CI", "nM"),
        ("dea_hi", "DEA/NO EC50 95% CI upper (nM)", "CI", "nM")]
COLUMNS = [{"id": c[0], "label": c[1], "metric_type": c[2]} for c in COLS]
STAR_LEGEND = {"*": "p<0.05 vs. control of the same series (ANOVA and Dunnett's post hoc test)"}


def decimals(raw):
    return len(raw.split(".")[1]) if "." in raw else 0


def main(out):
    out = Path(out)
    rows, tmpl, full = [], {}, {}
    for rid, label, *vals in ROWS:
        star = vals.pop()
        rows.append({"id": rid, "label": label})
        for (cid, _, mtype, unit), raw in zip(COLS, vals):
            key = f"{rid}|{cid}"
            stars = (star if cid == "ach_emax" else "") if cid.endswith("emax") else None
            tmpl[key] = {"metric_type": mtype, "unit": unit, "link_to": None, "value": None, "stars": None}
            full[key] = {"raw": raw, "metric_type": mtype, "unit": unit, "stars": stars, "link_to": None,
                         "comparator": None, "value": float(raw), "decimals": decimals(raw), "graded": True}
    caption = "Table 2. " + METHODS["tables"][0]["caption"]
    template = {"paper": "B", "table_id": "Table 2", "caption": caption, "rows": rows, "columns": COLUMNS,
                "star_legend": STAR_LEGEND, "cells": tmpl,
                "instructions": "Fill `value` (a number) for every cell. On the two Emax columns set `stars` to '*' where the treatment differs from its series' control at p<0.05 (ANOVA and Dunnett), else ''; elsewhere set `stars` to ''. `unit` gives the unit the table uses (EC50 in nM, Emax as % relaxation)."}
    tables_full = {"paper": "B", "table_id": "Table 2", "caption": caption, "rows": rows, "columns": COLUMNS,
                   "excluded_columns": ["Nicotine µg/ml (a property of the extract, not computed from the curves)"],
                   "footnotes": ["*p<0.05 vs. control as determined by ANOVA and Dunnett’s post hoc test."],
                   "star_legend": STAR_LEGEND, "cells": full}
    for name, obj in (("methods.json", METHODS), ("template.json", template), ("tables_full.json", tables_full)):
        (out / name).write_text(json.dumps(obj, indent=1, ensure_ascii=False), encoding="utf-8")
    print(len(full), "cells")


if __name__ == "__main__":
    main(sys.argv[1])
