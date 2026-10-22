"""Build docs/index.html: one self-contained page (no external calls) for this client's two papers and both models.

All numbers on the page come from the pipeline outputs: grades.json, story.json (the explainer), audit.json,
audit_review.json, the leak checks, the extraction files and the cost records. The page only formats them.

Usage: python -I build_site.py <work_dir> <template.html> <out.html>
"""
import json
import sys
from pathlib import Path

MODELS = [{"id": "r_opus", "label": "Claude Opus 5.5", "short": "Opus 5.5"},
          {"id": "r_sonnet", "label": "Claude Sonnet 5.5", "short": "Sonnet 5.5"}]


def load(p, default=None):
    p = Path(p)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else default


def flatten_methods(m):
    items = []

    def add(section, it, label=None):
        items.append({"section": section, "id": it.get("id"), "text": label or it.get("description") or it.get("text"),
                      "source": it.get("source_sentence"), "gap": it.get("gap", False), "gap_note": it.get("gap_note")})
    add("Research question", m["research_question"])
    s = m["setting"]
    add("Setting", s, f"{s['population']} {s['site']}")
    for d in m["data_sources"]:
        add("Data", d, f"{d['name']}: {d['summary']}")
    for g in m["general_manipulations"]:
        add("Data preparation", g)
    for t in m["tables"]:
        for f in t.get("table_specific_filters", []):
            add("Table filter", f)
        for sp in t.get("specification", []):
            add("Table specification", sp)
    return items


def run_summary(grades, run):
    keys = [k for k, c in grades["cells"].items() if c["graded"]]
    g = [grades["cells"][k]["runs"][run].get("grade") for k in keys]
    s = grades["summary"]["per_run"][run]
    return {"n": len(keys), "exact": sum(x == "A" for x in g), "close": sum(x in ("A", "B") for x in g),
            "far": sum(x in ("C", "D", "E", "F") for x in g), "dist": s["distribution"], "table_grade": s["table_grade"]}


def cost_of(rec):
    return None if not rec else {"logged": rec["cost_usd"], "at_least": rec.get("cost_at_least_usd", rec["cost_usd"]),
                                 "requests": rec["api_requests"]}


def paper_payload(work, pid, meta):
    d = Path(work) / f"paper{pid}"
    full = load(d / "extract/tables_full.json")
    grades = load(d / "eval/grades.json")
    tmpl = load(d / "extract/template.json")
    cells = {}
    for k, pub in full["cells"].items():
        gc = grades["cells"].get(k, {})
        e = {"pub": pub["raw"], "graded": pub["graded"], "why_not": pub.get("not_graded_reason"), "pstars": pub.get("stars"),
             "unit": pub.get("unit"), "runs": {}}
        for m in MODELS:
            r = (gc.get("runs") or {}).get(m["id"], {})
            e["runs"][m["id"]] = {"v": r.get("reproduced"), "u": r.get("reproduced_unrounded"), "g": r.get("grade"),
                                  "d": r.get("deviation_pct"), "s": r.get("stars")}
        cells[k] = e
    audit, review = load(d / "eval/audit.json", {}), load(d / "eval/audit_review.json", {})
    audit = audit.get("runs", audit)
    leak = load(d / "eval/leak_final.json") or load(d / "eval/leak_preflight.json")
    per_model = {}
    for m in MODELS:
        r = m["id"]
        a = audit.get(r, {})
        pa, ha = a.get("path_audit", {}), a.get("hardcoding", {})
        lk = leak["sandboxes"].get(r, {})
        per_model[r] = {
            "summary": run_summary(grades, r),
            "assumptions": (d / "sandbox" / r / "out" / "assumptions.md").read_text(encoding="utf-8")
            if (d / "sandbox" / r / "out" / "assumptions.md").exists() else "",
            "cost": cost_of(load(d / f"eval/cost_{r}.json")),
            "audit": {"paths": pa.get("counts"), "path_flags": pa.get("flagged", []), "literals": ha.get("numeric_literals"),
                      "hc_flags": ha.get("flagged", []), "review": review.get(r, {})},
            "leak": {"inputs": lk.get("inputs_hits"), "answers": lk.get("answers_hits"), "data": lk.get("data_hits")},
        }
    return {
        "meta": meta, "rows": full["rows"], "columns": full["columns"], "footnotes": full.get("footnotes", []),
        "caption": full.get("caption"), "excluded": full.get("excluded_columns", []), "cells": cells,
        "n_template": len(tmpl["cells"]), "models": per_model, "story": load(d / "eval/story.json", {}),
        "explainer_cost": cost_of(load(d / "eval/cost_explainer.json")),
        "methods": flatten_methods(load(d / "extract/methods.json")),
        "source_check": load(d / "eval/source_check.json"), "manifest": load(d / "extract/data_manifest.json"),
        "leak_pass": leak["pass"], "leak_review": load(d / "eval/leak_review.json"),
        "leak_tokens": leak.get("published_tokens"),
    }


def main(work, template, out):
    meta = load(Path(work) / "meta.json")
    data = {"client": meta["client"], "models": MODELS,
            "papers": {pid: paper_payload(work, pid, m) for pid, m in meta["papers"].items()}}
    html = Path(template).read_text(encoding="utf-8").replace("{{CLIENT}}", meta["client"])
    blob = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text(html.replace("/*__DATA__*/null", blob), encoding="utf-8")
    print("wrote", out, f"{Path(out).stat().st_size / 1024:.0f} KB")


if __name__ == "__main__":
    main(*sys.argv[1:])
