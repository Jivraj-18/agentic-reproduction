"""Reproduce Table 1 (CB1-OX1: cAMP inhibition and barrestin2 recruitment by CP55,940).

Usage: python -I out/repro_table.py data out
"""
import sys, os, json, csv, copy
import numpy as np
from scipy.optimize import curve_fit
from scipy import stats
from statsmodels.stats.multicomp import pairwise_tukeyhsd  # noqa: F401  (used in sensitivity)

DATA, OUT = sys.argv[1], sys.argv[2]
HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = os.path.join(os.path.dirname(HERE), "template.json")
if not os.path.exists(TEMPLATE):
    TEMPLATE = os.path.join(os.path.dirname(os.path.abspath(DATA)), "template.json")

DOSES = ["0.00", "0.10", "0.25", "0.50"]
ROW_ID = {"0.00": "ox_000", "0.10": "ox_010", "0.25": "ox_025", "0.50": "ox_050"}


# ---------------------------------------------------------------- data reading
def read_block(path, block_name):
    """Return {dose: (x array, Y matrix [conc x experiment])} for one block."""
    with open(path, encoding="utf-8") as fh:
        rows = list(csv.reader(fh))
    norm = lambda s: s.replace(" ", "").upper()
    start = next(i for i, r in enumerate(rows) if norm(r[0]) == norm(block_name))
    header = rows[start + 1]
    # group columns: a header cell with a label begins a group of 8 columns
    groups = []
    for j, h in enumerate(header):
        if j > 0 and h.strip():
            groups.append((h.split()[0], j))
    out = {}
    data_rows = []
    for r in rows[start + 2:]:
        if not r[0].strip():
            break
        data_rows.append(r)
    x = np.array([float(r[0]) for r in data_rows])
    for gi, (dose, j0) in enumerate(groups):
        j1 = groups[gi + 1][1] if gi + 1 < len(groups) else len(header)
        cols = []
        for j in range(j0, j1):
            vals = [r[j].strip() if j < len(r) else "" for r in data_rows]
            if all(v == "" for v in vals):
                continue
            cols.append([float(v) if v else np.nan for v in vals])
        out[dose] = (x, np.array(cols).T)
    return out


# ---------------------------------------------------------------- models
def fourpl(x, bottom, top, logec50, hill):
    # GraphPad Prism "log(agonist) vs. response -- Variable slope"
    return bottom + (top - bottom) / (1.0 + 10 ** ((logec50 - x) * hill))


def threepl(x, bottom, top, logec50):
    # Prism "log(agonist) vs. response" (Hill slope fixed at 1)
    return bottom + (top - bottom) / (1.0 + 10 ** (logec50 - x))


def fit_curve(x, Y, model, decreasing):
    """Least-squares fit of pooled points (each independent experiment value is one point)."""
    xs = np.repeat(x, Y.shape[1])
    ys = Y.ravel()
    ok = ~np.isnan(ys)
    xs, ys = xs[ok], ys[ok]
    lo, hi = ys.min(), ys.max()
    if model == "4pl":
        p0 = [lo, hi, -7.5, -1.0 if decreasing else 1.0]
        f = fourpl
    else:
        # Prism 3-parameter: Hill = +1, so a decreasing curve has Top < Bottom
        p0 = [hi, lo, -7.5] if decreasing else [lo, hi, -7.5]
        f = threepl
    best = None
    for le in [-9, -8, -7.5, -7, -6, -5]:
        p0[2] = le
        try:
            if model == "4pl":
                # keep the curve direction fixed (Hill sign) as in a Prism agonist/inhibition fit
                bnd = ([-np.inf, -np.inf, -np.inf, -20], [np.inf, np.inf, np.inf, 0]) if decreasing                     else ([-np.inf, -np.inf, -np.inf, 0], [np.inf, np.inf, np.inf, 20])
                p, cov = curve_fit(f, xs, ys, p0=p0, bounds=bnd, maxfev=20000)
            else:
                p, cov = curve_fit(f, xs, ys, p0=p0, maxfev=20000)
        except Exception:
            continue
        rss = np.sum((ys - f(xs, *p)) ** 2)
        if best is None or rss < best[2]:
            best = (p, cov, rss)
    p, cov, rss = best
    se = np.sqrt(np.diag(cov))
    dof = len(ys) - len(p)
    return dict(p=p, se=se, rss=rss, dof=dof, n_points=len(ys))


