"""Reproduce Table 1 (CB1-OX1, CP55,940) from the deposited fold data.

Usage: python -I out/repro_table.py data out

Main analysis (GraphPad-Prism-like):
  * one 4-parameter logistic ("log(agonist) vs response - variable slope") fit per
    transfection group, pooling every independent-experiment value as a separate point;
  * value = best-fit parameter, "+-" = standard error of the fitted parameter;
  * if the 4PL fit fails (rule fit_ok) the group is refit with |Hill| fixed to 1 (S6);
  * stars: one-way ANOVA + Tukey computed from summary data (mean, SD = SE*sqrt(n),
    n = number of independent experiments), each OX1 group vs 0.00 ug.
Sensitivity analysis (printed only): per-experiment fits averaged (mean +- SEM) with
ANOVA/Tukey on the per-experiment parameters.
"""
import sys, os, json, csv, copy, warnings
import numpy as np
from scipy.optimize import curve_fit
from scipy import stats
from scipy.stats import studentized_range

warnings.filterwarnings("ignore")
DATA, OUT = sys.argv[1], sys.argv[2]
TEMPLATE = os.path.join(os.path.dirname(os.path.abspath(DATA)), "template.json")
GROUPS = ["0.00", "0.10", "0.25", "0.50"]
ROWS = {"0.00": "ox_000", "0.10": "ox_010", "0.25": "ox_025", "0.50": "ox_050"}
LOGX_RANGE = (-11.0, -4.0)   # tested range -10..-5 extended by one log unit
HILL_RANGE = (0.2, 5.0)


# ---------------------------------------------------------------- data I/O
def read_block(path, block_key):
    """Return ({group: array (n_conc, n_exp)}, x in log M) for the block titled block_key."""
    with open(path, encoding="utf-8-sig") as f:
        rows = list(csv.reader(f))
    start = None
    for i, r in enumerate(rows):
        if r and r[0].replace(" ", "") == block_key.replace(" ", ""):
            start = i
            break
    if start is None:
        raise ValueError(f"block {block_key} not found in {path}")
    header = rows[start + 1]
    gcols = {h.split()[0]: j for j, h in enumerate(header) if j > 0 and h.strip()}
    starts = sorted(gcols.values())
    xs, body = [], []
    for r in rows[start + 2:]:
        if not r or r[0].strip() == "":
            break
        xs.append(float(r[0]))
        body.append(r)
    out = {}
    for g, j in gcols.items():
        nxt = [s for s in starts if s > j]
        end = nxt[0] if nxt else len(header)
        cols = []
        for c in range(j, end):
            vals = [b[c] if c < len(b) else "" for b in body]
            if all(v.strip() == "" for v in vals):
                continue
            cols.append([float(v) if v.strip() != "" else np.nan for v in vals])
        out[g] = np.array(cols).T
    return out, np.array(xs)


# ---------------------------------------------------------------- model
def four_pl(x, bottom, top, logec50, hill):
    # GraphPad Prism "log(agonist) vs. response -- Variable slope"
    return bottom + (top - bottom) / (1.0 + 10.0 ** ((logec50 - x) * hill))


def fit_curve(x, y, increasing, hill_fixed=None):
    """Least-squares fit. Returns dict with lower plateau ('bottom'), upper plateau
    ('top'), logec50, hill (signed: negative for a falling curve) and their SEs."""
    m = np.isfinite(y)
    x, y = x[m], y[m]
    b0, t0 = np.min(y), np.max(y)          # Prism-like initial values
    h0 = 1.0 if increasing else -1.0
    l0 = float(np.median(x))
    try:
        if hill_fixed is None:
            f, p0 = four_pl, [b0, t0, l0, h0]
        else:
            h = hill_fixed if increasing else -hill_fixed
            f = lambda xx, b, t, l: four_pl(xx, b, t, l, h)
            p0 = [b0, t0, l0]
        p, cov = curve_fit(f, x, y, p0=p0, maxfev=20000)
        se = np.sqrt(np.diag(cov))
        if hill_fixed is not None:
            p, se = np.append(p, h), np.append(se, np.nan)
        if not (np.all(np.isfinite(p)) and np.all(np.isfinite(se[:3]))):
            return None
    except Exception:
        return None
    b, t, l, hh = [float(v) for v in p]
    sb, st_, sl, sh = [float(v) for v in se]
    if b > t:  # re-express so that 'bottom' is the lower plateau
        b, t, hh, sb, st_ = t, b, -hh, st_, sb
    return dict(bottom=b, top=t, logec50=l, hill=hh, se_bottom=sb, se_top=st_,
                se_logec50=sl, se_hill=sh, n_points=int(m.sum()))


