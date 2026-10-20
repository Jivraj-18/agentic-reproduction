"""Reproduce Table 1 (CB1-OX1, CP55,940 cAMP inhibition and barrestin2 recruitment).
Usage: python -I out/repro_table.py data out
"""
import sys, os, json
import warnings
import numpy as np
import pandas as pd
from scipy.optimize import curve_fit
from scipy import stats

warnings.filterwarnings("ignore")

DATA, OUT = sys.argv[1], sys.argv[2]
os.makedirs(OUT, exist_ok=True)
TEMPLATE = os.path.join(os.path.dirname(os.path.abspath(DATA)), "template.json")
ROWS = {"0.00": "ox_000", "0.10": "ox_010", "0.25": "ox_025", "0.50": "ox_050"}
DOSES = ["0.00", "0.10", "0.25", "0.50"]


def load_block(path, block):
    """Read one titled block of the CSV export; return log10[M] x and {dose: (6 x n_exp) array}."""
    raw = pd.read_csv(path, header=None, encoding="utf-8")
    key = raw[0].astype(str).str.replace(" ", "")
    idx = raw.index[key == block.replace(" ", "")][0]
    hdr = raw.iloc[idx + 1]
    d = raw.iloc[idx + 2: idx + 8].astype(float)
    x = d[0].values
    starts = [i for i, v in enumerate(hdr) if isinstance(v, str) and "g OX" in v]
    groups = {}
    for s in starts:
        cols = [c for c in range(s, min(s + 8, raw.shape[1])) if not np.isnan(d[c]).all()]
        groups[hdr[s].split()[0]] = d[cols].values
    return x, groups


def f4(x, left, right, logec50, h):
    """Prism 'log(agonist) vs response, variable slope' algebra; left = response at low X."""
    return left + (right - left) / (1.0 + 10 ** ((logec50 - x) * h))


def fit_curve(x, Y, hill=None):
    """Single pooled least-squares fit to every per-experiment point (Prism replicate-Y default),
    multistart to reach the global least-squares minimum. Returns Prism-convention parameters
    (Bottom < Top; decreasing curve -> negative Hill) with asymptotic SEs."""
    xx = np.repeat(x, Y.shape[1])
    yy = Y.ravel()
    best = None
    for le0 in np.arange(-10, -4.4, 0.5):
        for h0 in ([0.5, 1.0, 2.0] if hill is None else [hill]):
            p0 = [yy[xx == xx.min()].mean(), yy[xx == xx.max()].mean(), le0, h0]
            try:
                if hill is None:
                    p, c = curve_fit(f4, xx, yy, p0=p0, maxfev=20000)
                else:
                    p, c = curve_fit(lambda X, a, b, l: f4(X, a, b, l, hill), xx, yy,
                                     p0=p0[:3], maxfev=20000)
                    p = np.r_[p, hill]
                    c = np.pad(c, (0, 1))
            except Exception:
                continue
            rss = float(((yy - f4(xx, *p)) ** 2).sum())
            if best is None or rss < best[0]:
                best = (rss, p, np.sqrt(np.abs(np.diag(c))))
    rss, p, se = best
    left, right, le, h = p
    if right < left:
        bottom, top, bse, tse, h = right, left, se[1], se[0], -h
    else:
        bottom, top, bse, tse = left, right, se[0], se[1]
    return dict(bottom=bottom, bottom_se=bse, top=top, top_se=tse, pec50=-le, pec50_se=se[2],
                hill=h, hill_se=(se[3] if hill is None else np.nan), rss=rss,
                n_exp=Y.shape[1], fixed_hill=hill is not None)


def tukey_from_summary(means, ses, ns):
    """One-way ANOVA + Tukey(-Kramer) from mean, SEM and n (SD = SEM*sqrt(n)); p of each group vs group 0."""
    means, ses, ns = (np.asarray(a, float) for a in (means, ses, ns))
    sds = ses * np.sqrt(ns)
    k, N = len(means), ns.sum()
    grand = (means * ns).sum() / N
    ssb = (ns * (means - grand) ** 2).sum()
    ssw = ((ns - 1) * sds ** 2).sum()
    dfb, dfw = k - 1, N - k
    mse = ssw / dfw
    F = (ssb / dfb) / mse
    pF = stats.f.sf(F, dfb, dfw)
    p = [np.nan]
    for i in range(1, k):
        q = abs(means[i] - means[0]) / np.sqrt(mse / 2 * (1 / ns[i] + 1 / ns[0]))
        p.append(float(stats.studentized_range.sf(q, k, dfw)))
    return F, pF, p


