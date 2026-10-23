"""Reproduce Table 1 (CB1-OX1 cells): CP55,940 cAMP inhibition and barrestin2 recruitment.

Usage: python -I out/repro_table.py data out

Pipeline (see out/assumptions.md for every choice):
  1. parse the CB1R-OX1R block of each fold CSV (rows = log10 M CP55,940, columns = experiments)
  2. fit a 4-parameter log(agonist)-response curve separately to each independent experiment
     (fallback: Hill slope fixed to +/-1 when the 4PL fit is not acceptable)
  3. summarise each parameter as mean +/- SEM across experiments; EC50 (nM) = 10^(-mean pEC50) * 1e9
  4. one-way ANOVA + Tukey HSD across the 4 OX1 groups; stars for each group vs 0.00 ug
"""
import csv
import json
import os
import sys

import numpy as np
from scipy.optimize import curve_fit
from statsmodels.stats.multicomp import pairwise_tukeyhsd
from scipy.stats import f_oneway

DATA_DIR = sys.argv[1] if len(sys.argv) > 1 else "data"
OUT_DIR = sys.argv[2] if len(sys.argv) > 2 else "out"

GROUPS = ["0.00", "0.10", "0.25", "0.50"]
ROW_IDS = {"0.00": "ox_000", "0.10": "ox_010", "0.25": "ox_025", "0.50": "ox_050"}
# Which of the 8 mock (0.00 ug) columns belong to the OX1 experiment series (assumption A2)
MOCK_COLS = {"cAMP": [4, 5, 6, 7], "barr2": [0, 1, 2, 3]}
XMIN, XMAX = -10.0, -5.0


# ------------------------------------------------------------------ parsing
def parse_block(path, block_prefix):
    """Return {group: array (n_conc, n_cols)} and x array for the block whose title starts with block_prefix."""
    with open(path, encoding="utf-8-sig") as fh:
        rows = list(csv.reader(fh))
    start = None
    for i, r in enumerate(rows):
        if r and r[0].replace(" ", "").startswith(block_prefix):
            start = i
            break
    if start is None:
        raise ValueError(f"block {block_prefix} not found in {path}")
    header = rows[start + 1]
    # group label positions
    gpos = [(j, h) for j, h in enumerate(header) if j > 0 and h.strip()]
    x, mat = [], []
    for r in rows[start + 2:]:
        if not r or not r[0].strip():
            break
        x.append(float(r[0]))
        mat.append(r)
    out = {}
    for k, (j, h) in enumerate(gpos):
        jend = gpos[k + 1][0] if k + 1 < len(gpos) else len(header)
        g = h.split()[0]
        cols = []
        for c in range(j, jend):
            vals = [m[c] if c < len(m) else "" for m in mat]
            if all(v.strip() == "" for v in vals):
                continue
            cols.append([float(v) if v.strip() else np.nan for v in vals])
        out[g] = np.array(cols).T  # (n_conc, n_exp)
    return np.array(x), out


# ------------------------------------------------------------------ curve model
def four_pl(x, bottom, top, logec50, hill):
    return bottom + (top - bottom) / (1.0 + 10.0 ** ((logec50 - x) * hill))


def fit_curve(x, y, direction):
    """Fit one experiment. direction=+1 (stimulation) or -1 (inhibition).

    Returns dict with bottom, top, logec50, hill, emax, model ('4PL' or 'Hill=1' or 'n.d.')."""
    ok = ~np.isnan(y)
    x, y = x[ok], y[ok]
    lo, hi = float(np.min(y)), float(np.max(y))
    if direction > 0:
        p0 = [lo, hi, -7.0, 1.0]
    else:
        p0 = [lo, hi, -8.0, -1.0]  # bottom=min (inhibited plateau), top=max
    res = None
    try:
        popt, pcov = curve_fit(four_pl, x, y, p0=p0, maxfev=20000)
        perr = np.sqrt(np.diag(pcov))
        b, t, le, h = popt
        acceptable = (
            np.all(np.isfinite(perr))
            and XMIN - 1 <= le <= XMAX + 1          # potency within +/-1 log of tested range
            and 0.3 <= abs(h) <= 5.0                 # physiologically plausible slope
            and np.sign(h) == direction              # curve goes the expected way
            and perr[2] < 1.0                        # logEC50 determined to < 1 log unit
        )
        if acceptable:
            res = dict(bottom=b, top=t, logec50=le, hill=h, model="4PL")
    except Exception:
        pass
    if res is None:
        hfix = float(direction)
        f3 = lambda xx, b, t, le: four_pl(xx, b, t, le, hfix)
        try:
            popt, pcov = curve_fit(f3, x, y, p0=p0[:3], maxfev=20000)
            b, t, le = popt
            if XMIN - 1 <= le <= XMAX + 1 and np.all(np.isfinite(np.diag(pcov))):
                res = dict(bottom=b, top=t, logec50=le, hill=hfix, model="Hill=1")
        except Exception:
            pass
    if res is None:
        # S5: potency not estimable -> Emax = greatest observed response
        emax = lo if direction < 0 else hi
        return dict(bottom=np.nan, top=np.nan, logec50=np.nan, hill=np.nan, emax=emax, model="n.d.")
    # Emax = plateau reached at high agonist concentration (fold)
    res["emax"] = res["bottom"] if direction < 0 else res["top"]
    return res