def fit_ok(fr, increasing):
    """Operational 'could be accurately estimated' rule (S2/S6)."""
    if fr is None:
        return False
    if not (LOGX_RANGE[0] <= fr["logec50"] <= LOGX_RANGE[1]):
        return False
    if (increasing and fr["hill"] <= 0) or (not increasing and fr["hill"] >= 0):
        return False
    if not (HILL_RANGE[0] <= abs(fr["hill"]) <= HILL_RANGE[1]):
        return False
    if (not np.isfinite(fr["se_hill"]) or fr["se_hill"] > abs(fr["hill"])
            or fr["se_logec50"] > 1.0):
        return False
    return True


def emax_of(fr, increasing):
    return (fr["top"], fr["se_top"]) if increasing else (fr["bottom"], fr["se_bottom"])


# ---------------------------------------------------------------- main analysis: pooled fit
def pooled_group_fit(arr, x, increasing):
    xx = np.repeat(x, arr.shape[1])
    yy = arr.reshape(-1)
    fr = fit_curve(xx, yy, increasing)
    constrained = not fit_ok(fr, increasing)
    if constrained:
        fr = fit_curve(xx, yy, increasing, hill_fixed=1.0)
    potency = fr is not None and LOGX_RANGE[0] <= fr["logec50"] <= LOGX_RANGE[1]
    return fr, constrained, potency


def tukey_summary(means, ses, ns):
    """One-way ANOVA + Tukey-Kramer from summary data (mean, SE, n) - as Prism does when
    data are entered as mean/SEM/n. Returns ANOVA p and {group: p_adj vs first group}."""
    g = [k for k in means if np.isfinite(means[k]) and np.isfinite(ses[k])]
    if len(g) < 2 or GROUPS[0] not in g:
        return np.nan, {k: None for k in means}
    m = np.array([means[k] for k in g]); n = np.array([ns[k] for k in g], float)
    sd = np.array([ses[k] for k in g]) * np.sqrt(n)
    N, k = n.sum(), len(g)
    grand = (m * n).sum() / N
    ssb = (n * (m - grand) ** 2).sum(); ssw = ((n - 1) * sd ** 2).sum()
    dfb, dfw = k - 1, N - k
    msw = ssw / dfw
    F = (ssb / dfb) / msw
    p_anova = float(stats.f.sf(F, dfb, dfw))
    res = {kk: None for kk in means}
    for i in range(1, k):
        q = abs(m[i] - m[0]) / np.sqrt(msw / 2 * (1 / n[i] + 1 / n[0]))
        res[g[i]] = float(studentized_range.sf(q, k, dfw))
    return p_anova, res


def tukey_raw(values_by_group):
    """One-way ANOVA + Tukey-Kramer on raw per-experiment values (sensitivity)."""
    means = {}; ses = {}; ns = {}
    for k, v in values_by_group.items():
        v = np.array([a for a in v if np.isfinite(a)])
        means[k] = v.mean() if len(v) else np.nan
        ses[k] = v.std(ddof=1) / np.sqrt(len(v)) if len(v) > 1 else np.nan
        ns[k] = len(v)
    return tukey_summary(means, ses, ns)


def stars_for(p):
    if p is None or not np.isfinite(p):
        return ""
    return "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else ""


# ---------------------------------------------------------------- sensitivity: per-experiment
def per_experiment(arr, x, increasing):
    fits = [fit_curve(x, arr[:, k], increasing) for k in range(arr.shape[1])]
    cons = not all(fit_ok(f, increasing) for f in fits)
    if cons:
        fits = [fit_curve(x, arr[:, k], increasing, hill_fixed=1.0) for k in range(arr.shape[1])]
    out = []
    for k, f in enumerate(fits):
        if f is not None and LOGX_RANGE[0] <= f["logec50"] <= LOGX_RANGE[1]:
            out.append((-f["logec50"], emax_of(f, increasing)[0], f["hill"]))
        else:
            y = arr[:, k]
            out.append((np.nan, np.nanmax(y) if increasing else np.nanmin(y), np.nan))
    return np.array(out), cons


