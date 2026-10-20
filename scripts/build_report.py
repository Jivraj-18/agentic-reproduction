"""Build report/index.html: one self-contained page (no external calls) from the pipeline outputs.

All numbers on the page come from grades.json, attribution.json, audit.json and the leak check;
the page only formats them.

Usage: python -I build_report.py <work_dir> <template.html> <out.html>
"""
import json
import sys
from pathlib import Path

META = {
    "A": {
        "title": "Natural history of limb girdle muscular dystrophy R9 over 6 years: searching for trial endpoints",
        "authors": "Murphy AP, Morrow J, Dahlqvist JR, et al.",
        "journal": "Annals of Clinical and Translational Neurology",
        "year": "2019; 6(6): 1033–1045",
        "field": "Clinical neurology",
        "doi": "10.1002/acn3.774",
        "dryad": "10.5061/dryad.f3r6799",
        "table": "Table 1. The median change in functional assessments over the follow-up of 6 years.",
        "why_table": "Every input is in the Dryad file, and the table carries several analyst choices that the Methods describe only loosely: who counts as a pair, how 'unable to perform' enters medians, which Wilcoxon variant, and the SRM convention.",
        "layout": [
            {"group": None, "cols": [
                {"label": "Median baseline", "fmt": "{med_b}"},
                {"label": "Median 6 years", "fmt": "{med_f}"},
                {"label": "P value", "fmt": "{p}"},
                {"label": "SRM", "fmt": "{srm}"}]}],
        "row_head": "Functional assessment",
    },
    "B": {
        "title": "In Vitro Signaling Properties of Cannabinoid and Orexin Receptors: How Orexin Receptors Influence Cannabinoid Receptor-Mediated Signaling",
        "authors": "Mohamed KA, Laprairie RB",
        "journal": "Pharmacology Research & Perspectives",
        "year": "2025; 13: e70078",
        "field": "Pharmacology",
        "doi": "10.1002/prp2.70078",
        "dryad": "10.5061/dryad.0cfxpnwcq",
        "table": "TABLE 1 | CB₁-dependent inhibition of cAMP and recruitment of βarrestin2 in CB₁-OX₁ cells.",
        "why_table": "A table of fitted concentration–response parameters (pEC50, EC50, Emax, Hill slope). Curve fitting involves many choices the Methods leave unstated: pooled or per-experiment fits, what ± means, when to fix the slope, and how Emax is defined for an inhibition curve.",
        "layout": [
            {"group": "cAMP", "cols": [
                {"label": "pEC50 (nM)", "fmt": "{camp_pec50} ± {camp_pec50_se} ({camp_ec50})"},
                {"label": "Emax (Fold)", "fmt": "{camp_emax} ± {camp_emax_se}"},
                {"label": "Hill slope", "fmt": "{camp_hill} ± {camp_hill_se}"}]},
            {"group": "βarrestin2", "cols": [
                {"label": "pEC50 (nM)", "fmt": "{arr_pec50} ± {arr_pec50_se} ({arr_ec50})"},
                {"label": "Emax (Fold)", "fmt": "{arr_emax} ± {arr_emax_se}"},
                {"label": "Hill slope", "fmt": "{arr_hill} ± {arr_hill_se}"}]}],
        "row_head": "[OX₁] (µg)",
    },
}


def load(p, default=None):
    p = Path(p)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else default


def flatten_methods(m):
    items = []
    def add(section, it, label=None):
        items.append({"section": section, "id": it.get("id"), "text": label or it.get("description") or it.get("text"),
                      "source": it.get("source_sentence"), "gap": it.get("gap", False), "gap_note": it.get("gap_note"),
                      "v2_change": it.get("v2_change")})
    add("Research question", m["research_question"])
    s = m["setting"]
    add("Setting", s, f"{s['population']} Period: {s['period'].rstrip('.')}. Site: {s['site']}")
    for d in m["data_sources"]:
        add("Data source", d, f"{d['name']}: {d['summary']}")
    for g in m["general_manipulations"]:
        add("Data preparation", g)
    for t in m["tables"]:
        for f in t.get("table_specific_filters", []):
            add("Table filter", f)
        for sp in t.get("specification", []):
            add("Table specification", sp)
    return items


