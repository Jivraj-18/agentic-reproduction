"""Step 3: deterministic grading of reproduced tables against the published table.

Grading rules (as in published agentic-reproduction evaluations):
  - normalise units first (declared unit in filled.json vs the table's unit)
  - round the reproduced value to the digits printed in the original
  - per-cell absolute % deviation and sign match
  - A <=2%, B 2-20%, C 20-40%, D 40-60% (sign matches); E >60% or sign flipped; F no number
  - where the original prints a +/- error, share of estimates within 1.96 x that error
  - table grade = mean of cell grades (A=5 ... F=0), per run and median over runs

Bounds: a published '<5' is matched by any reproduced value or bound that satisfies it;
otherwise deviation is measured from the bound value.

Usage: python -I grade.py <paper_dir> <out.json>
"""
import json
import math
import re
import statistics
import sys
from pathlib import Path

GRADE_POINTS = {"A": 5, "B": 4, "C": 3, "D": 2, "E": 1, "F": 0}
POINT_GRADES = {v: k for k, v in GRADE_POINTS.items()}

# unit -> factor to convert a value in that unit into the table's unit
CONVERSIONS = {
    "nM": {"nM": 1, "M": 1e9, "uM": 1e3, "µM": 1e3, "μM": 1e3, "pM": 1e-3, "mM": 1e6},
    "%": {"%": 1, "fraction": 100, "proportion": 100},
    "m/s": {"m/s": 1, "msec-1": 1, "cm/s": 0.01},
    "steps/s": {"steps/s": 1, "stairs/s": 1, "steps/sec": 1, "stairs/sec": 1},
    "kg": {"kg": 1, "g": 1e-3},
    "m": {"m": 1, "meters": 1, "metres": 1},
    "s": {"s": 1, "sec": 1, "seconds": 1},
    "fold": {"fold": 1, "Fold": 1},
}


def parse_value(v):
    """Return (comparator, number) or (None, None) when no number was produced."""
    if v is None:
        return None, None
    if isinstance(v, bool):
        return None, None
    if isinstance(v, (int, float)):
        return (None, float(v)) if math.isfinite(v) else (None, None)
    m = re.fullmatch(r"\s*([<>]=?)?\s*(-?[\d.]+(?:[eE][-+]?\d+)?)\s*", str(v).replace("−", "-"))
    if m:
        return (m.group(1)[0] if m.group(1) else None), float(m.group(2))
    return None, None


def unit_factor(table_unit, declared):
    if not table_unit or not declared or declared == table_unit:
        return 1.0, None
    f = CONVERSIONS.get(table_unit, {}).get(declared)
    if f is None:
        return 1.0, f"declared unit '{declared}' not convertible to '{table_unit}'"
    return f, f"converted {declared} -> {table_unit} (x{f:g})"


def letter(dev, sign_ok):
    if not sign_ok or dev > 60:
        return "E"
    if dev <= 2:
        return "A"
    if dev <= 20:
        return "B"
    if dev <= 40:
        return "C"
    return "D"


def grade_cell(pub, rep_value, rep_unit):
    """Grade one reproduced value against one published cell."""
    out = {"reproduced_raw": rep_value}
    comp, num = parse_value(rep_value)
    if num is None:
        out.update(grade="F", deviation_pct=None, sign_match=None, reproduced=None)
        return out
    factor, note = unit_factor(pub["unit"], rep_unit)
    num *= factor
    if note:
        out["unit_note"] = note
    p, d = pub["value"], pub["decimals"]
    out["reproduced_unrounded"] = num
    # Strip floating-point noise (2.6500000000000004 vs 2.65) before rounding to the published digits.
    rounded = round(round(num, 9), d)
    if pub["comparator"]:  # a published limit such as "<5" or ">10000" is compared as it is
        rounded = round(num, 9)
    elif d == 0 and p == int(p) and int(abs(p)) % 10 == 0:  # '3000' is printed to 1 s.f., '960' to 2 s.f.
        digits = len(str(int(abs(p))))
        sig = len(str(int(abs(p))).rstrip("0"))
        rounded = float(round(rounded, -(digits - sig)))
    out["reproduced"] = round(round(num, 9), d) if pub["comparator"] else rounded  # shown at the printed precision
    if pub["comparator"]:  # published bound, e.g. '<5'
        satisfied = (num < p) if pub["comparator"] == "<" else (num > p)
        if comp and comp == pub["comparator"]:
            satisfied = (num <= p) if comp == "<" else (num >= p)
        dev = 0.0 if satisfied else abs(rounded - p) / abs(p) * 100
        out.update(grade=letter(dev, True), deviation_pct=dev, sign_match=True, bound_satisfied=satisfied)
        return out
    if comp:  # reproducer gave a bound where the paper gave a number
        out.update(grade="F", deviation_pct=None, sign_match=None, note="reproducer reported a bound, not a number")
        return out
    sign_ok = (p == 0 and rounded == 0) or (p != 0 and rounded != 0 and (p > 0) == (rounded > 0))
    dev = abs(rounded - p) / abs(p) * 100 if p != 0 else (0.0 if rounded == 0 else math.inf)
    out.update(grade=letter(dev, sign_ok), deviation_pct=dev, sign_match=sign_ok)
    return out


def star_flag(s):
    """Normalise a significance marker to the number of '*' (or 1 for the letter marker 'a')."""
    if s is None:
        return None
    s = str(s).strip()
    if s in ("", "ns", "n.s."):
        return 0
    return s.count("*") or (1 if s else 0)


def table_grade(grades):
    pts = [GRADE_POINTS[g] for g in grades]
    mean = sum(pts) / len(pts)
    return {"mean_points": round(mean, 3), "letter": POINT_GRADES[min(5, max(0, round(mean)))]}


