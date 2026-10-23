"""Reproduce Table 1 (CB1-OX1: cAMP inhibition and barrestin2 recruitment, CP55,940).

Usage: python -I out/repro_table.py data out

Pipeline (see out/assumptions.md for the reasoning behind each choice):
  parse_block        read the CB1-OX1 block of each CSV (fold data, 1 column = 1 independent experiment)
  select_control     choose which of the 8 deposited 0.00 ug columns belong to the OX1 series
  fit_logistic       Prism 'log(agonist) vs response' least-squares fit, variable slope or Hill fixed
  fit_group_global   PRIMARY: one curve per transfection group fitted to all experiment points
                     (Prism XY table with replicate sub-columns); 4PL -> Hill=1 fallback (S6) -> bound (S5)
  summary_anova      one-way ANOVA + Tukey HSD from summary data (estimate, SE as SEM, n experiments)
  sensitivity_*      alternative readings printed to run.log only (not written to filled.json)
"""
import csv
import json
import os
import sys

import numpy as np
from scipy.optimize import least_squares
from scipy import stats

DATA_DIR = sys.argv[1] if len(sys.argv) > 1 else "data"
OUT_DIR = sys.argv[2] if len(sys.argv) > 2 else "out"
HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_CANDIDATES = [os.path.join(DATA_DIR, "..", "template.json"), os.path.join(HERE, "..", "template.json")]

GROUPS = ["0.00", "0.10", "0.25", "0.50"]
ROW_IDS = {"0.00": "ox_000", "0.10": "ox_010", "0.25": "ox_025", "0.50": "ox_050"}
GROUP_START = {"0.00": 1, "0.10": 9, "0.25": 17, "0.50": 25}  # 8 sub-columns per group

# Assumption A1: control columns of the OX1 experiment series (0-based within the 8 mock columns)
MATCHED_CTRL_COLS = {"barr2": [0, 1, 2, 3], "camp": [4, 5, 6, 7]}

# Assumption A5: operational rule for "pEC50/Hill could not be accurately estimated"
TESTED_RANGE = (-10.0, -5.0)
LOGEC50_LIMITS = (TESTED_RANGE[0] - 1.0, TESTED_RANGE[1] + 1.0)
MAX_SE_LOGEC50 = 1.0      # log units
MAX_REL_SE_HILL = 1.0     # SE(Hill)/|Hill|
HILL_ABS_LIMITS = (0.1, 10.0)


# ----------------------------------------------------------------------------- parsing
def parse_block(path, block_name):
    with open(path, newline="", encoding="utf-8-sig") as fh:
        rows = list(csv.reader(fh))
    key = block_name.replace(" ", "")
    start = next(i for i, r in enumerate(rows) if r and r[0].replace(" ", "") == key)
    hdr = rows[start + 1]
    data_rows = []
    for r in rows[start + 2:]:
        try:
            float(r[0])
        except (ValueError, IndexError):
            break
        data_rows.append(r)
    x = np.array([float(r[0]) for r in data_rows])
    out = {}
    for g, s in GROUP_START.items():
        assert hdr[s].startswith(g), (hdr[s], g)
        cols = []
        for c in range(s, s + 8):
            vals = [r[c].strip() if c < len(r) else "" for r in data_rows]
            if all(v != "" for v in vals):
                cols.append([float(v) for v in vals])
        out[g] = np.array(cols).T
    return x, out


def select_control(groups, assay, mode):
    g = dict(groups)
    if mode == "matched":
        g["0.00"] = groups["0.00"][:, MATCHED_CTRL_COLS[assay]]
    return g


# ----------------------------------------------------------------------------- model
def logistic(x, bottom, top, logec50, hill):
    """Prism: Y = Bottom + (Top-Bottom)/(1+10^((LogEC50-X)*HillSlope))."""
    with np.errstate(over="ignore"):
        return bottom + (top - bottom) / (1.0 + 10.0 ** ((logec50 - x) * hill))