def main():
    os.makedirs(OUT, exist_ok=True)
    with open(TEMPLATE, encoding="utf-8") as f:
        tpl = json.load(f)
    filled = copy.deepcopy(tpl)
    assays = {
        "camp": (os.path.join(DATA, "crc_cAMP_fold.csv"), "CB1R - OX1R", False),
        "arr": (os.path.join(DATA, "crc_barr2_fold.csv"), "CB1R-OX1R", True),
    }
    for a, (path, key, increasing) in assays.items():
        blocks, x = read_block(path, key)
        print(f"\n=================== {a}: block '{key}', log[CP55,940] = {x.tolist()}")
        res = {}
        for g in GROUPS:
            arr = blocks[g]
            fr, cons, pot = pooled_group_fit(arr, x, increasing)
            res[g] = dict(fr=fr, cons=cons, pot=pot, n=arr.shape[1])
            print(f"[pooled_group_fit] {g} ug  n_exp={arr.shape[1]}  hill_constrained={cons}  potency={pot}")
            print("     " + ", ".join(f"{k}={v:.5g}" for k, v in fr.items()))

        # summary statistics for stars
        par_vals = {}
        for g in GROUPS:
            fr = res[g]["fr"]; em, ese = emax_of(fr, increasing)
            par_vals[g] = dict(pec50=(-fr["logec50"] if res[g]["pot"] else np.nan, fr["se_logec50"]),
                               emax=(em, ese),
                               hill=(fr["hill"] if not res[g]["cons"] else np.nan, fr["se_hill"]))
        pstars = {}
        for par in ["pec50", "emax", "hill"]:
            means = {g: par_vals[g][par][0] for g in GROUPS}
            ses = {g: par_vals[g][par][1] for g in GROUPS}
            ns = {g: res[g]["n"] for g in GROUPS}
            pa, pt = tukey_summary(means, ses, ns)
            pstars[par] = pt
            print(f"[tukey_summary] {par}: ANOVA p={pa:.4g}; Tukey p vs 0.00 ug: " +
                  ", ".join(f"{g}={pt[g]:.4g}" if pt[g] is not None else f"{g}=NA" for g in GROUPS[1:]))

        # fill cells
        for g in GROUPS:
            row = ROWS[g]; fr = res[g]["fr"]
            src = "pooled_group_fit (4PL on all experiment values, Prism-style) ; +- = fit SE"
            if res[g]["cons"]:
                src += " ; Hill constrained to 1 (rule S6)"

            def put(col, val, st="", source=src):
                cell = filled["cells"][f"{row}|{col}"]
                if isinstance(val, float) and not np.isfinite(val):
                    val = "N/A"
                cell["value"] = val
                cell["stars"] = st
                cell["source"] = source

            def stv(par):
                return stars_for(pstars[par].get(g)) if g != "0.00" else ""
            if res[g]["pot"]:
                put(f"{a}_pec50", -fr["logec50"], stv("pec50"))
                put(f"{a}_pec50_se", fr["se_logec50"])
                put(f"{a}_ec50", float(10 ** fr["logec50"] * 1e9), source=src + " ; EC50 = 10^logEC50 in nM")
            else:  # rule S5
                arr = blocks[g]
                put(f"{a}_pec50", "n.d.", source="rule S5")
                put(f"{a}_pec50_se", "N/A", source="rule S5")
                put(f"{a}_ec50", ">10000", source="rule S5: bound = top tested concentration")
            em, ese = emax_of(fr, increasing)
            put(f"{a}_emax", em, stv("emax"))
            put(f"{a}_emax_se", ese)
            if res[g]["cons"]:
                put(f"{a}_hill", 1.0, source="rule S6: Hill slope constrained to 1")
                put(f"{a}_hill_se", "N/A", source="rule S6: constrained, no SE")
            else:
                put(f"{a}_hill", fr["hill"], stv("hill"))
                put(f"{a}_hill_se", fr["se_hill"])

        # sensitivity analysis
        print(f"--- sensitivity: per-experiment fits, mean +- SEM ({a})")
        pe = {}
        for g in GROUPS:
            v, cons = per_experiment(blocks[g], x, increasing)
            pe[g] = v
            msg = []
            for j, name in enumerate(["pEC50", "Emax", "Hill"]):
                col = v[:, j][np.isfinite(v[:, j])]
                msg.append(f"{name}={col.mean():.4f}+-{col.std(ddof=1)/np.sqrt(len(col)):.4f}(n={len(col)})"
                           if len(col) > 1 else f"{name}=NA")
            print(f"   {g} ug hill_constrained={cons}: " + "  ".join(msg))
        for j, name in enumerate(["pEC50", "Emax", "Hill"]):
            pa, pt = tukey_raw({g: pe[g][:, j] for g in GROUPS})
            print(f"   ANOVA {name}: p={pa:.4g}; Tukey vs 0.00: " +
                  ", ".join(f"{g}={pt[g]:.4g}" if pt[g] is not None else f"{g}=NA" for g in GROUPS[1:]))

    with open(os.path.join(OUT, "filled.json"), "w", encoding="utf-8") as f:
        json.dump(filled, f, indent=1, ensure_ascii=False)
    print("\nFilled table (value, stars):")
    for g in GROUPS:
        row = ROWS[g]
        print(row)
        for c in tpl["columns"]:
            cell = filled["cells"][f"{row}|{c['id']}"]
            v = cell["value"]
            print(f"   {c['id']:<14} {v if isinstance(v, str) else f'{v:.5g}':>10} {cell['stars']}")
    print("\nwrote", os.path.join(OUT, "filled.json"))


if __name__ == "__main__":
    main()
