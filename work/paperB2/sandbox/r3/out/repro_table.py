"""Reproduce Table 1 (CB1-OX1: cAMP inhibition and barrestin2 recruitment by CP55,940).

Usage: python -I out/repro_table.py data out

Pipeline (see out/assumptions.md for the reasoning behind each choice):
  1. parse_block(): read the 'CB1R - OX1R' / 'CB1R-OX1R' block of each fold CSV.
     Every non-empty column under a condition header = one independent experiment.
  2. fit_pooled(): one 4-parameter log(agonist)-response curve per condition, fitted by
     least squares to all per-experiment points pooled (Prism style, each experiment's
     value treated as a replicate Y). Reported value = best-fit, +/- = asymptotic SE.
     Emax = plateau at high agonist concentration (Bottom for cAMP, Top for barrestin2).
  3. cAMP 0.50 ug row: Hill slope constrained (|nH| = 1, sign of the downward curve).
  4. barrestin2 0.00 ug row: no clear asymptote -> Emax = mean +/- SEM of the observed
     response at the highest concentration; EC50 reported as a bound.
  5. stars(): one-way ANOVA + Tukey HSD from summary statistics (mean, SEM, n) per
     parameter, comparisons of each OX1 group against 0.00 ug.
"""
import sys
import os
import json
import math
import numpy as np
import pandas as pd
from scipy.optimize import curve_fit
from scipy import stats

DATA = sys.argv[1] if len(sys.argv) > 1 else "data"
OUT = sys.argv[2] if len(sys.argv) > 2 else "out"
HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = os.path.join(os.path.dirname(HERE), "template.json")
if not os.path.exists(TEMPLATE):
    TEMPLATE = os.path.join(os.path.dirname(os.path.abspath(DATA)), "template.json")

ROWS = {"0.00": "ox_000", "0.10": "ox_010", "0.25": "ox_025", "0.50": "ox_050"}


# ---------------------------------------------------------------- parsing
def parse_block(path, block_name):
    raw = pd.read_csv(path, header=None, dtype=str, keep_default_na=False)
    lines = raw.values.tolist()
    start = None
    for i, r in enumerate(lines):
        if r[0].replace(" ", "") == block_name.replace(" ", ""):
            start = i
            break
    if start is None:
        raise ValueError(f"block {block_name} not found in {path}")
    hdr = lines[start + 1]
    groups = {}
    cur = None
    for j, h in enumerate(hdr[1:], start=1):
        if h.strip():
            cur = h.strip().split()[0]  # '0.00'
            groups[cur] = []
        if cur is not None:
            groups[cur].append(j)
    x, rowsvals = [], []
    for r in lines[start + 2:]:
        if not r[0].strip():
            break
        x.append(float(r[0]))
        rowsvals.append(r)
    x = np.array(x)
    out = {}
    for g, cols in groups.items():
        exps = []
        for j in cols:
            col = [rv[j].strip() for rv in rowsvals]
            if all(c == "" for c in col):
                continue
            exps.append(np.array([float(c) if c else np.nan for c in col]))
        out[g] = np.column_stack(exps)  # shape (n_conc, n_exp)
    return x, out


# ---------------------------------------------------------------- model
def four_pl(x, bottom, top, logec50, hill):
    return bottom + (top - bottom) / (1.0 + 10.0 ** ((logec50 - x) * hill))


