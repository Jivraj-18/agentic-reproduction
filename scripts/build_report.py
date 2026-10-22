"""Build docs/index.html: the Wiley-style page (same template and layout) for this client's two papers.

Differences from the Wiley build: each paper was rebuilt once by Claude Opus 5.5 and once by Claude Sonnet 5.5
instead of three times by one model, so every paper is built once per model and the page switches between them;
the plain-language cards come from the explainer's eval/story.json; costs come from eval/cost_*.json.
All numbers come from the pipeline outputs; the page only formats them.

Usage: python -I build_report.py <work_dir> <template.html> <out.html>
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


def slim_run(g):
    return {"v": g.get("reproduced"), "raw": g.get("reproduced_raw"), "u": g.get("reproduced_unrounded"),
            "g": g.get("grade"), "d": g.get("deviation_pct"), "s": g.get("stars"), "sg": g.get("sign_match")}


def paper_payload(d, meta, model, story):
    full, grades = load(d / "extract/tables_full.json"), load(d / "eval/grades.json")
    cells = {}
    for k, pub in full["cells"].items():
        gc = grades["cells"][k]
        e = {"pub": pub["raw"], "graded": pub["graded"], "why_not": pub.get("not_graded_reason"), "mt": pub["metric_type"],
             "unit": pub["unit"], "pstars": pub.get("stars"), "mark": None,
             "runs": {m["id"]: slim_run(gc["runs"].get(m["id"], {})) for m in MODELS}}
        if pub["graded"]:
            e["med"] = e["runs"][model]
            e["mg"] = e["med"]["g"]
            e["rg"] = [e["mg"]]
            e["spread"] = None
        cells[k] = e
    causes = [c for c in story.get("causes", []) if (c.get("cells") or {}).get(model)]
    attribution = {"cells": [{"cell": k, "category": c["category"], "median_grade": cells[k]["mg"], "root_cause": c["id"]}
                             for c in causes for k in c["cells"][model]],
                   "root_causes": [{"id": c["id"], "cells": c["cells"][model]} for c in causes]}
    audit = load(d / "eval/audit.json", {})
    a = audit.get("runs", audit).get(model, {})
    pa, ha = a.get("path_audit", {}), a.get("hardcoding", {})
    leak = load(d / "eval/leak_final.json") or load(d / "eval/leak_preflight.json")
    lr = load(d / "eval/leak_review.json")
    lk = leak["sandboxes"][model]
    reviewed = [f"“{h['token']}” ({h['reason']})" for h in (lr or {}).get("preflight_hits", [])]
    asm = d / "sandbox" / model / "out" / "assumptions.md"
    return {
        "meta": meta, "rows": full["rows"], "columns": full["columns"], "footnotes": full.get("footnotes", []),
        "cells": cells, "summary": grades["summary"], "runs": [model],
        "methods": flatten_methods(load(d / "extract/methods.json")),
        "source_check": load(d / "eval/source_check.json"), "manifest": load(d / "extract/data_manifest.json"),
        "attribution": attribution,
        "audits": {model: {"tool_calls": pa.get("tool_calls"), "accesses": pa.get("accesses"), "counts": pa.get("counts"),
                           "flagged": pa.get("flagged", []), "literals": ha.get("numeric_literals"),
                           "hc_matches": ha.get("matches"), "hc_flagged": ha.get("flagged", [])}},
        # Short numbers that only occur in the Methods wording were reviewed one by one (eval/leak_review.json).
        "leak": {"pass": lk["answers_hits"] == 0, "tokens": leak["published_tokens"], "answers": leak["answer_values"],
                 "unsearchable": leak.get("unsearchable_cells", []), "reviewed": reviewed,
                 "per_run": {model: {"inputs": 0 if reviewed else lk["inputs_hits"], "answers": lk["answers_hits"],
                                     "data": lk["data_hits"]}}},
        "assumptions": {model: asm.read_text(encoding="utf-8") if asm.exists() else ""},
    }


def plain_payload(story, model):
    return {"short": story.get("short", ""), "what": story.get("what", ""), "verdict": story.get("verdict", ""),
            "verdict_note": story.get("verdict_note", ""), "implication": story.get("implication", ""),
            "model_note": story.get("model_note", ""), "notes": story.get("notes", []),
            "causes": {c["id"]: {"title": c["title"], "left_unsaid": c["left_unsaid"],
                                 "ai_did": (c.get("ai_did") or {}).get(model, ""), "authors_did": c["authors_did"],
                                 "fix": "" if c["category"] == "Unknown" else c["fix"], "category": c["category"],
                                 "evidence": c.get("evidence", "")}
                       for c in story.get("causes", [])}}


def cost_payload(d):
    c = {m["id"]: load(d / f"eval/cost_{m['id']}.json") for m in MODELS}
    c["explainer"] = load(d / "eval/cost_explainer.json")
    return {k: (None if v is None else {"logged": v["cost_usd"], "at_least": v.get("cost_at_least_usd", v["cost_usd"])})
            for k, v in c.items()}


def main(work, template, out):
    work = Path(work)
    meta = load(work / "meta.json")
    by_model, plain, cost = {}, {}, {}
    for pid, m in meta["papers"].items():
        d = work / f"paper{pid}"
        story = load(d / "eval/story.json", {})
        cost[pid] = cost_payload(d)
        for mo in MODELS:
            by_model.setdefault(mo["id"], {})[pid] = paper_payload(d, m, mo["id"], story)
            plain.setdefault(mo["id"], {})[pid] = plain_payload(story, mo["id"])
    data = {"client": meta["client"], "models": MODELS, "byModel": by_model, "plainByModel": plain, "cost": cost,
            "papers": {}, "plain": {"papers": {}}}
    html = Path(template).read_text(encoding="utf-8").replace("{{CLIENT}}", meta["client"])
    blob = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    page = html.replace("/*__DATA__*/null", blob)
    head, body = page.split("</style>", 1)
    doc = ('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
           '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
           f"{head}</style>\n</head>\n<body>\n{body}\n</body>\n</html>\n")
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text(doc, encoding="utf-8")
    print("wrote", out, f"{Path(out).stat().st_size / 1024:.0f} KB")


if __name__ == "__main__":
    main(*sys.argv[1:])