# ------------------------------------------------------------------ statistics
def mean_sem(v):
    v = np.asarray([a for a in v if np.isfinite(a)], float)
    if len(v) == 0:
        return np.nan, np.nan, 0
    sem = np.std(v, ddof=1) / np.sqrt(len(v)) if len(v) > 1 else np.nan
    return float(np.mean(v)), float(sem), len(v)


def stars_vs_control(per_group, control="0.00"):
    """One-way ANOVA + Tukey HSD over all groups; stars for each group vs control."""
    vals, labels = [], []
    for g, v in per_group.items():
        v = [a for a in v if np.isfinite(a)]
        vals.extend(v)
        labels.extend([g] * len(v))
    groups = [np.array([a for a in per_group[g] if np.isfinite(a)]) for g in per_group]
    stars = {g: "" for g in per_group}
    pvals = {g: None for g in per_group}
    if any(len(gv) < 2 for gv in groups) or np.allclose(np.var(vals), 0):
        return stars, pvals, np.nan
    F, p_anova = f_oneway(*groups)
    tk = pairwise_tukeyhsd(np.array(vals), np.array(labels), alpha=0.05)
    tab = tk.summary().data[1:]
    for g1, g2, md, padj, lo, hi, rej in tab:
        other = g2 if g1 == control else (g1 if g2 == control else None)
        if other is None:
            continue
        pvals[other] = float(padj)
        if padj < 0.001:
            stars[other] = "***"
        elif padj < 0.01:
            stars[other] = "**"
        elif padj < 0.05:
            stars[other] = "*"
    return stars, pvals, float(p_anova)


# ------------------------------------------------------------------ main
def analyse(assay, path, direction, prefix):
    x, blocks = parse_block(path, prefix)
    print(f"\n=== {assay}: block {prefix}, x = {x.tolist()}")
    per = {}
    for g in GROUPS:
        m = blocks[g]
        if g == "0.00":
            print(f"  mock block has {m.shape[1]} columns; using columns {MOCK_COLS[assay]}")
            m = m[:, MOCK_COLS[assay]]
        fits = []
        for j in range(m.shape[1]):
            f = fit_curve(x, m[:, j], direction)
            fits.append(f)
            print(f"  {g} ug exp{j+1}: model={f['model']:7s} pEC50={-f['logec50']:.3f} "
                  f"Emax={f['emax']:.4f} Hill={f['hill']:.3f} bottom={f['bottom']:.4f} top={f['top']:.4f}")
        per[g] = fits
    summary = {}
    for par in ["pec50", "emax", "hill"]:
        pg = {}
        for g in GROUPS:
            if par == "pec50":
                pg[g] = [-f["logec50"] for f in per[g]]
            else:
                pg[g] = [f[par] for f in per[g]]
        st, pv, pa = stars_vs_control(pg)
        print(f"  {par}: ANOVA p={pa:.4g}; Tukey p vs 0.00: {pv}")
        for g in GROUPS:
            mu, se, n = mean_sem(pg[g])
            summary[(g, par)] = (mu, se, n, st[g])
    for g in GROUPS:
        print("  %s ug: pEC50 %.4f +/- %.4f (EC50 %.3f nM) | Emax %.4f +/- %.4f | Hill %.4f +/- %.4f | n=%d" % (
            g, summary[(g, 'pec50')][0], summary[(g, 'pec50')][1], 10 ** (-summary[(g, 'pec50')][0]) * 1e9,
            summary[(g, 'emax')][0], summary[(g, 'emax')][1], summary[(g, 'hill')][0], summary[(g, 'hill')][1],
            summary[(g, 'pec50')][2]))
    return summary, per