def star(p):
    if p is None or np.isnan(p):
        return ""
    return "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else ""


def test(name, means, ses, ns, ds):
    F, pF, p = tukey_from_summary(means, ses, ns)
    print(f"ANOVA {name}: groups {ds} F={F:.4f} p={pF:.4g}; Tukey p vs 0.00: "
          + ", ".join(f"{d}:{pp:.4g}" for d, pp in zip(ds[1:], p[1:])))
    return {d: (p[i] if i > 0 else np.nan) for i, d in enumerate(ds)}


def section_camp():
    x, g = load_block(os.path.join(DATA, "crc_cAMP_fold.csv"), "CB1R - OX1R")
    res = {}
    for dose, Y in g.items():
        r = fit_curve(x, Y)
        print(f"cAMP {dose} ug n={Y.shape[1]} 4P fit: pEC50={r['pec50']:.4f}+-{r['pec50_se']:.4g} "
              f"Bottom={r['bottom']:.4f}+-{r['bottom_se']:.4g} Top={r['top']:.4f} "
              f"Hill={r['hill']:.4f}+-{r['hill_se']:.4g}")
        if dose == "0.50":  # F2/S6: 4P fit not estimable -> Hill constrained (|h|=1)
            r = fit_curve(x, Y, hill=1.0)
            print(f"   0.50 refit, Hill constrained: pEC50={r['pec50']:.4f}+-{r['pec50_se']:.4g} "
                  f"Bottom={r['bottom']:.4f}+-{r['bottom_se']:.4g} Hill={r['hill']:.1f}")
        res[dose] = r
    return res


def section_arr():
    x, g = load_block(os.path.join(DATA, "crc_barr2_fold.csv"), "CB1R-OX1R")
    res = {}
    for dose, Y in g.items():
        r = fit_curve(x, Y)
        print(f"barr2 {dose} ug n={Y.shape[1]} 4P fit: pEC50={r['pec50']:.4f}+-{r['pec50_se']:.4g} "
              f"Top={r['top']:.4f}+-{r['top_se']:.4g} Hill={r['hill']:.4f}+-{r['hill_se']:.4g}")
        if dose == "0.00":  # F3/S5: no clear asymptote -> observed Emax, EC50 as a bound
            ytop = Y[-1, :]
            r["top_obs"] = float(ytop.mean())
            r["top_obs_se"] = float(ytop.std(ddof=1) / np.sqrt(len(ytop)))
            m = Y.mean(axis=1)
            half = (m.min() + m.max()) / 2
            i = np.where(m >= half)[0][0]
            xh = x[i - 1] + (half - m[i - 1]) * (x[i] - x[i - 1]) / (m[i] - m[i - 1])
            r["pec50_bound"] = float(-xh)
            print(f"   0.00 observed Emax (mean at 10 uM) = {r['top_obs']:.4f}+-{r['top_obs_se']:.4g}; "
                  f"half-observed-max crossing log[M]={xh:.4f} -> pEC50 < {-xh:.4f}")
        res[dose] = r
    return res


