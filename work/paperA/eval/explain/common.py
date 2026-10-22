"""Shared loader for the explain scripts (paper A, Table 1)."""
import os, numpy as np, pandas as pd
import statsmodels.formula.api as smf
from scipy import stats

HERE = os.path.dirname(os.path.abspath(__file__))
PAPER = os.path.abspath(os.path.join(HERE, "..", ".."))
XLSX = os.path.join(PAPER, "source", "data", "DATA_Knot-tying_FINAL.xlsx")
PAIRS = {"io": ("A", "B"), "ic": ("A", "C"), "oc": ("B", "C")}


def tosec(v):
    if isinstance(v, str):
        parts = [int(p) for p in v.split(":")]
        m, s = parts[-2], parts[-1]
        return m * 60 + s
    if hasattr(v, "hour"):
        return v.hour * 60 + v.minute
    return np.nan


def load():
    d = pd.read_excel(XLSX, sheet_name="Knot-Tying_Data")
    d = d.rename(columns={"knot-tying technique": "tech", "time total (s)": "t",
                          "delta knot strength (mm)": "ks", "knot spread ability (mm)": "sp",
                          "mistakes": "mi", "knot strength before 15 N(mm)": "kb",
                          "knot strength after 15 N (mm)": "ka"})
    d["t"] = d["t"].map(tosec).astype(float)
    d["run"] = d["run"].astype(int)
    d["mb"] = (d["mi"] >= 1).astype(float).where(d["mi"].notna())
    d["lt"] = np.log(d["t"])
    d["lks"] = np.log(d["ks"].where(d["ks"] > 0))
    return d


def lmm(d, var, interaction=False, reml=True, extra=""):
    """Random-intercept LMM; contrasts averaged equally over runs (emmeans style). Wald z."""
    import patsy, statsmodels.api as sm
    x = d.dropna(subset=[var]).copy()
    rhs = ("C(tech) * C(run)" if interaction else "C(tech) + C(run)") + extra
    Xd = patsy.dmatrix(rhs, x, return_type="dataframe")
    m = sm.MixedLM(x[var].values, Xd, groups=x["subject"].values).fit(reml=reml)
    names = list(Xd.columns)
    b = m.fe_params.values
    cov = m.cov_params().iloc[:len(names), :len(names)].values
    # reference grid: every tech x run cell, other factors averaged over their observed levels
    rows = []
    for t in "ABC":
        for r in (1, 2, 3):
            g = x.copy(); g["tech"] = t; g["run"] = r
            rows.append(np.asarray(patsy.build_design_matrices([Xd.design_info], g)[0]).mean(0))
    rows = np.array(rows)
    emm_rows = {t: rows[i * 3:(i + 1) * 3].mean(0) for i, t in enumerate("ABC")}
    res = {}
    for k, (a, c) in PAIRS.items():
        L = emm_rows[a] - emm_rows[c]
        est = L @ b; se = np.sqrt(L @ cov @ L)
        res[k] = dict(est=est, lo=est - 1.96 * se, hi=est + 1.96 * se, p=2 * stats.norm.sf(abs(est / se)))
    res["_emm"] = {t: emm_rows[t] @ b for t in "ABC"}
    res["_n"] = len(x)
    return res


def fmt(res, back=None):
    f = back or (lambda v: v)
    out = []
    for k in PAIRS:
        r = res[k]
        out.append(f"{k}: eff={f(r['est']):.3f} lo={f(r['lo']):.3f} hi={f(r['hi']):.3f} p={r['p']:.4f}")
    return " | ".join(out)


def glmm_logit(x, y, X, groups, nagq=15):
    """Random-intercept logistic GLMM by ML with adaptive Gauss-Hermite quadrature (nagq=1 is Laplace,
    the glmer default). Vectorised over subjects."""
    from scipy import optimize
    import statsmodels.tools.numdiff as nd
    X = np.asarray(X, float); y = np.asarray(y, float)
    g = pd.factorize(np.asarray(groups))[0]; G = g.max() + 1
    nodes, w = np.polynomial.hermite_e.hermegauss(nagq)
    lw = np.log(w)
    p = X.shape[1]
    gsum = lambda v: np.bincount(g, weights=v, minlength=G)

    def modes(b, s):
        eta = X @ b; u = np.zeros(G)
        for _ in range(100):
            pr = 1 / (1 + np.exp(-(eta + u[g])))
            gr = gsum(y - pr) - u / s ** 2
            h = gsum(pr * (1 - pr)) + 1 / s ** 2
            u = u + gr / h
            if np.abs(gr).max() < 1e-12: break
        pr = 1 / (1 + np.exp(-(eta + u[g])))
        return u, 1 / np.sqrt(gsum(pr * (1 - pr)) + 1 / s ** 2)

    def nll(par):
        b = par[:p]; s = np.exp(par[p])
        mu, sd = modes(b, s)
        U = mu[:, None] + sd[:, None] * nodes[None, :]          # G x K
        e = (X @ b)[:, None] + U[g]                               # n x K
        ll = y[:, None] * e - np.logaddexp(0, e)
        LL = np.vstack([np.bincount(g, weights=ll[:, k], minlength=G) for k in range(nagq)]).T
        lt = LL - 0.5 * (U / s) ** 2 - np.log(s) - 0.5 * np.log(2 * np.pi) + np.log(sd)[:, None] + 0.5 * nodes ** 2 + lw
        m = lt.max(1)
        return -(m + np.log(np.exp(lt - m[:, None]).sum(1))).sum()

    o = optimize.minimize(nll, np.zeros(p + 1), method="BFGS", options=dict(gtol=1e-7))
    o = optimize.minimize(nll, o.x, method="Nelder-Mead", options=dict(maxiter=4000, xatol=1e-9, fatol=1e-12))
    par = o.x
    cov = np.linalg.inv(nd.approx_hess(par, nll))
    return par, cov


