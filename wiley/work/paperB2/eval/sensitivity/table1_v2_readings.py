"""Sensitivity checks for Paper B Table 1, extraction v2 (cells graded B or worse).

Usage: python -I table1_v2_readings.py <crc_cAMP_fold.csv> <crc_barr2_fold.csv> <v1_table1_readings.py> <out.json>

Reuses the fit and parsing functions of the v1 script (paperB/eval/sensitivity/table1_readings.py):
unweighted least squares on Y = Bottom + (Top-Bottom)/(1+10^((LogEC50-X)*Hill)), asymptotic SEs.

Checks:
  A. barr2 0.00 ug potency bound: which bound each reasonable reading gives
     (top tested concentration; fitted EC50 (r3); half-observed-max crossing (r2)).
  B. cAMP 0.50 ug Hill-constrained fit: Hill fixed +1 vs -1 give the same curve; only the sign label differs.
  C. barr2 0.10 ug EC50 = 3078 nM vs published 3000: print-precision check against all published EC50s.
"""
import importlib.util
import json
import math
import sys

import numpy as np


def load_v1(path):
    spec = importlib.util.spec_from_file_location("v1", path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def sig(v, n):
    if v == 0:
        return 0.0
    d = n - int(math.floor(math.log10(abs(v)))) - 1
    return round(v, d)


def main(camp_path, arr_path, v1_path, out_path):
    v1 = load_v1(v1_path)
    res = {}
    xc, camp = v1.parse_block(camp_path, "CB1R - OX1R")
    xa, arr = v1.parse_block(arr_path, "CB1R-OX1R")

    # ---------- A. barr2 0.00 ug bound (published pEC50 "<5", EC50 ">10000" nM)
    A0 = arr["0.00"]
    xmax = float(np.max(xa))
    res["A_top_tested_conc"] = {"log_M": xmax, "pec50_bound": f"<{-xmax:g}", "ec50_bound_nM": f">{10 ** xmax * 1e9:.0f}"}
    f = v1.clean(v1.fit(xa, A0))
    res["A_free4PL_all8"] = f
    res["A_fitted_ec50_as_bound"] = {"pec50_bound": f"<{f['pec50']:.4f}", "ec50_bound_nM": f">{f['ec50_nM']:.0f}"}
    order = np.argsort(xa)
    x, m = xa[order], A0[order].mean(axis=1)
    half = (m.min() + m.max()) / 2
    i = int(np.where(m >= half)[0][0])
    xh = x[i - 1] + (half - m[i - 1]) * (x[i] - x[i - 1]) / (m[i] - m[i - 1])
    res["A_half_observed_max_crossing"] = {"log_M": float(xh), "pec50_bound": f"<{-xh:.4f}", "ec50_bound_nM": f">{10 ** xh * 1e9:.1f}"}
    res["A_fit_inside_tested_range"] = bool(f["pec50"] > -xmax)

    # ---------- B. cAMP 0.50 ug, Hill fixed (published pEC50 7.9 (11), Emax 0.69, Hill "-1")
    C50 = camp["0.50"]
    for h in (1.0, -1.0):
        r = v1.fit(xc, C50, hill=h)
        xx, yy = np.repeat(xc, C50.shape[1]), C50.ravel()
        sse = float(np.sum((yy - v1.f4(xx, r["bottom"], r["top"], -r["pec50"], h)) ** 2))
        res[f"B_3PL_hill{h:+.0f}"] = v1.clean(dict(r, sse=sse,
                                                    plateau_at_high_conc=(r["top"] if h > 0 else r["bottom"]),
                                                    plateau_at_low_conc=(r["bottom"] if h > 0 else r["top"])))
    res["B_note"] = ("With Hill=+1 the decreasing curve has Bottom (low-x end) > Top (high-x end), as in the "
                     "authors' Prism tab (Bottom 0.9716, Top 0.6861, 'log(agonist) vs. response (three parameters)'). "
                     "With Hill=-1 the same curve is returned with the plateau labels swapped.")
    # sign of the free Hill slopes printed for the other cAMP rows
    res["B_free_hill_other_rows"] = {d: round(float(v1.fit(xc, camp[d])["hill"]), 3) for d in ("0.00", "0.10", "0.25")}

    # ---------- C. EC50 print precision
    A10 = arr["0.10"]
    f10 = v1.fit(xa, A10)
    ec = f10["ec50_nM"]
    res["C_arr010_ec50_nM"] = round(float(ec), 2)
    res["C_arr010_rounding"] = {"1sf": sig(ec, 1), "2sf": sig(ec, 2), "3sf": sig(ec, 3),
                                "from_printed_pEC50_5.5": round(10 ** -5.5 * 1e9, 1),
                                "from_printed_pEC50_5.5_2sf": sig(10 ** -5.5 * 1e9, 2)}
    # published EC50s in Table 1 vs the authors' Prism EC50s (tabs 'Fig. 2B Table 1' row 8 / H7 and 'Fig. 2D Table 1' row 8)
    authors = {"camp 0.00": (1.49e-9, "1.5"), "camp 0.10": (7.176e-9, "7.2"), "camp 0.25": (1.244e-8, "12"),
               "camp 0.50 (3PL)": (1.079e-8, "11"), "arr 0.10": (3.078e-6, "3000"),
               "arr 0.25": (9.614e-7, "960"), "arr 0.50": (3.983e-7, "400")}
    tab = {}
    for k, (m_, pub) in authors.items():
        nm = m_ * 1e9
        tab[k] = {"authors_nM": nm, "2sf": sig(nm, 2), "published": pub,
                  "matches_2sf": abs(sig(nm, 2) - float(pub)) < 1e-9}
    res["C_published_vs_authors_ec50"] = tab

    for k, v in res.items():
        print(k, v)
    json.dump(res, open(out_path, "w", encoding="utf-8"), indent=1, default=float)


if __name__ == "__main__":
    main(*sys.argv[1:5])