def distribution(grades):
    return {g: grades.count(g) for g in "ABCDEF"}


def main(paper_dir, out_path):
    paper_dir = Path(paper_dir)
    full = json.load(open(paper_dir / "extract" / "tables_full.json", encoding="utf-8"))
    runs = sorted(p for p in (paper_dir / "sandbox").glob("r*") if (p / "out" / "filled.json").exists())
    filled = {r.name: json.load(open(r / "out" / "filled.json", encoding="utf-8")) for r in runs}
    cells_out, per_run = {}, {r: [] for r in filled}
    within_ci = {r: [] for r in filled}
    within_ci_median = []
    stars = {r: [] for r in filled}
    for key, pub in full["cells"].items():
        entry = {"published_raw": pub["raw"], "metric_type": pub["metric_type"], "unit": pub["unit"],
                 "graded": pub["graded"], "published_stars": pub.get("stars"), "runs": {}}
        nums = []
        for rname, f in filled.items():
            rc = (f.get("cells") or {}).get(key) or {}
            g = grade_cell(pub, rc.get("value"), rc.get("unit")) if pub["graded"] else {"reproduced_raw": rc.get("value")}
            g["stars"] = rc.get("stars")
            g["source"] = rc.get("source")
            entry["runs"][rname] = g
            if pub["graded"]:
                per_run[rname].append(g["grade"])
                if g.get("reproduced_unrounded") is not None and not parse_value(rc.get("value"))[0]:
                    nums.append(g["reproduced_unrounded"])
            if pub.get("stars") is not None and pub["graded"]:
                stars[rname].append(star_flag(pub["stars"]) == star_flag(rc.get("stars")))
        if pub["graded"]:
            # consensus cell: median of the runs' numeric values (or the bound if all runs gave one)
            if nums:
                med = statistics.median(nums)
                cons = grade_cell(pub, med, None)
                spread = (max(nums) - min(nums)) / abs(pub["value"]) * 100 if pub["value"] else None
            else:
                # all runs gave bounds/strings: show the run whose grade is the median grade
                pts = sorted((GRADE_POINTS[entry["runs"][r]["grade"]], r) for r in filled)
                mid = pts[(len(pts) - 1) // 2][1] if pts else None
                cons = grade_cell(pub, entry["runs"][mid]["reproduced_raw"] if mid else None, None)
                spread = None
            entry["median"] = cons
            entry["run_spread_pct"] = spread
            rounded = {entry["runs"][r].get("reproduced") for r in filled}
            entry["runs_agree"] = len(rounded) == 1 and None not in rounded
            entry["run_grades"] = [entry["runs"][r]["grade"] for r in filled]
            entry["median_grade"] = POINT_GRADES[int(statistics.median_low(GRADE_POINTS[g] for g in entry["run_grades"]))]
        cells_out[key] = entry
    # +/- check: estimate within 1.96 x published error
    for key, pub in full["cells"].items():
        if pub["metric_type"] != "pm" or not pub["graded"] or not pub.get("link_to"):
            continue
        est_key = pub["link_to"]
        est = full["cells"][est_key]
        if not est["graded"] or est["comparator"]:
            continue
        for rname in filled:
            r = cells_out[est_key]["runs"][rname].get("reproduced_unrounded")
            if r is not None:
                within_ci[rname].append(abs(r - est["value"]) <= 1.96 * pub["value"])
        m = cells_out[est_key].get("median", {}).get("reproduced_unrounded")
        if m is not None:
            within_ci_median.append(abs(m - est["value"]) <= 1.96 * pub["value"])
        cells_out[est_key]["published_error"] = pub["value"]
    graded_keys = [k for k, c in cells_out.items() if c["graded"]]
    sign_cells = [cells_out[k]["median"].get("sign_match") for k in graded_keys]
    summary = {
        "n_cells_graded": len(graded_keys),
        "per_run": {r: {"distribution": distribution(g), "table_grade": table_grade(g),
                        "within_1.96se": (sum(within_ci[r]), len(within_ci[r])),
                        "stars_agree": (sum(stars[r]), len(stars[r]))} for r, g in per_run.items()},
        "median_cell_grades": distribution([cells_out[k]["median_grade"] for k in graded_keys]),
        "consensus_cell_grades": distribution([cells_out[k]["median"]["grade"] for k in graded_keys]),
        "table_grade_median_of_runs": statistics.median(table_grade(g)["mean_points"] for g in per_run.values()) if per_run else None,
        "sign_match": (sum(1 for s in sign_cells if s), sum(1 for s in sign_cells if s is not None)),
        "within_1.96se_consensus": (sum(within_ci_median), len(within_ci_median)),
        "runs_identical_cells": (sum(1 for k in graded_keys if cells_out[k]["runs_agree"]), len(graded_keys)),
        "runs_same_grade_cells": (sum(1 for k in graded_keys if len(set(cells_out[k]["run_grades"])) == 1), len(graded_keys)),
        "within_20pct_consensus": (sum(1 for k in graded_keys if cells_out[k]["median"]["grade"] in "AB"), len(graded_keys)),
    }
    tg = summary["table_grade_median_of_runs"]
    summary["table_grade_median_letter"] = POINT_GRADES[min(5, max(0, round(tg)))] if tg is not None else None
    json.dump({"paper": full["paper"], "table": full["table_id"], "runs": list(filled), "summary": summary,
               "cells": cells_out}, open(out_path, "w", encoding="utf-8"), indent=1, ensure_ascii=False, default=str)
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main(*sys.argv[1:])