def fit_pooled(x, Y, hill_fixed=None):
    """Fit one curve to all points (each experiment value = replicate)."""
    xx = np.repeat(x, Y.shape[1])
    yy = Y.reshape(-1)
    m = ~np.isnan(yy)
    xx, yy = xx[m], yy[m]
    means = np.nanmean(Y, axis=1)
    lo_y, hi_y = means[0], means[-1]  # response at lowest / highest concentration
    p0_log = x[np.argmin(np.abs(means - (lo_y + hi_y) / 2))]
    sign = 1.0 if hi_y > lo_y else -1.0
    if hill_fixed is None:
        f = four_pl
        p0 = [lo_y, hi_y, p0_log, sign]
        names = ["Y0", "Yinf", "logEC50", "Hill"]
    else:
        f = lambda xv, a, b, c: four_pl(xv, a, b, c, hill_fixed)
        p0 = [lo_y, hi_y, p0_log]
        names = ["Y0", "Yinf", "logEC50"]
    # NB: with this parameterisation 'bottom' = response at x -> -inf when hill>0;
    # we fit with Y0 := asymptote at low x and Yinf := asymptote at high x by keeping
    # the sign of hill equal to the curve direction (cAMP: negative).
    best = None
    for shift in (0.0, -1.0, 1.0, -2.0, 2.0):
        try:
            pp = list(p0)
            pp[2] = p0_log + shift
            popt, pcov = curve_fit(f, xx, yy, p0=pp, maxfev=200000)
            rss = float(np.sum((yy - f(xx, *popt)) ** 2))
            if best is None or rss < best[2]:
                best = (popt, pcov, rss)
        except Exception:
            continue
    popt, pcov, rss = best
    se = np.sqrt(np.diag(pcov)) if np.all(np.isfinite(pcov)) else np.full(len(popt), np.inf)
    res = dict(zip(names, popt))
    res.update({k + "_se": s for k, s in zip(names, se)})
    if hill_fixed is not None:
        res["Hill"] = hill_fixed
        res["Hill_se"] = float("nan")
    # four_pl(x, bottom, top, ...): bottom is the asymptote for (logec50-x)*hill -> +inf
    # i.e. x -> -inf when hill > 0.  For hill < 0, 'bottom' is the x -> +inf asymptote.
    h = res["Hill"]
    a, b = popt[0], popt[1]
    a_se, b_se = se[0], se[1]
    if h > 0:
        res["low_plateau"], res["high_plateau"] = a, b
        res["low_plateau_se"], res["high_plateau_se"] = a_se, b_se
    else:
        res["low_plateau"], res["high_plateau"] = b, a
        res["low_plateau_se"], res["high_plateau_se"] = b_se, a_se
    res["n_exp"] = Y.shape[1]
    res["n_pts"] = len(yy)
    res["df"] = len(yy) - len(popt)
    res["rss"] = rss
    res["cv_logec50"] = abs(res["logEC50_se"] / res["logEC50"]) if res["logEC50"] else np.inf
    return res


# ---------------------------------------------------------------- stats
def tukey_from_summary(means, sems, ns, ref=0):
    """One-way ANOVA + Tukey-Kramer from summary data (mean, SEM, n). Returns p vs ref."""
    means, sems, ns = map(np.asarray, (means, sems, ns))
    sds = sems * np.sqrt(ns)
    k = len(means)
    N = ns.sum()
    grand = np.sum(ns * means) / N
    ssb = np.sum(ns * (means - grand) ** 2)
    ssw = np.sum((ns - 1) * sds ** 2)
    dfb, dfw = k - 1, N - k
    msw = ssw / dfw
    F = (ssb / dfb) / msw
    p_anova = stats.f.sf(F, dfb, dfw)
    ps = {}
    for i in range(k):
        if i == ref:
            continue
        q = abs(means[i] - means[ref]) / math.sqrt(msw / 2 * (1 / ns[i] + 1 / ns[ref]))
        ps[i] = float(stats.studentized_range.sf(q, k, dfw))
    return F, p_anova, ps


def star(p):
    if p is None or not np.isfinite(p):
        return ""
    if p < 0.001:
        return "***"
    if p < 0.01:
        return "**"
    if p < 0.05:
        return "*"
    return ""


def fmt(v):
    return float(v) if v is not None and np.isfinite(v) else "N/A"