def fit_logistic(x, y, hill_fixed=None):
    """Least squares (Levenberg-Marquardt, multi-start). Returns canonical parameters:
    Bottom = low-concentration plateau, Top = high-concentration plateau (so for cAMP inhibition
    the Hill slope is negative, as Prism reports), plus asymptotic SEs."""
    y0, y1 = float(np.mean(y[x == x.min()])), float(np.mean(y[x == x.max()]))
    best = None
    for le0 in (-9.0, -8.0, -7.0, -6.0, -5.5):
        for h0 in ((1.0, -1.0) if hill_fixed is None else (None,)):
            if hill_fixed is None:
                p0 = [y0, y1, le0, h0 if y1 > y0 else -h0]
                res = lambda p: logistic(x, p[0], p[1], p[2], p[3]) - y
            else:
                p0 = [y0, y1, le0]
                res = lambda p: logistic(x, p[0], p[1], p[2], hill_fixed) - y
            try:
                r = least_squares(res, p0, method="lm", max_nfev=20000)
            except Exception:
                continue
            if best is None or r.cost < best.cost:
                best = r
    p = list(best.x)
    k = len(p)
    dof = max(len(y) - k, 1)
    s2 = 2 * best.cost / dof
    try:
        se = list(np.sqrt(np.abs(np.diag(np.linalg.inv(best.jac.T @ best.jac) * s2))))
    except np.linalg.LinAlgError:
        se = [np.inf] * k
    if hill_fixed is None:
        b, t, le, h = p
        sb, st, sle, sh = se
    else:
        b, t, le = p
        h, sh = hill_fixed, None
        sb, st, sle = se
    # canonicalise: the low-X plateau is Bottom when h>0; Prism parameterisation is symmetric
    # under (Bottom,Top,h) -> (Top,Bottom,-h); we keep Bottom = low-X plateau.
    if h < 0 and hill_fixed is None:
        pass
    low_x, high_x = (b, t) if h > 0 else (t, b)
    se_low, se_high = (sb, st) if h > 0 else (st, sb)
    # report Hill sign by direction of the response (rise -> +, fall -> -)
    direction = 1.0 if high_x > low_x else -1.0
    hill_signed = direction * abs(h)
    return dict(baseline=low_x, emax=high_x, se_baseline=se_low, se_emax=se_high,
                logec50=le, se_logec50=sle, hill=hill_signed, se_hill=sh,
                converged=bool(best.success), sse=2 * best.cost, n=len(y))


def fit_ok(f, four_param):
    if not f["converged"] or not np.isfinite(f["logec50"]):
        return False
    if not (LOGEC50_LIMITS[0] <= f["logec50"] <= LOGEC50_LIMITS[1]):
        return False
    if not (np.isfinite(f["se_logec50"]) and f["se_logec50"] <= MAX_SE_LOGEC50):
        return False
    if four_param:
        if not (HILL_ABS_LIMITS[0] <= abs(f["hill"]) <= HILL_ABS_LIMITS[1]):
            return False
        if not (np.isfinite(f["se_hill"]) and f["se_hill"] <= MAX_REL_SE_HILL * abs(f["hill"])):
            return False
    return True


def fmt_fit(f):
    sh = "fixed" if f["se_hill"] is None else f"{f['se_hill']:.4g}"
    return (f"base={f['baseline']:.4f} Emax={f['emax']:.4f}+-{f['se_emax']:.4g} "
            f"logEC50={f['logec50']:.4f}+-{f['se_logec50']:.4g} Hill={f['hill']:.4f}+-{sh} "
            f"SSE={f['sse']:.4g}")


# ----------------------------------------------------------------------------- primary: global fit per group
def fit_group_global(x, Y, assay, log):
    n_exp = Y.shape[1]
    X = np.repeat(x, n_exp)
    yy = Y.ravel()  # row-major: each concentration, all experiments
    f4 = fit_logistic(X, yy)
    log(f"      4PL     : {fmt_fit(f4)} ok={fit_ok(f4, True)}")
    if fit_ok(f4, True):
        return dict(model="4PL", fit=f4, n=n_exp, Y=Y)
    h = -1.0 if assay == "camp" else 1.0
    f3 = fit_logistic(X, yy, hill_fixed=h)
    log(f"      Hill=1  : {fmt_fit(f3)} ok={fit_ok(f3, False)}")
    if fit_ok(f3, False):
        return dict(model="Hill=1", fit=f3, n=n_exp, Y=Y)
    return dict(model="not_estimable", fit=f3, n=n_exp, Y=Y)


