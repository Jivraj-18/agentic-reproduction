"""Reproduce Table 2 (rat aorta relaxation to ACh and DEA/NO after 24 h extract incubation).
Usage: python -I repro_table.py <data_dir> <out_dir>
"""
import sys, os, json, copy
import numpy as np
import pandas as pd
from scipy import stats
from scipy.optimize import curve_fit

data_dir, out_dir = sys.argv[1], sys.argv[2]
here = os.path.dirname(os.path.abspath(__file__))
template_path = os.path.join(os.path.dirname(os.path.abspath(data_dir)), "template.json")

ROWMAP = {
    ("CSE", "Control (DMEM)"): "cse_ctrl", ("CSE", "CSE 1:3 Verd."): "cse_3",
    ("CSE", "CSE 1:20 Verd."): "cse_20", ("CSE", "CSE  1:200 Verd."): "cse_200",
    ("EVE", "Control (DMEM)"): "eve_ctrl", ("EVE", "EVE unv."): "eve_undil",
    ("EVE", "EVE 1:2"): "eve_2", ("EVE", "EVE 1:20"): "eve_20",
    ("HTE", "Control (DMEM)"): "hte_ctrl", ("HTE", "HTE unv."): "hte_undil",
    ("HTE", "HTE 1:2"): "hte_2", ("HTE", "HTE 1:20"): "hte_20",
}
SERIES = {"CSE": ["cse_ctrl", "cse_3", "cse_20", "cse_200"],
          "EVE": ["eve_ctrl", "eve_undil", "eve_2", "eve_20"],
          "HTE": ["hte_ctrl", "hte_undil", "hte_2", "hte_20"]}
AGONISTS = {"acetylcholine": "ach", "DEA/NO": "dea"}


def hill(logc, emax, logec50, n):
    """Hill model, baseline fixed at 0 % relaxation, free Emax, EC50 and slope."""
    return emax / (1.0 + 10.0 ** ((logec50 - logc) * n))


def fit_curve(logc, rel):
    """Least-squares fit of one experiment's curve (section: fit_curve)."""
    p0 = [max(rel.max(), 1.0), logc[np.argmin(np.abs(rel - rel.max() / 2))], 1.0]
    popt, _ = curve_fit(hill, logc, rel, p0=p0,
                        bounds=([0.0, -11.0, 0.2], [200.0, -3.0, 5.0]), maxfev=20000)
    emax, logec, n = popt
    # Fallback: free-slope fit not identifiable (no plateau reached): EC50 beyond the
    # highest tested concentration, Emax > 100 %, or slope at a bound -> refit with nH = 1.
    if logec > logc.max() or emax > 100.0 or n <= 0.2 + 1e-6 or n >= 5.0 - 1e-6:
        p2, _ = curve_fit(lambda x, e, l: hill(x, e, l, 1.0), logc, rel, p0=p0[:2],
                          bounds=([0.0, -11.0], [200.0, -3.0]), maxfev=20000)
        print(f"   refit with nH=1 (free fit Emax={emax:.2f}, EC50={10**logec*1e9:.1f} nM, nH={n:.2f})")
        return np.array([p2[0], p2[1], 1.0])
    return popt


def geo_ci(ec50_M):
    """Geometric mean with t-based 95% CI on log10 EC50 (section: geo_ci). Returns nM."""
    l = np.log10(ec50_M)
    n = len(l)
    m, se = l.mean(), l.std(ddof=1) / np.sqrt(n)
    t = stats.t.ppf(0.975, n - 1)
    return [10 ** (x) * 1e9 for x in (m, m - t * se, m + t * se)]


def dunnett_p(groups):
    """One-way ANOVA + Dunnett vs control (first group) (section: dunnett_p)."""
    f, p_anova = stats.f_oneway(*groups)
    res = stats.dunnett(*groups[1:], control=groups[0])
    return p_anova, res.pvalue


def main():
    df = pd.read_csv(os.path.join(data_dir, "aorta_crc.csv"))
    df["rel"] = 100.0 - df["pct_of_precontraction"]  # M1
    df["row"] = [ROWMAP[(e, t)] for e, t in zip(df["extract"], df["treatment"])]

    fits = {}
    for (row, ag, exp), g in df.groupby(["row", "agonist", "experiment"]):
        g = g.sort_values("conc_M")
        logc = np.log10(g["conc_M"].values)
        emax, logec, n = fit_curve(logc, g["rel"].values)
        fits[(row, AGONISTS[ag], exp)] = (emax, 10 ** logec, n)
        print(f"fit {row:10s} {ag:13s} exp{exp}: Emax={emax:7.2f}  EC50={10**logec*1e9:9.2f} nM  nH={n:5.2f}  obs_max={g['rel'].max():6.2f}")

    with open(template_path, encoding="utf-8") as fh:
        tpl = json.load(fh)
    out = copy.deepcopy(tpl)
    cells = out["cells"]

    for ser, rows in SERIES.items():
        for ag in ("ach", "dea"):
            em = [np.array([fits[(r, ag, e)][0] for e in range(1, 6)]) for r in rows]
            le = [np.log10([fits[(r, ag, e)][1] for e in range(1, 6)]) for r in rows]
            pa_e, pd_e = dunnett_p(em)
            pa_c, pd_c = dunnett_p(le)
            print(f"{ser} {ag}: Emax ANOVA p={pa_e:.4g}, Dunnett p={np.round(pd_e,4)}; "
                  f"logEC50 ANOVA p={pa_c:.4g}, Dunnett p={np.round(pd_c,4)}")
            for i, r in enumerate(rows):
                gm, lo, hi = geo_ci(np.array([fits[(r, ag, e)][1] for e in range(1, 6)]))
                mean_e = float(em[i].mean()); sem_e = float(em[i].std(ddof=1) / np.sqrt(5))
                star_e = "" if i == 0 else ("*" if pd_e[i - 1] < 0.05 else "")
                star_c = "" if i == 0 else ("*" if pd_c[i - 1] < 0.05 else "")
                vals = {
                    "emax": (mean_e, star_e, "fit_curve + mean (S1,S2); stars: dunnett_p on per-experiment Emax"),
                    "sem": (sem_e, "", "fit_curve + SEM (S2)"),
                    "ec50": (gm, star_c, "fit_curve + geo_ci geometric mean (S3); stars: dunnett_p on log10 EC50"),
                    "lo": (lo, "", "geo_ci lower 95% limit (S3)"),
                    "hi": (hi, "", "geo_ci upper 95% limit (S3)"),
                }
                for col, (v, s, src) in vals.items():
                    c = cells[f"{r}|{ag}_{col}"]
                    c["value"] = round(float(v), 6)
                    c["stars"] = s
                    c["source"] = src

    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "filled.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, ensure_ascii=False)
    print("\nTable:")
    for r in [r for rows in SERIES.values() for r in rows]:
        print(r.ljust(10), "  ".join(f"{cells[f'{r}|{k}']['value']:.4g}{cells[f'{r}|{k}']['stars']}"
                                     for k in [c['id'] for c in out['columns']]))


if __name__ == "__main__":
    main()