def slim_cells(grades, full):
    out = {}
    for k, c in grades["cells"].items():
        pub = full["cells"][k]
        e = {"pub": pub["raw"], "graded": c["graded"], "mt": c["metric_type"], "unit": c["unit"],
             "pstars": pub.get("stars"), "mark": pub.get("footnote_mark"), "runs": {}}
        for r, g in c["runs"].items():
            e["runs"][r] = {"v": g.get("reproduced"), "raw": g.get("reproduced_raw"), "u": g.get("reproduced_unrounded"),
                            "g": g.get("grade"), "d": g.get("deviation_pct"), "s": g.get("stars"), "src": g.get("source")}
        if c["graded"]:
            m = c["median"]
            e["med"] = {"v": m.get("reproduced"), "raw": m.get("reproduced_raw"), "u": m.get("reproduced_unrounded"),
                        "g": m.get("grade"), "d": m.get("deviation_pct")}
            e["spread"] = c.get("run_spread_pct")
            e["mg"] = c["median_grade"]
            e["rg"] = c["run_grades"]
            e["err"] = c.get("published_error")
        out[k] = e
    return out


def paper_payload(work, pid, folder=None):
    d = Path(work) / (folder or f"paper{pid}")
    full = load(d / "extract/tables_full.json")
    grades = load(d / "eval/grades.json")
    audit = load(d / "eval/audit.json", {})
    leak = load(d / "eval/leak_final.json") or load(d / "eval/leak_preflight.json")
    assumptions = {}
    for sb in sorted((d / "sandbox").glob("r*")):
        p = sb / "out" / "assumptions.md"
        if p.exists():
            assumptions[sb.name] = p.read_text(encoding="utf-8")
    audits = {}
    for r, a in audit.items():
        pa, ha = a["path_audit"], a["hardcoding"]
        audits[r] = {"tool_calls": pa.get("tool_calls"), "accesses": pa.get("accesses"), "counts": pa.get("counts"),
                     "flagged": pa.get("flagged"), "literals": ha.get("numeric_literals"),
                     "hc_matches": ha.get("matches"), "hc_flagged": ha.get("flagged")}
    return {
        "meta": META[pid],
        "rows": full["rows"],
        "footnotes": full.get("footnotes", {}),
        "cells": slim_cells(grades, full),
        "summary": grades["summary"],
        "runs": grades["runs"],
        "methods": flatten_methods(load(d / "extract/methods.json")),
        "source_check": load(d / "eval/source_check.json"),
        "manifest": load(d / "extract/data_manifest.json"),
        "attribution": load(d / "eval/attribution.json", {"cells": [], "root_causes": []}),
        "audits": audits,
        "leak": {"pass": leak["pass"], "tokens": leak["published_tokens"], "answers": leak["answer_values"],
                 "unsearchable": leak.get("unsearchable_cells", []),
                 "per_run": {r: {"inputs": v["inputs_hits"], "answers": v["answers_hits"], "data": v["data_hits"]}
                             for r, v in leak["sandboxes"].items()}},
        "assumptions": assumptions,
    }


def main(work, template, out):
    data = {"papers": {"A": paper_payload(work, "A")}}
    if (Path(work) / "paperB2" / "eval" / "grades.json").exists():
        b = paper_payload(work, "B", "paperB2")
        v1 = paper_payload(work, "B", "paperB")
        b["v1"] = {"summary": v1["summary"], "attribution": v1["attribution"], "cells": v1["cells"], "runs": v1["runs"],
                   "audits": v1["audits"], "leak": v1["leak"]}
        data["papers"]["B"] = b
    else:
        data["papers"]["B"] = paper_payload(work, "B")
    html = Path(template).read_text(encoding="utf-8")
    blob = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    page = html.replace("/*__DATA__*/null", blob)
    # Standalone file (opens offline from disk): give it a full document skeleton.
    head, body = page.split("</style>", 1)
    doc = ('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
           '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
           f"{head}</style>\n</head>\n<body>\n{body}\n</body>\n</html>\n")
    Path(out).write_text(doc, encoding="utf-8")
    print("wrote", out, f"{Path(out).stat().st_size/1024:.0f} KB")
    if len(sys.argv) > 4:  # body-only variant for hosting
        Path(sys.argv[4]).write_text(page, encoding="utf-8")


if __name__ == "__main__":
    main(*sys.argv[1:])