def main():
    tpl = json.load(open(TEMPLATE, encoding="utf-8"))
    cells = tpl["cells"]
    camp = section_camp()
    arr = section_arr()

    n = lambda R, ds: [R[d]["n_exp"] for d in ds]
    p_cp = test("cAMP pEC50", [camp[d]["pec50"] for d in DOSES], [camp[d]["pec50_se"] for d in DOSES], n(camp, DOSES), DOSES)
    p_ce = test("cAMP Emax", [camp[d]["bottom"] for d in DOSES], [camp[d]["bottom_se"] for d in DOSES], n(camp, DOSES), DOSES)
    dh = ["0.00", "0.10", "0.25"]
    p_ch = test("cAMP Hill", [camp[d]["hill"] for d in dh], [camp[d]["hill_se"] for d in dh], n(camp, dh), dh)
    em = [arr["0.00"]["top_obs"]] + [arr[d]["top"] for d in DOSES[1:]]
    es = [arr["0.00"]["top_obs_se"]] + [arr[d]["top_se"] for d in DOSES[1:]]
    p_ae = test("barr2 Emax", em, es, n(arr, DOSES), DOSES)
    p_ah = test("barr2 Hill", [arr[d]["hill"] for d in DOSES], [arr[d]["hill_se"] for d in DOSES], n(arr, DOSES), DOSES)

    def put(dose, col, value, stars, source):
        c = cells[f"{ROWS[dose]}|{col}"]
        c["value"] = float(value) if isinstance(value, (float, np.floating, int)) else value
        c["stars"] = stars
        c["source"] = source

    for d in DOSES:
        c = camp[d]
        src = "section_camp/fit_curve (pooled 4P)" if d != "0.50" else "section_camp/fit_curve (pooled, Hill constrained)"
        put(d, "camp_pec50", c["pec50"], star(p_cp[d]), src + " + tukey_from_summary")
        put(d, "camp_pec50_se", c["pec50_se"], "N/A", src + " asymptotic SE")
        put(d, "camp_ec50", 10 ** (-c["pec50"]) * 1e9, "N/A", src + " 10^-pEC50 (nM)")
        put(d, "camp_emax", c["bottom"], star(p_ce[d]), src + " Bottom plateau + tukey_from_summary")
        put(d, "camp_emax_se", c["bottom_se"], "N/A", src + " asymptotic SE")
        if d == "0.50":
            put(d, "camp_hill", c["hill"], "N/A", src + " (fixed; not tested)")
            put(d, "camp_hill_se", "N/A", "N/A", src + " (fixed parameter, no SE)")
        else:
            put(d, "camp_hill", c["hill"], star(p_ch[d]), src + " + tukey_from_summary")
            put(d, "camp_hill_se", c["hill_se"], "N/A", src + " asymptotic SE")
        a = arr[d]
        if d == "0.00":
            put(d, "arr_pec50", f"<{a['pec50_bound']:.4f}", "N/A", "section_arr: bound from half-observed-max interpolation")
            put(d, "arr_pec50_se", "N/A", "N/A", "section_arr: bound, no SE")
            put(d, "arr_ec50", f">{10 ** (-a['pec50_bound']) * 1e9:.4f}", "N/A", "section_arr: bound from half-observed-max interpolation")
            put(d, "arr_emax", a["top_obs"], "", "section_arr: observed mean at 10 uM (F3/S5), reference group")
            put(d, "arr_emax_se", a["top_obs_se"], "N/A", "section_arr: SEM across experiments at 10 uM")
        else:
            put(d, "arr_pec50", a["pec50"], "N/A", "section_arr/fit_curve (pooled 4P); untested, reference is a bound")
            put(d, "arr_pec50_se", a["pec50_se"], "N/A", "section_arr/fit_curve asymptotic SE")
            put(d, "arr_ec50", 10 ** (-a["pec50"]) * 1e9, "N/A", "section_arr/fit_curve 10^-pEC50 (nM)")
            put(d, "arr_emax", a["top"], star(p_ae[d]), "section_arr/fit_curve Top plateau + tukey_from_summary")
            put(d, "arr_emax_se", a["top_se"], "N/A", "section_arr/fit_curve asymptotic SE")
        put(d, "arr_hill", a["hill"], star(p_ah[d]), "section_arr/fit_curve (pooled 4P) + tukey_from_summary")
        put(d, "arr_hill_se", a["hill_se"], "N/A", "section_arr/fit_curve asymptotic SE")

    missing = [k for k, c in cells.items() if c["value"] is None]
    print("unfilled cells:", missing)
    with open(os.path.join(OUT, "filled.json"), "w", encoding="utf-8") as fh:
        json.dump(tpl, fh, indent=1, ensure_ascii=False)
    print("wrote", os.path.join(OUT, "filled.json"))


if __name__ == "__main__":
    main()