def four_pl_failed(fit, x):
    """Objective rule for 'could not be accurately estimated' (S6):
    logEC50 outside the tested range, or SE of logEC50 / Hill larger than the estimate scale."""
    b, t, le, h = fit["p"]
    se_le, se_h = fit["se"][2], fit["se"][3]
    return (not np.isfinite(se_le)) or le < x.min() or le > x.max() or se_le > 1.0 \
        or (not np.isfinite(se_h)) or abs(se_h) > abs(h)


# ---------------------------------------------------------------- assays
def analyse_camp(blocks):
    res = {}
    for d in DOSES:
        x, Y = blocks[d]
        f4 = fit_curve(x, Y, "4pl", decreasing=True)
        failed = four_pl_failed(f4, x)
        print(f"cAMP {d} ug n={Y.shape[1]} 4PL p={np.round(f4['p'],4)} se={np.round(f4['se'],4)} failed={failed}")
        if d == "0.50":  # F2 footnote a marks only the 0.50 ug row (failed flag is logged only)
            f3 = fit_curve(x, Y, "3pl", decreasing=True)
            b, t, le = f3["p"]
            sb, st, sle = f3["se"]
            print(f"   constrained fit (Hill=1): p={np.round(f3['p'],4)} se={np.round(f3['se'],4)}")
            # decreasing curve with Prism's Hill=+1 equation: Top (curve end at high x) < Bottom
            emax, emax_se = (t, st) if t < b else (b, sb)
            res[d] = dict(pec50=-le, pec50_se=sle, emax=emax, emax_se=emax_se,
                          hill=1.0, hill_se="N/A", n=Y.shape[1], src="analyse_camp:3PL_hill_fixed_1",
                          failed4=failed)
        else:
            b, t, le, h = f4["p"]
            sb, st, sle, sh = f4["se"]
            emax, emax_se = (b, sb) if b < t else (t, st)  # lower plateau = max inhibition
            res[d] = dict(pec50=-le, pec50_se=sle, emax=emax, emax_se=emax_se,
                          hill=h, hill_se=sh, n=Y.shape[1], src="analyse_camp:4PL_pooled",
                          failed4=failed)
    return res


def analyse_arr(blocks):
    res = {}
    for d in DOSES:
        x, Y = blocks[d]
        f4 = fit_curve(x, Y, "4pl", decreasing=False)
        b, t, le, h = f4["p"]
        sb, st, sle, sh = f4["se"]
        failed = four_pl_failed(f4, x)
        print(f"barr2 {d} ug n={Y.shape[1]} 4PL p={np.round(f4['p'],4)} se={np.round(f4['se'],4)} failed={failed}")
        r = dict(pec50=-le, pec50_se=sle, emax=t, emax_se=st, hill=h, hill_se=sh,
                 n=Y.shape[1], src="analyse_arr:4PL_pooled", failed4=failed)
        if d == "0.00":
            # F3 / S5: no clear asymptote -> Emax = observed (mean response at the highest
            # concentration across independent experiments, +/- SEM); EC50 reported as a bound.
            top_conc = Y[np.argmax(x)]
            top_conc = top_conc[~np.isnan(top_conc)]
            r["emax"] = float(np.mean(top_conc))
            r["emax_se"] = float(stats.sem(top_conc))
            r["emax_src"] = "analyse_arr:observed_mean_at_10uM"
            r["fit_pec50"] = -le
            # bound: curve still rising at the top tested concentration -> EC50 > midpoint
            # cannot be placed; use the half-max of the observed data: EC50 is at least the
            # concentration where the observed mean crosses 50% of the observed Emax.
            r["bound"] = True
            print(f"   observed Emax={r['emax']:.4f} +/- {r['emax_se']:.4f}; fitted pEC50 (not reported)={-le:.4f}")
        res[d] = r
    return res