def summarise(res, assay):
    """Convert a group fit into table quantities (value, SE, n)."""
    f, model, n = res["fit"], res["model"], res["n"]
    if model == "not_estimable":
        # S5: Emax = mean of greatest response observed (per experiment), EC50 as a bound
        Y = res["Y"]
        greatest = Y.min(axis=0) if assay == "camp" else Y.max(axis=0)
        return dict(pec50=f"<{-TESTED_RANGE[1]:g}", pec50_se="N/A", ec50=f">{10 ** TESTED_RANGE[1] * 1e9:g}",
                    emax=float(np.mean(greatest)), emax_se=float(np.std(greatest, ddof=1) / np.sqrt(n)),
                    hill="N/A", hill_se="N/A", n=n, model=model)
    pec50 = -f["logec50"]
    return dict(pec50=float(pec50), pec50_se=float(f["se_logec50"]), ec50=float(10 ** (-pec50) * 1e9),
                emax=float(f["emax"]), emax_se=float(f["se_emax"]),
                hill=float(f["hill"]), hill_se=(float(f["se_hill"]) if f["se_hill"] is not None else "N/A"),
                n=n, model=model)


# ----------------------------------------------------------------------------- stats
def stars_from_p(p):
    if p is None or not np.isfinite(p):
        return ""
    if p < 0.001:
        return "***"
    if p < 0.01:
        return "**"
    if p < 0.05:
        return "*"
    return ""


def summary_anova(means, sems, ns):
    """One-way ANOVA + Tukey-Kramer from summary data (Prism 'enter mean, SEM, N').
    Returns (F, p_anova, {group: p_tukey vs first group})."""
    means, sems, ns = map(lambda a: np.asarray(a, float), (means, sems, ns))
    sds = sems * np.sqrt(ns)
    k, N = len(means), ns.sum()
    grand = np.sum(ns * means) / N
    ssb = np.sum(ns * (means - grand) ** 2)
    ssw = np.sum((ns - 1) * sds ** 2)
    dfb, dfw = k - 1, N - k
    msw = ssw / dfw
    F = (ssb / dfb) / msw
    p_anova = stats.f.sf(F, dfb, dfw)
    p_vs_ref = {}
    for i in range(1, k):
        q = abs(means[i] - means[0]) / np.sqrt(msw / 2 * (1 / ns[i] + 1 / ns[0]))
        p_vs_ref[i] = float(stats.studentized_range.sf(q, k, dfw))
    return float(F), float(p_anova), p_vs_ref


def raw_anova(groups_vals):
    """One-way ANOVA + Tukey on per-experiment values (sensitivity analysis)."""
    arrs = [np.asarray(v, float) for v in groups_vals]
    means = [a.mean() for a in arrs]
    sems = [a.std(ddof=1) / np.sqrt(len(a)) for a in arrs]
    return summary_anova(means, sems, [len(a) for a in arrs])


def stats_for_table(summ, log, label):
    out = {}
    for par, se_key in (("pec50", "pec50_se"), ("emax", "emax_se"), ("hill", "hill_se")):
        if not all(isinstance(summ[g][se_key], float) for g in GROUPS):
            log(f"    {label} {par}: ANOVA not run (no SE for at least one group)")
            out[par] = {}
            continue
        F, pa, pv = summary_anova([summ[g][par] for g in GROUPS], [summ[g][se_key] for g in GROUPS],
                                  [summ[g]["n"] for g in GROUPS])
        out[par] = {GROUPS[i]: p for i, p in pv.items()}
        log(f"    {label} {par}: ANOVA F={F:.4f} p={pa:.4g}; Tukey p vs 0.00: "
            + ", ".join(f"{g}:{out[par][g]:.4g}" for g in GROUPS[1:]))
    return out