def glmm_contrasts(d, ycol="mb", extra_cols=(), nagq=15):
    import patsy
    x = d.dropna(subset=[ycol]).copy()
    rhs = "C(tech) + C(run)" + "".join(f" + C({c})" for c in extra_cols)
    Xd = patsy.dmatrix(rhs, x, return_type="dataframe")
    par, cov = glmm_logit(x, x[ycol].values, Xd.values, x["subject"].values, nagq=nagq)
    names = list(Xd.columns)
    res = {}
    for k, (a, c) in PAIRS.items():
        L = np.zeros(len(par))
        for t, s in ((a, 1), (c, -1)):
            if t != "A": L[names.index(f"C(tech)[T.{t}]")] += s
        est = L @ par; se = np.sqrt(L @ cov @ L)
        res[k] = dict(est=est, lo=est - 1.96 * se, hi=est + 1.96 * se, p=2 * stats.norm.sf(abs(est / se)))
    res["_sd"] = float(np.exp(par[-1])); res["_n"] = len(x)
    return res


def add_position(d):
    """Position of the technique block in the participant's sequence (1st, 2nd or 3rd block), e.g. BAC -> B=1, A=2, C=3."""
    d = d.copy()
    d["pos"] = d.apply(lambda r: r["sequence"].index(r["tech"]) + 1, axis=1)
    return d


def published():
    import json
    t = json.load(open(os.path.join(PAPER, "extract", "tables_full.json"), encoding="utf-8"))
    return {k: c for k, c in t["cells"].items()}


def runs():
    import json
    g = json.load(open(os.path.join(PAPER, "eval", "grades.json"), encoding="utf-8"))
    return {k: {r: c["runs"][r]["reproduced_raw"] for r in ("r_opus", "r_sonnet")} for k, c in g["cells"].items()}, \
           {k: {r: c["runs"][r]["grade"] for r in ("r_opus", "r_sonnet")} for k, c in g["cells"].items()}


def grade(cell, val, pub):
    """Same bands as eval/grades.json: A <=2%, B <=20%, C <=40%, D <=60%, E otherwise; '<x' cells pass if below x."""
    c = pub[cell]
    if c.get("comparator") == "<":
        return ("A", 0.0) if val < c["value"] else ("E", 100.0)
    pv = c["value"]
    dev = abs(val - pv) / abs(pv) * 100 if pv != 0 else abs(val) * 100
    if np.sign(val) != np.sign(pv) and pv != 0:
        return "E", dev
    for L, cut in (("A", 2), ("B", 20), ("C", 40), ("D", 60)):
        if dev <= cut + 1e-9:
            return L, dev
    return "E", dev


def rnd(cell, val, pub):
    dec = pub[cell].get("decimals") or 3
    return round(val, dec)


def show(cells, vals, pub, label):
    for c in cells:
        v = vals[c]; gr, dev = grade(c, rnd(c, v, pub), pub)
        print(f"  {label:28s} {c:10s} published={pub[c]['raw']:>7s} alt={v:9.4f} grade={gr} dev={dev:5.1f}%")


def table(pos=True, ks_zero=0.1, sp_zero="keep", nagq=1, means="runmeans"):
    """Rebuild every Table 1 cell under one reading. Returns {cell: value}.
    pos: add the block position (1st/2nd/3rd technique) as a fixed factor to every mixed model.
    ks_zero: value that replaces the single zero delta knot strength before logging (None = drop that run).
    sp_zero: 'keep' or 'drop' the matching zero knot-spread value.
    means: 'runmeans' = average of the three per-run arithmetic means; 'pooled' = arithmetic mean over all valid runs."""
    d = add_position(load())
    if ks_zero is not None:
        d["lks"] = np.log(d["ks"].replace(0, ks_zero))
    if sp_zero == "drop":
        d.loc[d["sp"] == 0, "sp"] = np.nan
    extra = " + C(pos)" if pos else ""
    out = {}
    for pre, var, raw, back in (("time", "lt", "t", np.exp), ("ks", "lks", "ks", np.exp), ("sp", "sp", "sp", lambda v: v)):
        r = lmm(d, var, extra=extra)
        for k in PAIRS:
            for f in ("eff", "lo", "hi", "p"):
                key = "est" if f == "eff" else f
                out[f"{pre}_{k}|{f}"] = r[k][key] if f == "p" else back(r[k][key])
    r = glmm_contrasts(d, "mb", ("pos",) if pos else (), nagq=nagq)
    for k in PAIRS:
        for f in ("eff", "lo", "hi", "p"):
            key = "est" if f == "eff" else f
            out[f"mi_{k}|{f}"] = r[k][key] if f == "p" else np.exp(r[k][key])
    for pre, col in (("time", "t"), ("ks", "ks"), ("sp", "sp"), ("mi", "mi")):
        x = d.dropna(subset=[col])
        if means == "runmeans":
            m = x.groupby(["tech", "run"])[col].mean().groupby("tech").mean()
        else:
            m = x.groupby("tech")[col].mean()
        for k, (a, c) in PAIRS.items():
            out[f"{pre}_{k}|m1"] = m[a]; out[f"{pre}_{k}|m2"] = m[c]
    return out