# ---------------------------------------------------------------- statistics
def tukey_from_summary(means, sems, ns):
    """One-way ANOVA + Tukey HSD from summary statistics (mean, SEM, n per group),
    as GraphPad Prism does for 'Mean, SEM, N' data tables. Returns p-values vs group 0."""
    means, sems, ns = map(np.asarray, (means, sems, ns))
    sds = sems * np.sqrt(ns)
    k, N = len(means), ns.sum()
    dfw = N - k
    msw = np.sum((ns - 1) * sds ** 2) / dfw
    out = []
    for i in range(1, k):
        q = abs(means[i] - means[0]) / np.sqrt(msw / 2 * (1 / ns[i] + 1 / ns[0]))
        out.append(float(stats.studentized_range.sf(q, k, dfw)))
    grand = np.sum(ns * means) / N
    F = np.sum(ns * (means - grand) ** 2) / (k - 1) / msw
    pF = float(stats.f.sf(F, k - 1, dfw))
    return out, pF


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


# ---------------------------------------------------------------- per-experiment sensitivity
def per_experiment_sensitivity(blocks, decreasing, label):
    print(f"\n[sensitivity] {label}: per-experiment 4PL fits, mean +/- SEM, ANOVA/Tukey on fitted params")
    vals = {}
    for d in DOSES:
        x, Y = blocks[d]
        pars = []
        for j in range(Y.shape[1]):
            try:
                f = fit_curve(x, Y[:, [j]], "4pl", decreasing)
                b, t, le, h = f["p"]
                emax = min(b, t) if decreasing else max(b, t)
                pars.append((-le, emax, h))
            except Exception:
                pars.append((np.nan,) * 3)
        pars = np.array(pars)
        vals[d] = pars
        m = np.nanmean(pars, axis=0)
        s = stats.sem(pars, axis=0, nan_policy="omit")
        print(f"  {d}: pEC50 {m[0]:.3f}+/-{s[0]:.3f}  Emax {m[1]:.3f}+/-{s[1]:.3f}  Hill {m[2]:.3f}+/-{s[2]:.3f}")
    for k, name in enumerate(["pEC50", "Emax", "Hill"]):
        allv = np.concatenate([vals[d][:, k] for d in DOSES])
        grp = np.concatenate([[d] * len(vals[d]) for d in DOSES])
        ok = np.isfinite(allv)
        t = pairwise_tukeyhsd(allv[ok], grp[ok])
        ps = {(a, b): p for (a, b), p in zip(
            [(t.groupsunique[i], t.groupsunique[j]) for i in range(len(t.groupsunique))
             for j in range(i + 1, len(t.groupsunique))], t.pvalues)}
        print(f"  Tukey vs 0.00 {name}: " + ", ".join(f"{d}: p={ps[('0.00', d)]:.4g}" for d in DOSES[1:]))