# ----------------------------------------------------------------------------- sensitivity
def sensitivity_per_experiment(x, groups, assay, log):
    """Alternative S2/S4/S7 reading: fit each experiment, mean +- SEM, ANOVA on per-experiment values."""
    log(f"  [sensitivity: per-experiment fits, {assay}]")
    h = -1.0 if assay == "camp" else 1.0
    vals = {}
    for g in GROUPS:
        Y = groups[g]
        f4 = [fit_logistic(x, Y[:, j]) for j in range(Y.shape[1])]
        if all(fit_ok(f, True) for f in f4):
            fits, model = f4, "4PL"
        else:
            fits, model = [fit_logistic(x, Y[:, j], hill_fixed=h) for j in range(Y.shape[1])], "Hill=1"
        pe = np.array([-f["logec50"] for f in fits])
        em = np.array([f["emax"] for f in fits])
        hl = np.array([f["hill"] for f in fits])
        vals[g] = (pe, em, hl, model)
        sem = lambda a: a.std(ddof=1) / np.sqrt(len(a))
        log(f"    {g}: model={model} pEC50={pe.mean():.4f}+-{sem(pe):.4f} Emax={em.mean():.4f}+-{sem(em):.4f} "
            f"Hill={hl.mean():.4f}+-{sem(hl):.4f}  (per-exp logEC50 {np.round(-pe, 2).tolist()})")
    for i, par in enumerate(("pEC50", "Emax", "Hill")):
        F, pa, pv = raw_anova([vals[g][i] for g in GROUPS])
        log(f"    {par}: ANOVA p={pa:.4g}; Tukey vs 0.00: " + ", ".join(f"{GROUPS[k]}:{p:.4g}" for k, p in pv.items()))


# ----------------------------------------------------------------------------- main
def analyse_assay(x, groups, assay, log):
    summ = {}
    for g in GROUPS:
        log(f"  [{assay}] {g} ug OX1, n={groups[g].shape[1]} experiments")
        res = fit_group_global(x, groups[g], assay, log)
        summ[g] = summarise(res, assay)
        s = summ[g]
        log(f"      -> {s['model']}: pEC50={s['pec50']} +- {s['pec50_se']} (EC50 {s['ec50']} nM) "
            f"Emax={s['emax']} +- {s['emax_se']} Hill={s['hill']} +- {s['hill_se']}")
    pvals = stats_for_table(summ, log, assay)
    return summ, pvals


def main():
    lines = []

    def log(s=""):
        print(s)
        lines.append(s)

    tpl_path = next(p for p in TEMPLATE_CANDIDATES if os.path.exists(p))
    with open(tpl_path, encoding="utf-8") as fh:
        filled = json.load(fh)

    sources = {
        "camp": (os.path.join(DATA_DIR, "crc_cAMP_fold.csv"), "CB1R - OX1R", "camp"),
        "barr2": (os.path.join(DATA_DIR, "crc_barr2_fold.csv"), "CB1R-OX1R", "arr"),
    }
    for assay, (path, block, pf) in sources.items():
        x, raw = parse_block(path, block)
        groups = select_control(raw, assay, "matched")
        log(f"== PRIMARY {assay}: block '{block}', log[M] = {x.tolist()}, control columns "
            f"{[c + 1 for c in MATCHED_CTRL_COLS[assay]]} of 8")
        summ, pvals = analyse_assay(x, groups, assay, log)
        for g in GROUPS:
            s, rid = summ[g], ROW_IDS[g]
            src = (f"fit_group_global[{s['model']}] (global fit, n={s['n']} expts) -> summarise(); "
                   f"stars: summary_anova() Tukey vs 0.00 ug")
            cells = {
                "pec50": (s["pec50"], "pec50"), "pec50_se": (s["pec50_se"], None), "ec50": (s["ec50"], None),
                "emax": (s["emax"], "emax"), "emax_se": (s["emax_se"], None),
                "hill": (s["hill"], "hill"), "hill_se": (s["hill_se"], None),
            }
            for col, (v, par) in cells.items():
                cell = filled["cells"][f"{rid}|{pf}_{col}"]
                cell["value"] = float(f"{v:.6g}") if isinstance(v, float) else v
                st = ""
                if par is not None and g != "0.00":
                    st = stars_from_p(pvals.get(par, {}).get(g))
                cell["stars"] = st
                cell["source"] = src

        # ---- sensitivity analyses (log only)
        log(f"== SENSITIVITY {assay}")
        sensitivity_per_experiment(x, groups, assay, log)
        log(f"  [sensitivity: all 8 deposited control columns pooled, global fit, {assay}]")
        g8 = select_control(raw, assay, "pooled")
        analyse_assay(x, {"0.00": g8["0.00"], **{g: g8[g] for g in GROUPS[1:]}}, assay, log)

    os.makedirs(OUT_DIR, exist_ok=True)
    with open(os.path.join(OUT_DIR, "filled.json"), "w", encoding="utf-8") as fh:
        json.dump(filled, fh, indent=1, ensure_ascii=False)
    log("wrote " + os.path.join(OUT_DIR, "filled.json"))


if __name__ == "__main__":
    main()
