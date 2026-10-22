"""Reproduce Table 2 (M2CA tested alone, n = 31) from raw_crc.csv.
Usage: python -I repro_table.py <data_dir> <out_dir>
"""
import sys, os, json
import numpy as np
import pandas as pd
from scipy.optimize import least_squares
from scipy.stats import shapiro

data_dir, out_dir = sys.argv[1], sys.argv[2]
TIMES = [15, 30, 45]
MAX = 100.0


def model(x, ec50, h, s):
    """5PL-1P (Eq. 1/2): y = max/(1+(xb/x)^h)^s, xb chosen so y(EC50)=max/2."""
    xb = ec50 * 10 ** ((1.0 / h) * np.log10(2 ** (1.0 / s) - 1))
    return MAX / (1 + (xb / x) ** h) ** s


def ecx(p, ec50, h, s):
    xb = ec50 * 10 ** ((1.0 / h) * np.log10(2 ** (1.0 / s) - 1))
    return xb / (((MAX / p) ** (1.0 / s) - 1) ** (1.0 / h))


def fit_5pl1p(x, y):
    """Unweighted least squares on all replicate points; EC50>0, 0.1<s<10, max=100."""
    x = np.asarray(x, float); y = np.asarray(y, float)
    # automatic initial values: EC50 by interpolation on log-x of mean response
    xs = np.unique(x); ym = np.array([y[x == v].mean() for v in xs])
    if ym.max() > 50 and ym.min() < 50:
        ec0 = 10 ** np.interp(50, np.maximum.accumulate(ym), np.log10(xs))
    else:
        ec0 = xs[np.argmin(np.abs(ym - 50))]
    best = None
    for h0 in (0.5, 1.0, 2.0):
        for s0 in (0.5, 1.0, 2.0):
            p0 = [np.log(ec0), h0, s0]
            res = least_squares(lambda p: model(x, np.exp(p[0]), p[1], p[2]) - y, p0,
                                bounds=([-np.inf, 1e-3, 0.1], [np.inf, 50, 10]),
                                method="trf", max_nfev=20000, xtol=1e-14, ftol=1e-14, gtol=1e-14)
            if best is None or res.cost < best.cost:
                best = res
    ec50, h, s = np.exp(best.x[0]), best.x[1], best.x[2]
    yhat = model(x, ec50, h, s)
    r2 = 1 - np.sum((y - yhat) ** 2) / np.sum((y - y.mean()) ** 2)
    return dict(ec50=ec50, slope=h, s=s, r2=r2,
                ec25=ecx(25, ec50, h, s), ec75=ecx(75, ec50, h, s))


def select_m2ca_alone_tests(d):
    """30 A-alone tests (test 1 of every combination) + B-alone test (test 2) of sham M2CA-M2CA."""
    tests = []
    for comb in sorted(d.combination.unique()):
        g = d[(d.combination == comb) & (d.test == 1)]
        tests.append((comb + ":A", g.conc_A_uM.values, g))
    g = d[(d.combination == "M2CA-M2CA") & (d.test == 2)]
    tests.append(("M2CA-M2CA:B", g.conc_B_uM.values, g))
    return tests


def per_test_fits(d):
    rows = []
    for name, conc, g in select_m2ca_alone_tests(d):
        rec = {"test": name}
        for t in TIMES:
            m = (g.time_min == t).values
            f = fit_5pl1p(conc[m], g.effect_pct.values[m])
            for k, v in f.items():
                rec[f"{k}_{t}"] = v
        rec["tdt_15_45"] = (rec["ec50_15"] - rec["ec50_45"]) / (rec["ec50_15"] * 0.667) * 100
        rows.append(rec)
    return pd.DataFrame(rows)


def summary_stats(v):
    v = np.asarray(v, float)
    mean = v.mean(); sd = v.std(ddof=1)
    return {"mean": mean, "sd": sd, "cv": sd / mean * 100,
            "range": v.max() - v.min(), "sw": shapiro(v).statistic}


def main():
    d = pd.read_csv(os.path.join(data_dir, "raw_crc.csv"))
    d["effect_pct"] = pd.to_numeric(d["effect_pct"], errors="coerce")
    print(f"dropping {d.effect_pct.isna().sum()} missing (dashed) effect readings")
    d = d.dropna(subset=["effect_pct"])
    fits = per_test_fits(d)
    print(f"n tests = {len(fits)}")
    pd.set_option("display.width", 250); pd.set_option("display.max_columns", 50)
    print(fits.round(4).to_string())
    os.makedirs(out_dir, exist_ok=True)
    fits.to_csv(os.path.join(out_dir, "per_test_fits.csv"), index=False)
    tpl_path = os.path.join(data_dir, "..", "template.json")
    with open(tpl_path, encoding="utf-8") as fh:
        tpl = json.load(fh)
    for key, cell in tpl["cells"].items():
        row, col = key.split("|")
        st = summary_stats(fits[row].values)
        cell["value"] = float(st[col])
        cell["stars"] = ""
        cell["source"] = f"summary_stats(per_test_fits()['{row}'])['{col}']"
    with open(os.path.join(out_dir, "filled.json"), "w", encoding="utf-8") as fh:
        json.dump(tpl, fh, indent=1, ensure_ascii=False)
    for r in tpl["rows"]:
        print(r["id"].ljust(10), "  ".join(f"{tpl['cells'][r['id']+'|'+c['id']]['value']:.5g}" for c in tpl["columns"]))


if __name__ == "__main__":
    main()