# ---------------------------------------------------------------- main
def main():
    camp_blocks = read_block(os.path.join(DATA, "crc_cAMP_fold.csv"), "CB1R - OX1R")
    arr_blocks = read_block(os.path.join(DATA, "crc_barr2_fold.csv"), "CB1R-OX1R")
    for d in DOSES:
        print(f"n experiments {d} ug: cAMP={camp_blocks[d][1].shape[1]} barr2={arr_blocks[d][1].shape[1]}")

    camp = analyse_camp(camp_blocks)
    arr = analyse_arr(arr_blocks)

    with open(TEMPLATE, encoding="utf-8") as fh:
        tpl = json.load(fh)
    filled = copy.deepcopy(tpl)
    cells = filled["cells"]

    # ---- significance (ANOVA from summary stats; group 0.00 is the reference)
    stars = {}
    for assay, res in (("camp", camp), ("arr", arr)):
        for par in ("pec50", "emax", "hill"):
            groups = [d for d in DOSES if isinstance(res[d][par + "_se"], float)
                      or isinstance(res[d][par + "_se"], np.floating)]
            if assay == "arr" and par == "pec50":
                groups = [d for d in groups if not res[d].get("bound")]
            if "0.00" not in groups or len(groups) < 3:
                # reference not estimable -> no comparison possible
                for d in DOSES:
                    stars[(assay, par, d)] = ""
                print(f"ANOVA {assay} {par}: reference group not estimable / too few groups; no stars")
                continue
            ps, pF = tukey_from_summary([res[d][par] for d in groups],
                                        [res[d][par + "_se"] for d in groups],
                                        [res[d]["n"] for d in groups])
            print(f"ANOVA {assay} {par} groups={groups}: F p={pF:.4g}; Tukey vs 0.00: " +
                  ", ".join(f"{g}: p={p:.4g}" for g, p in zip(groups[1:], ps)))
            stars[(assay, par, "0.00")] = ""
            for g, p in zip(groups[1:], ps):
                stars[(assay, par, g)] = star(p)
            for d in DOSES:
                stars.setdefault((assay, par, d), "")

    def setc(key, value, stars_, source, unit=None):
        c = cells[key]
        if isinstance(value, (float, np.floating)):
            value = float(value)
        c["value"] = value
        c["stars"] = stars_
        c["source"] = source
        if unit is not None:
            c["unit"] = unit

    for d in DOSES:
        rid = ROW_ID[d]
        for assay, res in (("camp", camp), ("arr", arr)):
            r = res[d]
            src = r["src"]
            if assay == "arr" and r.get("bound"):
                # EC50 bound: curve not saturated by top tested concentration (10 uM)
                xmax = float(np.max(arr_blocks[d][0]))
                setc(f"{rid}|{assay}_pec50", f"<{-xmax:.4g}", "", "analyse_arr:bound_no_asymptote")
                setc(f"{rid}|{assay}_pec50_se", "N/A", "", "analyse_arr:bound_no_asymptote")
                setc(f"{rid}|{assay}_ec50", f">{10 ** xmax * 1e9:.6g}", "", "analyse_arr:bound_no_asymptote")
                setc(f"{rid}|{assay}_emax", r["emax"], stars[(assay, "emax", d)], r["emax_src"])
                setc(f"{rid}|{assay}_emax_se", r["emax_se"], "", r["emax_src"])
                setc(f"{rid}|{assay}_hill", r["hill"], stars[(assay, "hill", d)], src)
                setc(f"{rid}|{assay}_hill_se", r["hill_se"], "", src)
                continue
            setc(f"{rid}|{assay}_pec50", r["pec50"], stars[(assay, "pec50", d)], src)
            setc(f"{rid}|{assay}_pec50_se", r["pec50_se"], "", src)
            setc(f"{rid}|{assay}_ec50", 10 ** (-r["pec50"]) * 1e9, "", src + ":10^-pEC50 in nM")
            setc(f"{rid}|{assay}_emax", r["emax"], stars[(assay, "emax", d)], src)
            setc(f"{rid}|{assay}_emax_se", r["emax_se"], "", src)
            setc(f"{rid}|{assay}_hill", r["hill"], stars[(assay, "hill", d)], src)
            setc(f"{rid}|{assay}_hill_se", r["hill_se"], "", src)

    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "filled.json"), "w", encoding="utf-8") as fh:
        json.dump(filled, fh, indent=1, ensure_ascii=False)

    print("\nFilled table:")
    for d in DOSES:
        rid = ROW_ID[d]
        print(rid, {k.split("|")[1]: (v["value"] if not isinstance(v["value"], float) else round(v["value"], 4), v["stars"])
                    for k, v in cells.items() if k.startswith(rid)})

    per_experiment_sensitivity(camp_blocks, True, "cAMP")
    per_experiment_sensitivity(arr_blocks, False, "barr2")


if __name__ == "__main__":
    main()