# ---------------------------------------------------------------- main
def main():
    os.makedirs(OUT, exist_ok=True)
    tpl = json.load(open(TEMPLATE, encoding="utf-8"))
    cells = tpl["cells"]

    xc, camp = parse_block(os.path.join(DATA, "crc_cAMP_fold.csv"), "CB1R - OX1R")
    xb, barr = parse_block(os.path.join(DATA, "crc_barr2_fold.csv"), "CB1R-OX1R")
    print("cAMP experiments per group:", {k: v.shape[1] for k, v in camp.items()})
    print("barr2 experiments per group:", {k: v.shape[1] for k, v in barr.items()})

    results = {"camp": {}, "arr": {}}
    # ---- cAMP
    for g, Y in camp.items():
        r4 = fit_pooled(xc, Y)
        print(f"cAMP {g} 4PL: pEC50={-r4['logEC50']:.4f}+/-{r4['logEC50_se']:.4f} "
              f"Emax(high plateau)={r4['high_plateau']:.4f}+/-{r4['high_plateau_se']:.4f} "
              f"Hill={r4['Hill']:.4f}+/-{r4['Hill_se']:.4f} rss={r4['rss']:.4f}")
        if g == "0.50":  # F2 / S6: report Hill-constrained fit for this curve
            rc = fit_pooled(xc, Y, hill_fixed=-1.0)
            print(f"cAMP {g} nH=-1: pEC50={-rc['logEC50']:.4f}+/-{rc['logEC50_se']:.4f} "
                  f"Emax={rc['high_plateau']:.4f}+/-{rc['high_plateau_se']:.4f} rss={rc['rss']:.4f}")
            rc["constrained"] = True
            results["camp"][g] = rc
        else:
            r4["constrained"] = False
            results["camp"][g] = r4

    # ---- barrestin2
    for g, Y in barr.items():
        r4 = fit_pooled(xb, Y)
        print(f"barr2 {g} 4PL: pEC50={-r4['logEC50']:.4f}+/-{r4['logEC50_se']:.4f} "
              f"Emax={r4['high_plateau']:.4f}+/-{r4['high_plateau_se']:.4f} "
              f"Hill={r4['Hill']:.4f}+/-{r4['Hill_se']:.4f}")
        obs = Y[-1, :]
        r4["obs_emax"] = float(np.nanmean(obs))
        r4["obs_emax_se"] = float(np.nanstd(obs, ddof=1) / np.sqrt(np.sum(~np.isnan(obs))))
        # F3 / S5: the 0.00 ug curve has no clear asymptote -> observed Emax, EC50 bound
        r4["no_asymptote"] = (g == "0.00")
        results["arr"][g] = r4
        print(f"   observed response at 10 uM: {r4['obs_emax']:.4f} +/- {r4['obs_emax_se']:.4f}")

    # sensitivity: 0.00 ug group using only first 4 columns
    for lab, X, D in (("cAMP", xc, camp), ("barr2", xb, barr)):
        rs = fit_pooled(X, D["0.00"][:, :4])
        print(f"[sensitivity] {lab} 0.00 first-4-columns only: pEC50={-rs['logEC50']:.4f} "
              f"Emax={rs['high_plateau']:.4f} Hill={rs['Hill']:.4f}; "
              f"obs@10uM={np.mean(D['0.00'][-1, :4]):.4f}")

    # ---- fill cells
    order = ["0.00", "0.10", "0.25", "0.50"]

    def put(key, value, src, stars="", unit=None):
        c = cells[key]
        c["value"] = value
        c["stars"] = stars
        c["source"] = src
        if unit is not None:
            c["unit"] = unit

    # stars per parameter
    def param_summary(assay, pname):
        m, s, n = [], [], []
        for g in order:
            r = results[assay][g]
            if pname == "pec50":
                m.append(-r["logEC50"]); s.append(r["logEC50_se"])
            elif pname == "emax":
                if assay == "arr" and r["no_asymptote"]:
                    m.append(r["obs_emax"]); s.append(r["obs_emax_se"])
                else:
                    m.append(r["high_plateau"]); s.append(r["high_plateau_se"])
            elif pname == "hill":
                m.append(r["Hill"]); s.append(r["Hill_se"])
            n.append(r["n_exp"])
        return m, s, n

    star_map = {}
    for assay in ("camp", "arr"):
        for pname in ("pec50", "emax", "hill"):
            m, s, n = param_summary(assay, pname)
            valid = [i for i in range(4) if np.isfinite(m[i]) and np.isfinite(s[i])]
            # exclude bounds / constrained values from tests
            if assay == "arr" and pname in ("pec50", "hill"):
                valid = [i for i in valid if not results["arr"][order[i]]["no_asymptote"]]
            if assay == "camp" and pname == "hill":
                valid = [i for i in valid if not results["camp"][order[i]]["constrained"]]
            if 0 not in valid or len(valid) < 3:
                print(f"ANOVA {assay} {pname}: skipped (reference or groups not estimable)")
                star_map[(assay, pname)] = {}
                continue
            F, pa, ps = tukey_from_summary([m[i] for i in valid], [s[i] for i in valid],
                                           [n[i] for i in valid], ref=0)
            pmap = {order[valid[i]]: p for i, p in ps.items()}
            print(f"ANOVA {assay} {pname}: F={F:.3f} p={pa:.4g}; Tukey p vs 0.00: "
                  + ", ".join(f"{g}:{p:.4g}" for g, p in pmap.items()))
            star_map[(assay, pname)] = pmap if pa < 0.05 else {g: 1.0 for g in pmap}

    for g in order:
        row = ROWS[g]
        # cAMP
        r = results["camp"][g]
        src = "main/cAMP: fit_pooled(hill_fixed=-1) [S6/F2]" if r["constrained"] else "main/cAMP: fit_pooled 4PL"
        pec = -r["logEC50"]
        put(f"{row}|camp_pec50", pec, src, star(star_map[("camp", "pec50")].get(g)))
        put(f"{row}|camp_pec50_se", fmt(r["logEC50_se"]), src + " (SE of fit)")
        put(f"{row}|camp_ec50", 10 ** (-pec) * 1e9, src + " (10^-pEC50 in nM)")
        put(f"{row}|camp_emax", r["high_plateau"], src + " (high-concentration plateau)",
            star(star_map[("camp", "emax")].get(g)))
        put(f"{row}|camp_emax_se", fmt(r["high_plateau_se"]), src + " (SE of fit)")
        if r["constrained"]:
            put(f"{row}|camp_hill", 1.0, src + " (constrained, |nH|=1; fitted as -1 for downward curve)")
            put(f"{row}|camp_hill_se", "N/A", src + " (constrained, no SE)")
        else:
            put(f"{row}|camp_hill", r["Hill"], src, star(star_map[("camp", "hill")].get(g)))
            put(f"{row}|camp_hill_se", fmt(r["Hill_se"]), src + " (SE of fit)")
        # barrestin2
        r = results["arr"][g]
        if r["no_asymptote"]:
            src = "main/barr2: observed response at 10 uM (mean+/-SEM) [F3/S5]; EC50 bound"
            # EC50 bound: curve still rising at the top concentration, so EC50 >= the
            # half-maximal concentration of the observed response -> report lower bound on
            # EC50 from the fitted curve (upper bound on pEC50), capped by the fit.
            pec_bound = -r["logEC50"]
            put(f"{row}|arr_pec50", f"<{pec_bound:.4f}", src + " ; bound = fitted pEC50 of unconstrained 4PL")
            put(f"{row}|arr_pec50_se", "N/A", src)
            put(f"{row}|arr_ec50", f">{10 ** (-pec_bound) * 1e9:.4g}", src + " ; bound in nM")
            put(f"{row}|arr_emax", r["obs_emax"], src, star(star_map[("arr", "emax")].get(g)))
            put(f"{row}|arr_emax_se", r["obs_emax_se"], src + " (SEM across experiments)")
            put(f"{row}|arr_hill", r["Hill"], "main/barr2: fit_pooled 4PL (Hill from unconstrained fit)")
            put(f"{row}|arr_hill_se", fmt(r["Hill_se"]), "main/barr2: fit_pooled 4PL (SE of fit)")
        else:
            src = "main/barr2: fit_pooled 4PL"
            pec = -r["logEC50"]
            put(f"{row}|arr_pec50", pec, src)
            put(f"{row}|arr_pec50_se", fmt(r["logEC50_se"]), src + " (SE of fit)")
            put(f"{row}|arr_ec50", 10 ** (-pec) * 1e9, src + " (10^-pEC50 in nM)")
            put(f"{row}|arr_emax", r["high_plateau"], src + " (top plateau)",
                star(star_map[("arr", "emax")].get(g)))
            put(f"{row}|arr_emax_se", fmt(r["high_plateau_se"]), src + " (SE of fit)")
            put(f"{row}|arr_hill", r["Hill"], src)
            put(f"{row}|arr_hill_se", fmt(r["Hill_se"]), src + " (SE of fit)")

    with open(os.path.join(OUT, "filled.json"), "w", encoding="utf-8") as fh:
        json.dump(tpl, fh, indent=1, ensure_ascii=False)
    print("\nFilled table:")
    for g in order:
        row = ROWS[g]
        print(row, {k.split("|")[1]: (v["value"], v["stars"]) for k, v in cells.items()
                    if k.startswith(row + "|")})
    print("wrote", os.path.join(OUT, "filled.json"))


if __name__ == "__main__":
    main()
