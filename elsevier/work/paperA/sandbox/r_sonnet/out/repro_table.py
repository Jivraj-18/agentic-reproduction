import sys, json, os, warnings
import numpy as np, pandas as pd
import statsmodels.formula.api as smf
from scipy import stats, optimize
warnings.filterwarnings("ignore")
data_dir, out_dir = sys.argv[1], sys.argv[2]
d = pd.read_excel(os.path.join(data_dir, "DATA_Knot-tying_FINAL.xlsx"), sheet_name="Knot-Tying_Data")
d = d.rename(columns={"knot-tying technique": "tech", "time total (s)": "t", "delta knot strength (mm)": "ks",
                      "knot spread ability (mm)": "sp", "mistakes": "mi"})
def tosec(v):
    if isinstance(v, str):
        m, s = v.split(":")[-2:]; return int(m) * 60 + int(s)
    if hasattr(v, "hour"): return v.hour * 60 + v.minute
    return np.nan
d["t"] = d["t"].map(tosec)
d["mb"] = (d["mi"] >= 1).astype(float).where(d["mi"].notna())
d["lt"] = np.log(d["t"]); d["lks"] = np.log(d["ks"].where(d["ks"] > 0))  # zero delta -> excluded
d["run"] = d["run"].astype(int)
print("rows", len(d), "valid time", d.t.notna().sum(), "ks", d.lks.notna().sum(), "sp", d.sp.notna().sum(), "mi", d.mb.notna().sum())

pairs = {"io": ("A", "B"), "ic": ("A", "C"), "oc": ("B", "C")}

def lmm_contrasts(var):
    x = d.dropna(subset=[var]).copy()
    m = smf.mixedlm(f"{var} ~ C(tech, Treatment('A')) + C(run)", x, groups=x["subject"]).fit(reml=True)
    names = list(m.fe_params.index); cov = m.cov_params().loc[names, names].values; b = m.fe_params.values
    res = {}
    for k, (a, c) in pairs.items():
        L = np.zeros(len(names))
        for t_, sgn in ((a, 1), (c, -1)):
            if t_ != "A": L[names.index(f"C(tech, Treatment('A'))[T.{t_}]")] += sgn
        est = L @ b; se = np.sqrt(L @ cov @ L); z = est / se
        res[k] = (est, est - 1.96 * se, est + 1.96 * se, 2 * stats.norm.sf(abs(z)))
    return res

# random-intercept logistic GLMM, adaptive Gauss-Hermite quadrature, ML
def glmm_logit(x):
    x = x.dropna(subset=["mb"])
    X = np.column_stack([np.ones(len(x)), (x.tech == "B"), (x.tech == "C"), (x.run == 2), (x.run == 3)]).astype(float)
    y = x.mb.values; g = pd.factorize(x.subject)[0]; G = g.max() + 1
    nodes, w = np.polynomial.hermite_e.hermegauss(15); w = w / np.sqrt(2 * np.pi)
    def gl(b, u, idx):  # log-lik at nodes u (K,) for group idx
        eta = X[idx] @ b
        e = eta[:, None] + u[None, :]
        return (y[idx][:, None] * e - np.logaddexp(0, e)).sum(0)
    idxs = [np.where(g == i)[0] for i in range(G)]
    state = {"mu": np.zeros(G), "sd": np.ones(G)}
    def nll(par, adapt=True):
        b = par[:5]; s = np.exp(par[5]); tot = 0
        for i, idx in enumerate(idxs):
            if adapt:
                mu, sd = state["mu"][i], state["sd"][i]
            else: mu, sd = 0., 1.
            u = mu + sd * nodes
            lf = gl(b, u, idx) - 0.5 * (u / s) ** 2 - np.log(s) - 0.5 * np.log(2 * np.pi)
            # integrand f(u); integral = sum w_k * sqrt(2pi)*sd * f(u_k) * exp(z^2/2) * phi(z)... 
            tot += np.log(np.sum(w * np.sqrt(2 * np.pi) * sd * np.exp(lf + 0.5 * nodes ** 2 - 0.5 * np.log(2 * np.pi) * 0) ) ) - 0.0
        return -tot
    # exact formula: int f(u)du = sum_k w_k' * f(u_k) * sd * exp(z_k^2/2) with w_k' = sqrt(2pi)*w_k(prob weights)
    def nll2(par):
        b = par[:5]; s = np.exp(par[5]); tot = 0
        for i, idx in enumerate(idxs):
            mu, sd = state["mu"][i], state["sd"][i]
            u = mu + sd * nodes
            lf = gl(b, u, idx) - 0.5 * (u / s) ** 2 - np.log(s) - 0.5 * np.log(2 * np.pi)
            lt = lf + np.log(sd) + 0.5 * nodes ** 2 + np.log(w * np.sqrt(2 * np.pi))
            mx = lt.max(); tot += mx + np.log(np.exp(lt - mx).sum())
        return -tot
    par = np.zeros(6)
    for it in range(6):  # update adaptive centres/scales at current params, re-optimise
        b = par[:5]; s = np.exp(par[5])
        for i, idx in enumerate(idxs):
            f = lambda u: -(gl(b, np.array([u]), idx)[0] - 0.5 * (u / s) ** 2)
            r = optimize.minimize_scalar(f)
            u0 = r.x; e = X[idx] @ b + u0; p = 1 / (1 + np.exp(-e))
            h = (p * (1 - p)).sum() + 1 / s ** 2
            state["mu"][i], state["sd"][i] = u0, 1 / np.sqrt(h)
        o = optimize.minimize(nll2, par, method="BFGS"); par = o.x
    # Hessian at the final params (adaptation fixed at the final centres)
    import statsmodels.tools.numdiff as nd
    H = nd.approx_hess(par, nll2)
    cov = np.linalg.inv(H)
    return par, cov, x

