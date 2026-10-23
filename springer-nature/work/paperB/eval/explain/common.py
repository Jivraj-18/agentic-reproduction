"""Shared helpers: parse the deposited workbook (raw curves + the authors' own fitted rows),
fit Hill models, and summarise a group of 5 experiments the way Table 2 does."""
import json, os
import numpy as np, openpyxl
from scipy import stats
from scipy.optimize import least_squares

PAPER = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
XLSX = os.path.join(PAPER, "source", "data", "Data Fig 1+Tab 2.xlsx")
CONC = np.array([1e-9, 3e-9, 1e-8, 3e-8, 1e-7, 3e-7, 1e-6, 3e-6, 1e-5])

ROWMAP = {  # table row -> (sheet, block index within sheet)
    "cse_ctrl": ("CSE", 0), "cse_3": ("CSE", 1), "cse_20": ("CSE", 2), "cse_200": ("CSE", 3),
    "eve_ctrl": ("EVE", 0), "eve_undil": ("EVE", 1), "eve_2": ("EVE", 2), "eve_20": ("EVE", 3),
    "hte_ctrl": ("HTE", 0), "hte_undil": ("HTE", 1), "hte_2": ("HTE", 2), "hte_20": ("HTE", 3),
}


def parse():
    """Return {(row, ag): dict(tension=5x9 array, ec50=5 (M), emax_t=5 (% tension remaining), label)}."""
    wb = openpyxl.load_workbook(XLSX, data_only=True)
    out = {}
    for sheet in ("CSE", "EVE", "HTE"):
        ws = wb[sheet]
        rows = [list(r) for r in ws.iter_rows(values_only=True)]
        for ag, c0 in (("ach", 0), ("dea", 13)):
            starts = [i for i, r in enumerate(rows) if isinstance(r[c0], str) and "DWK rat Aorta" in r[c0]]
            for b, s in enumerate(starts):
                label = rows[s + 1][c0]
                ten = np.array([[float(rows[s + 4 + k][c0 + 1 + e]) for e in range(5)] for k in range(9)]).T
                ecr = [r for r in rows[s:s + 20] if isinstance(r[c0], str) and r[c0].startswith("EC50")][0]
                emr = [r for r in rows[s:s + 20] if isinstance(r[c0], str) and r[c0].startswith("Emax")][0]
                rid = [k for k, v in ROWMAP.items() if v == (sheet, b)][0]
                out[(rid, ag)] = dict(tension=ten, ec50=np.array([float(x) for x in ecr[c0 + 1:c0 + 6]]),
                                      emax_t=np.array([float(x) for x in emr[c0 + 1:c0 + 6]]), label=label)
    return out


def published():
    t = json.load(open(os.path.join(PAPER, "extract", "tables_full.json"), encoding="utf-8"))
    return {k: (v["value"], v["decimals"]) for k, v in t["cells"].items()}


def runs():
    r = {}
    for run in ("r_opus", "r_sonnet"):
        f = json.load(open(os.path.join(PAPER, "sandbox", run, "out", "filled.json"), encoding="utf-8"))
        r[run] = {k: v["value"] for k, v in f["cells"].items()}
    return r


def summarise(emax_rel, ec50_M):
    """Emax mean, SEM; geometric mean EC50 (nM) with t-based 95% limits (as the authors' sheet does)."""
    emax_rel = np.asarray(emax_rel, float); lg = np.log10(np.asarray(ec50_M, float))
    n = len(lg); t = stats.t.ppf(0.975, n - 1)
    m, se = lg.mean(), lg.std(ddof=1) / np.sqrt(n)
    return dict(emax=emax_rel.mean(), sem=emax_rel.std(ddof=1) / np.sqrt(n),
                ec50=10 ** (m + 9), lo=10 ** (m - t * se + 9), hi=10 ** (m + t * se + 9))


def hill(logc, y, model="3p", nh_fixed=None, emax_max=np.inf):
    """Fit relaxation y (%) vs log10 conc. 3p: baseline 0, Emax, logEC50, nH free.
    4p: free bottom too. nh_fixed: fix slope. Returns (Emax, EC50_M, nH)."""
    best = None
    for lec0 in np.arange(-9, -4.4, 0.5):
        for h0 in ((nh_fixed,) if nh_fixed else (0.7, 1.0, 1.5)):
            def res(p):
                if model == "4p":
                    b, emax, lec, h = p
                else:
                    b = 0; emax, lec = p[0], p[1]; h = nh_fixed if nh_fixed else p[2]
                return b + (emax - b) / (1 + 10 ** (h * (lec - logc))) - y
            p0 = [min(max(y.max(), 5), 100), lec0] + ([] if nh_fixed else [h0])
            lb = [0, -11] + ([] if nh_fixed else [0.2]); ub = [emax_max, -2] + ([] if nh_fixed else [5])
            if model == "4p":
                p0 = [0] + p0; lb = [-20] + lb; ub = [20] + ub
            try:
                r = least_squares(res, p0, bounds=(lb, ub))
            except Exception:
                continue
            if best is None or r.cost < best.cost:
                best = r
    p = best.x
    if model == "4p":
        p = p[1:]
    return p[0], 10 ** p[1], (nh_fixed if nh_fixed else p[2])


def r2(x):  # 2 significant figures, as the authors' sheet holds EC50s
    return float(f"{x:.2g}")


def grade(pub, val, dec=None):
    if dec is not None:
        val = round(val, dec)
    d = abs(val - pub) / abs(pub) * 100 if pub else 0
    return "A" if d <= 2 else "B" if d <= 20 else "C" if d <= 40 else "D" if d <= 60 else "E"
