"""Sensitivity re-runs for Paper B Table 1 (CB1-OX1).

Usage: python -I table1_readings.py <crc_cAMP_fold.csv> <crc_barr2_fold.csv> <out.json>

Tests alternative readings of the methods against the published values:
  - pooled single fit (all experiment points) vs per-experiment fits averaged
  - all 8 mock columns vs columns 1-4 or 5-8
  - free 4-parameter fit vs Hill fixed to +/-1
  - 'observed Emax' rule: mean +/- SEM of the values at 10 uM
Fit = unweighted least squares on Prism's equation
Y = Bottom + (Top-Bottom)/(1+10^((LogEC50-X)*Hill)); SE from the asymptotic covariance (Prism default).
"""
import csv
import json
import sys

import numpy as np
from scipy.optimize import curve_fit


def parse_block(path, title):
    rows = list(csv.reader(open(path, encoding="utf-8-sig")))
    i = next(k for k, r in enumerate(rows) if r and r[0].replace(" ", "") == title.replace(" ", ""))
    header = rows[i + 1]
    starts = [j for j, h in enumerate(header) if j > 0 and h.strip()]
    names = [header[j].split()[0] for j in starts]
    data = []
    k = i + 2
    while k < len(rows) and rows[k] and rows[k][0].strip():
        data.append(rows[k])
        k += 1
    x = np.array([float(r[0]) for r in data])
    out = {}
    for n, (s, e) in zip(names, zip(starts, starts[1:] + [len(header)])):
        cols = []
        for j in range(s, e):
            v = [r[j] if j < len(r) else "" for r in data]
            if all(t.strip() for t in v):
                cols.append([float(t) for t in v])
        out[n] = np.array(cols).T
    return x, out


def f4(x, b, t, le, h):
    return b + (t - b) / (1 + 10 ** ((le - x) * h))


def fit(x, Y, hill=None):
    xx = np.repeat(x, Y.shape[1])
    yy = Y.ravel()
    lo, hi = yy.min(), yy.max()
    best = None
    for h0 in ([1.0, -1.0] if hill is None else [None]):
        for le0 in (-9.0, -8.0, -7.0, -6.0, -5.0):
            try:
                if hill is None:
                    p, c = curve_fit(f4, xx, yy, p0=[yy[xx == x.min()].mean(), yy[xx == x.max()].mean(), le0, h0], maxfev=50000)
                else:
                    g = lambda xv, b, t, le: f4(xv, b, t, le, hill)
                    p, c = curve_fit(g, xx, yy, p0=[yy[xx == x.min()].mean(), yy[xx == x.max()].mean(), le0], maxfev=50000)
                    p = np.append(p, hill)
                    c2 = np.full((4, 4), np.nan)
                    c2[:3, :3] = c
                    c = c2
            except Exception:
                continue
            sse = float(np.sum((yy - f4(xx, *p)) ** 2))
            if best is None or sse < best[2] - 1e-12:
                best = (p, c, sse)
    p, c, sse = best
    se = np.sqrt(np.abs(np.diag(c)))
    if hill is None and p[0] > p[1]:
        # (b, t, le, h) and (t, b, le, -h) are the same curve; use Prism's convention Bottom < Top
        p = np.array([p[1], p[0], p[2], -p[3]])
        se = np.array([se[1], se[0], se[2], se[3]])
    return dict(bottom=p[0], se_bottom=se[0], top=p[1], se_top=se[1], pec50=-p[2], se_pec50=se[2],
                ec50_nM=10 ** p[2] * 1e9, hill=p[3], se_hill=(None if hill is not None else se[3]),
                n_y=int(Y.size), df=int(Y.size - (4 if hill is None else 3)))


def per_exp(x, Y, hill=None):
    fs = [fit(x, Y[:, [j]], hill) for j in range(Y.shape[1])]
    out = {}
    for k in ("pec50", "bottom", "top", "hill"):
        v = np.array([f[k] for f in fs])
        out[k] = float(v.mean())
        out["sem_" + k] = float(v.std(ddof=1) / np.sqrt(len(v)))
    return out


def clean(d):
    return {k: (round(float(v), 5) if isinstance(v, (float, np.floating)) else v) for k, v in d.items()}


def main(camp_path, arr_path, out_path):
    res = {}
    xc, camp = parse_block(camp_path, "CB1R - OX1R")
    xa, arr = parse_block(arr_path, "CB1R-OX1R")
    C0, A0, A10 = camp["0.00"], arr["0.00"], arr["0.10"]
    print("mock columns: cAMP", C0.shape, "barr2", A0.shape)

    # ---- cAMP 0.00 ug (published 8.8+-0.45 (1.5); Emax 0.79+-0.03; Hill -1.7+-3.6)
    sets = {"all8": C0, "cols1-4": C0[:, :4], "cols5-8": C0[:, 4:]}
    for name, Y in sets.items():
        res[f"camp000_{name}_free4PL"] = clean(fit(xc, Y))
        res[f"camp000_{name}_hill-1"] = clean(fit(xc, Y, hill=-1.0))
        res[f"camp000_{name}_perexp_hill-1"] = clean(per_exp(xc, Y, hill=-1.0))

    # ---- barr2 0.00 ug (published pEC50 <5 (>10000 nM); Emax 17+-4.6 (observed); Hill n.d.)
    for name, Y in {"all8": A0, "cols1-4": A0[:, :4], "cols5-8": A0[:, 4:]}.items():
        res[f"arr000_{name}_free4PL"] = clean(fit(xa, Y))
        res[f"arr000_{name}_hill+1"] = clean(fit(xa, Y, hill=1.0))
        top = Y[np.argmax(xa), :]
        res[f"arr000_{name}_observed_at_10uM"] = clean(dict(mean=top.mean(), sem=top.std(ddof=1) / np.sqrt(len(top)), n=len(top)))

    # ---- barr2 0.10 ug (published 5.5+-1.4 (3000); Emax 5.7+-3.2; Hill 0.41+-0.23)
    res["arr010_pooled_free4PL"] = clean(fit(xa, A10))
    res["arr010_pooled_hill+1"] = clean(fit(xa, A10, hill=1.0))
    res["arr010_perexp_free4PL"] = clean(per_exp(xa, A10))

    for k, v in res.items():
        print(k, v)
    json.dump(res, open(out_path, "w"), indent=1)


if __name__ == "__main__":
    main(*sys.argv[1:4])