def glmm_contrasts():
    par, cov, x = glmm_logit(d)
    print("GLMM params", par, "sd re", np.exp(par[5]))
    res = {}
    for k, (a, c) in pairs.items():
        L = np.zeros(6)
        for t_, sgn in ((a, 1), (c, -1)):
            if t_ == "B": L[1] += sgn
            if t_ == "C": L[2] += sgn
        est = L @ par; se = np.sqrt(L @ cov @ L)
        res[k] = (est, est - 1.96 * se, est + 1.96 * se, 2 * stats.norm.sf(abs(est / se)))
    return res

tmpl = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "template.json"))) if False else None
tpath = os.path.join(out_dir, "..", "template.json")
tmpl = json.load(open(tpath))
def setc(cell, v, src):
    c = tmpl["cells"][cell]; c["value"] = float(v); c["stars"] = ""; c["source"] = src

def means(col, k, how):
    a, c = pairs[k]
    return [d.loc[d.tech == t_, col].mean() for t_ in (a, c)]

specs = [("time", "lt", "t", True), ("ks", "lks", "ks", True), ("sp", "sp", "sp", False)]
for pre, mvar, rawcol, islog in specs:
    r = lmm_contrasts(mvar)
    for k in pairs:
        est, lo, hi, p = r[k]
        f = np.exp if islog else (lambda v: v)
        src = f"lmm_contrasts({mvar}) REML random intercept subject; Wald z"
        setc(f"{pre}_{k}|eff", f(est), src); setc(f"{pre}_{k}|lo", f(lo), src); setc(f"{pre}_{k}|hi", f(hi), src); setc(f"{pre}_{k}|p", p, src)
        m1, m2 = means(rawcol, k, None)
        setc(f"{pre}_{k}|m1", m1, "arithmetic mean over valid runs"); setc(f"{pre}_{k}|m2", m2, "arithmetic mean over valid runs")
r = glmm_contrasts()
for k in pairs:
    est, lo, hi, p = r[k]; src = "glmm_contrasts: logit random-intercept GLMM, adaptive GH quadrature (15), Wald z"
    setc(f"mi_{k}|eff", np.exp(est), src); setc(f"mi_{k}|lo", np.exp(lo), src); setc(f"mi_{k}|hi", np.exp(hi), src); setc(f"mi_{k}|p", p, src)
    m1, m2 = means("mi", k, None)
    setc(f"mi_{k}|m1", m1, "mean mistake count per run"); setc(f"mi_{k}|m2", m2, "mean mistake count per run")
json.dump(tmpl, open(os.path.join(out_dir, "filled.json"), "w"), indent=1)
for key, c in tmpl["cells"].items(): print(key, round(c["value"], 5))
