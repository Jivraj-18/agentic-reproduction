import sys, os, json, csv, warnings
import numpy as np
from scipy.optimize import least_squares
from scipy import stats
import statsmodels.api as sm
from statsmodels.stats.multicomp import pairwise_tukeyhsd
warnings.filterwarnings("ignore")
data_dir, out_dir = sys.argv[1], sys.argv[2]
ROWS = {"ox_000": 0, "ox_010": 1, "ox_025": 2, "ox_050": 3}

def load(fn, section="OX1R"):
    """returns {group_index: (logx array (6,), matrix (6, n_exp))} for CB1 x OX1 block"""
    rows = list(csv.reader(open(os.path.join(data_dir, fn), encoding="utf-8-sig")))
    # locate the CB1 block with OX1
    start = [i for i, r in enumerate(rows) if r and r[0].replace(" ", "") == "CB1R-OX1R"][0]
    blk = rows[start + 2:start + 8]
    x = np.array([float(r[0]) for r in blk])
    out = {}
    for g in range(4):
        cols = range(1 + 8 * g, 9 + 8 * g)
        cols = [c for c in cols if blk[0][c].strip() != ""]
        out[g] = (x, np.array([[float(r[c]) for c in cols] for r in blk]))
    return x, out

def model(p, x, h=None):
    bottom, top, lec = p[0], p[1], p[2]
    hh = p[3] if h is None else h
    # Prism convention: slope negative for downward curves
    return bottom + (top - bottom) / (1 + 10 ** ((lec - x) * hh))

def fit(x, y, direction, hfix=None):
    """y: 1d values at x (replicates stacked). returns params, se"""
    s = 1 if direction == "up" else -1
    best = None
    for lec0 in (-8, -7, -6, -5):
        for top0 in (np.max(y), 2 * np.max(y)) if direction == "up" else (np.max(y),):
            p0 = [np.min(y), top0, lec0] + ([s] if hfix is None else [])
            if direction == "down":
                p0[0], p0[1] = np.min(y) * 0.8, 1.0
            lo = [0, 0, -12] + ([-6] if hfix is None else [])
            hi = [1e3, 1e4, -3] + ([6] if hfix is None else [])
            f = lambda p: model(p, x, hfix) - y
            try:
                r = least_squares(f, p0, bounds=(lo, hi), x_scale="jac")
            except Exception:
                continue
            if best is None or r.cost < best.cost:
                best = r
    r = best
    n, k = len(y), len(r.x)
    J = r.jac
    s2 = 2 * r.cost / max(n - k, 1)
    try:
        cov = np.linalg.inv(J.T @ J) * s2
        se = np.sqrt(np.diag(cov))
    except Exception:
        se = np.full(k, np.nan)
    return r.x, se, r.cost

def run_fit(x, M, direction, hfix=None):
    xs = np.repeat(x, M.shape[1]); ys = M.ravel()
    return fit(xs, ys, direction, hfix)

def per_exp(x, M, direction, hfix=None):
    res = []
    for j in range(M.shape[1]):
        p, se, c = fit(x, M[:, j], direction, hfix)
        res.append(p)
    return np.array(res)

def stars(p):
    return "***" if p < 0.001 else "**" if p < 0.01 else ""

def analyse(fn, direction, constrain_rows, bound_rows, log):
    x, G = load(fn)
    res = {}
    pe = {}
    for rid, g in ROWS.items():
        M = G[g][1]
        hfix = (-1.0 if direction == "down" else 1.0) if rid in constrain_rows else None
        p, se, c = run_fit(x, M, direction, hfix)
        n = M.shape[1]
        d = {"n_exp": n}
        if rid in bound_rows:
            # no asymptote: Emax = mean of response at highest conc (per experiment mean +- SEM)
            top = M[-1, :]
            d.update(emax=top.mean(), emax_se=top.std(ddof=1) / np.sqrt(n))
            d.update(pec50=p[2] * -1, pec50_se=se[2], hill=p[3] if hfix is None else hfix,
                     hill_se=se[3] if hfix is None else np.nan, bound=True)
            d["fit_params"] = p.tolist()
        else:
            if direction == "up":
                emax, emax_se = p[1], se[1]
            else:
                emax, emax_se = p[0], se[0]
            d.update(emax=emax, emax_se=emax_se, pec50=-p[2], pec50_se=se[2],
                     hill=p[3] if hfix is None else hfix, hill_se=se[3] if hfix is None else np.nan)
            d["fit_params"] = p.tolist()
        # per-experiment fits for ANOVA
        pp = per_exp(x, M, direction, hfix)
        pe[rid] = pp
        d["pe_pec50"] = (-pp[:, 2]).tolist()
        d["pe_emax"] = (pp[:, 1] if direction == "up" else pp[:, 0]).tolist()
        if rid in bound_rows:
            d["pe_emax"] = M[-1, :].tolist()
        res[rid] = d
        log(f"{fn} {rid} {direction} n={n} fit={np.round(p,4).tolist()} se={np.round(se,4).tolist()} cost={c:.4f}")
    return res

