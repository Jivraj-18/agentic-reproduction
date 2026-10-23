"""Build the top-level index.html: all six papers by publisher, then the Opus 5.5 vs Sonnet 5.5 comparison.

Every number comes from the per-publisher pipeline outputs (grades, cost, choices); this script only collects them.
Elsevier and Springer Nature: one run per model (r_opus, r_sonnet). Wiley: three Opus runs (r1-r3, from the first
demo) and one Sonnet run (r_sonnet); its Opus figures are shown per run and its Opus cost is the mean of the three.

Usage: python -I hub/build_hub.py <repo_root> <out.html>
"""
import json
import sys
from pathlib import Path

PUBLISHERS = [  # alphabetical
    ("Elsevier", "elsevier", {"A": "paperA", "B": "paperB"}),
    ("Springer Nature", "springer-nature", {"A": "paperA", "B": "paperB"}),
    ("Wiley", "wiley", {"A": "paperA", "B": "paperB2"}),
]
WILEY_META = {  # wiley/scripts/build_report.py META, short fields only
    "A": {"title": "Natural history of limb girdle muscular dystrophy R9 over 6 years: searching for trial endpoints",
          "authors": "Murphy AP, Morrow J, Dahlqvist JR, et al.", "journal": "Annals of Clinical and Translational Neurology",
          "year": "2019; 6(6): 1033–1045", "field": "Clinical neurology", "doi": "10.1002/acn3.774",
          "table": "Table 1. The median change in functional assessments over the follow-up of 6 years."},
    "B": {"title": "In Vitro Signaling Properties of Cannabinoid and Orexin Receptors: How Orexin Receptors Influence "
                   "Cannabinoid Receptor-Mediated Signaling",
          "authors": "Mohamed KA, Laprairie RB", "journal": "Pharmacology Research & Perspectives",
          "year": "2025; 13: e70078", "field": "Pharmacology (curve fitting)", "doi": "10.1002/prp2.70078",
          "table": "Table 1. CB₁-dependent inhibition of cAMP and recruitment of βarrestin2 in CB₁-OX₁ cells."},
}


def load(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def run_stats(cells, run):
    graded = [c for c in cells.values() if c["graded"] and run in c["runs"]]
    gs = [c["runs"][run]["grade"] for c in graded]
    st = [c for c in cells.values() if c.get("published_stars") is not None and run in c["runs"]]
    return {"a": gs.count("A"), "ab": sum(g in "AB" for g in gs),
            "dist": {g: gs.count(g) for g in "ABCDEF"},
            "stars": [sum((c["runs"][run].get("stars") or "") == (c["published_stars"] or "") for c in st), len(st)]}


def cost(d, run):
    c = load(d / f"eval/cost_{run}.json")
    return c.get("cost_at_least_usd", c["cost_usd"])


def paper(root, pub, folder, pid, sub):
    d = root / folder / "work" / sub
    if folder == "wiley":
        meta = WILEY_META[pid]
        cells = load(d / "eval/grades_all.json")["cells"]
        opus_runs = ["r1", "r2", "r3"]
    else:
        meta = load(root / folder / "work/meta.json")["papers"][pid]
        cells = load(d / "eval/grades.json")["cells"]
        opus_runs = ["r_opus"]
    n = sum(1 for c in cells.values() if c["graded"])
    opus = [run_stats(cells, r) for r in opus_runs]
    opus_cost = [cost(d, r) for r in opus_runs]
    ch = d / "eval/choices.json"
    return {
        "publisher": pub, "pid": pid, "href": f"{folder}/docs/index.html#{pid}",
        "title": meta["title"], "authors": meta["authors"], "journal": meta["journal"], "year": meta["year"],
        "field": meta["field"], "doi": meta["doi"], "table": meta["table"], "n": n,
        "opus": opus, "sonnet": run_stats(cells, "r_sonnet"),
        "cost": {"opus": round(sum(opus_cost) / len(opus_cost), 4), "opus_runs": opus_cost, "sonnet": cost(d, "r_sonnet")},
        "choices": load(ch)["choices"] if ch.exists() else [],
    }


def main(root, out):
    root = Path(root)
    papers = [paper(root, pub, folder, pid, sub) for pub, folder, subs in PUBLISHERS for pid, sub in subs.items()]
    tpl = (Path(__file__).parent / "hub_template.html").read_text(encoding="utf-8")
    blob = json.dumps({"papers": papers}, ensure_ascii=False).replace("</", "<\\/")
    Path(out).write_text(tpl.replace("/*__DATA__*/null", blob), encoding="utf-8")
    print("wrote", out, f"{Path(out).stat().st_size / 1024:.0f} KB")


if __name__ == "__main__":
    main(*sys.argv[1:])