def pooled_sensitivity(assay, path, direction, prefix):
    """Sensitivity check only (not written to the table): one 4PL fit to all experiments pooled."""
    x, blocks = parse_block(path, prefix)
    for g in GROUPS:
        m = blocks[g]
        if g == "0.00":
            m = m[:, MOCK_COLS[assay]]
        xx = np.repeat(x, m.shape[1])
        yy = m.reshape(-1)
        try:
            p0 = [yy.min(), yy.max(), -7.5, float(direction)]
            popt, pcov = curve_fit(four_pl, xx, yy, p0=p0, maxfev=20000)
            se = np.sqrt(np.diag(pcov))
            emax = popt[0] if direction < 0 else popt[1]
            print(f"  [pooled] {assay} {g}: pEC50={-popt[2]:.3f}+/-{se[2]:.3f} Emax={emax:.4f} Hill={popt[3]:.3f}+/-{se[3]:.3f}")
        except Exception as e:
            print(f"  [pooled] {assay} {g}: fit failed ({e})")


def fmt(v):
    return None if v is None or (isinstance(v, float) and not np.isfinite(v)) else float(v)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    tpl_path = os.path.join(os.path.dirname(os.path.abspath(DATA_DIR)), "template.json")
    with open(tpl_path, encoding="utf-8") as fh:
        tpl = json.load(fh)

    camp, _ = analyse("cAMP", os.path.join(DATA_DIR, "crc_cAMP_fold.csv"), -1, "CB1R-OX1R")
    arr, _ = analyse("barr2", os.path.join(DATA_DIR, "crc_barr2_fold.csv"), +1, "CB1R-OX1R")
    print("\n--- sensitivity: pooled fits ---")
    pooled_sensitivity("cAMP", os.path.join(DATA_DIR, "crc_cAMP_fold.csv"), -1, "CB1R-OX1R")
    pooled_sensitivity("barr2", os.path.join(DATA_DIR, "crc_barr2_fold.csv"), +1, "CB1R-OX1R")
    print("\n--- sensitivity: alternative mock-column assignment (not written to table) ---")
    MOCK_COLS["cAMP"], MOCK_COLS["barr2"] = [0, 1, 2, 3], [4, 5, 6, 7]
    analyse("cAMP", os.path.join(DATA_DIR, "crc_cAMP_fold.csv"), -1, "CB1R-OX1R")
    analyse("barr2", os.path.join(DATA_DIR, "crc_barr2_fold.csv"), +1, "CB1R-OX1R")

    for pre, summ in (("camp", camp), ("arr", arr)):
        for g in GROUPS:
            rid = ROW_IDS[g]
            src_fit = "analyse()->fit_curve() per experiment, mean_sem() across experiments"
            src_st = "stars_vs_control(): one-way ANOVA + Tukey HSD vs 0.00 ug"
            mu, se, n, st = summ[(g, "pec50")]
            c = tpl["cells"]
            c[f"{rid}|{pre}_pec50"].update(value=fmt(mu), stars=st, source=src_fit + "; " + src_st, n=n)
            c[f"{rid}|{pre}_pec50_se"].update(value=fmt(se), stars="", source="mean_sem(): SEM across experiments")
            c[f"{rid}|{pre}_ec50"].update(value=fmt(10 ** (-mu) * 1e9) if np.isfinite(mu) else "n.d.", stars="",
                                          source="10**(-mean pEC50)*1e9 in main()")
            mu, se, n, st = summ[(g, "emax")]
            c[f"{rid}|{pre}_emax"].update(value=fmt(mu), stars=st, source=src_fit + "; " + src_st, n=n)
            c[f"{rid}|{pre}_emax_se"].update(value=fmt(se), stars="", source="mean_sem(): SEM across experiments")
            mu, se, n, st = summ[(g, "hill")]
            c[f"{rid}|{pre}_hill"].update(value=fmt(mu), stars=st, source=src_fit + "; " + src_st, n=n)
            c[f"{rid}|{pre}_hill_se"].update(value=fmt(se), stars="", source="mean_sem(): SEM across experiments")
    with open(os.path.join(OUT_DIR, "filled.json"), "w", encoding="utf-8") as fh:
        json.dump(tpl, fh, indent=1, ensure_ascii=False)
    print("\nwrote", os.path.join(OUT_DIR, "filled.json"))


if __name__ == "__main__":
    main()