def anova_stars(res, key):
    # one-way ANOVA + Tukey on per-experiment parameter, groups vs 0.00
    vals, labs = [], []
    for rid in ROWS:
        v = np.array(res[rid][key], float)
        vals += list(v); labs += [rid] * len(v)
    vals = np.array(vals); labs = np.array(labs)
    ok = np.isfinite(vals)
    F, pa = stats.f_oneway(*[vals[(labs == r) & ok] for r in ROWS])
    t = pairwise_tukeyhsd(vals[ok], labs[ok])
    out = {}
    for i, (a, b) in enumerate(zip(*t._multicomp.pairindices)):
        ga, gb = t.groupsunique[a], t.groupsunique[b]
        if "ox_000" in (ga, gb):
            other = gb if ga == "ox_000" else ga
            out[other] = float(t.pvalues[i])
    return out, pa

def main():
    logs = []
    def log(s):
        print(s); logs.append(s)
    camp = analyse("crc_cAMP_fold.csv", "down", {"ox_050"}, set(), log)
    arr = analyse("crc_barr2_fold.csv", "up", set(), {"ox_000"}, log)
    tmpl = json.load(open(os.path.join(os.path.dirname(os.path.abspath(data_dir)), "template.json"), encoding="utf-8"))
    cells = tmpl["cells"]
    star_map = {}
    for tag, res in (("camp", camp), ("arr", arr)):
        for key, col in (("pe_pec50", "pec50"), ("pe_emax", "emax")):
            pv, pa = anova_stars(res, key)
            log(f"ANOVA {tag} {key}: p={pa:.4g} Tukey vs 0.00: {pv}")
            for rid, p in pv.items():
                star_map[(rid, f"{tag}_{col}")] = stars(p)
    for key, c in cells.items():
        rid, col = key.split("|")
        tag, what = col.split("_", 1)
        res = (camp if tag == "camp" else arr)[rid]
        src = f"analyse('{'crc_cAMP_fold.csv' if tag=='camp' else 'crc_barr2_fold.csv'}') pooled 4PL fit"
        v = None
        if what == "pec50": v = res["pec50"]
        elif what == "pec50_se": v = res["pec50_se"]
        elif what == "ec50":
            v = 10 ** (-res["pec50"]) * 1e9
            if res.get("bound"):
                v = ">10000"
        elif what == "emax": v = res["emax"]
        elif what == "emax_se": v = res["emax_se"]
        elif what == "hill": v = res["hill"]
        elif what == "hill_se": v = res["hill_se"]
        if isinstance(v, float) and not np.isfinite(v):
            v = "N/A"
        if res.get("bound") and what == "pec50": v = "<5"
        if res.get("bound") and what in ("pec50_se", "hill", "hill_se"): v = "N/A"
        c["value"] = v if isinstance(v, str) else float(v)
        c["stars"] = star_map.get((rid, col), "")
        c["source"] = src + (" (Hill constrained to -1)" if rid == "ox_050" and tag == "camp" else "") + \
            (" (Emax = mean observed at top conc; EC50 bound)" if res.get("bound") and what in ("emax","emax_se","ec50","pec50") else "")
        if what == "pec50_se" and False: pass
    json.dump(tmpl, open(os.path.join(out_dir, "filled.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
main()
