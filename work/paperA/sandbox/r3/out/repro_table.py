"""Reproduce Table 1 (median change in functional assessments over 6 years).
Usage: python -I out/repro_table.py data out
"""
import sys, os, glob, json
import numpy as np, pandas as pd
from scipy import stats

DATA, OUT = sys.argv[1], sys.argv[2]
HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = os.path.join(HERE, os.pardir, 'template.json')
UNABLE = 10000.0

ROWS = {  # row id -> (baseline column, follow-up column)
    'fvc_sit': ('FVC sitting B (%)', 'FVC sitting F (%)'),
    'fvc_lie': ('FVC lying B (%)', 'FVC lying F (%)'),
    'hip_flex': ('Hip flexion B (kg)', 'Hip flexion F (kg)'),
    'hip_add': ('Hip Adduction B (kg)', 'Hip Adduction F (kg)'),
    'hip_abd': ('Hip Abduction B (kg)', 'Hip Abduction F (kg)'),
    'knee_ext': ('Knee Extension B (kg)', 'Knee Extension F (kg)'),
    'knee_flex': ('Knee Flexion B (kg)', 'Knee Flexion F (kg)'),
    'ankle_df': ('Ankle Dorsiflexion B (kg)', 'Ankle Dorsiflexion F (kg)'),
    'smwt': ('Six minute walk B (m)', 'Six minute walk F (m)'),
    'tug': ('Timed up and go velocity B (m/s)', 'Timed up and go velocity F (m/s)'),
    'tmwr': ('Ten metre walk or run velocity B (m/s)', 'Ten metre walk or run velocity F (m/s)'),
    'stair_up': ('Stair ascent velocity B (steps/s)', 'Stair ascent velocity F (steps/s)'),
    'stair_down': ('Stair descent velocity B (steps/s)', 'Stair descent velocity F (steps/s)'),
    'chair': ('Chair Rise B (s)', 'Chair Rise F (s)'),
}


def load(data_dir):
    f = sorted(glob.glob(os.path.join(data_dir, '*.xlsx')))[0]
    df = pd.read_excel(f)
    df = df[pd.to_numeric(df['Patient no'], errors='coerce').notna()].copy()  # drop NOTES rows
    df.columns = [str(c).strip() for c in df.columns]
    return df


def paired(df, b, f):
    x = pd.to_numeric(df[b], errors='coerce'); y = pd.to_numeric(df[f], errors='coerce')
    m = x.notna() & y.notna()
    return x[m].to_numpy(float), y[m].to_numpy(float)


def wilcoxon_spss(x, y):
    """SPSS-style asymptotic Wilcoxon signed-rank: zero differences dropped,
    average ranks for ties, tie-corrected variance, no continuity correction."""
    d = y - x
    d = d[d != 0]
    n = len(d)
    if n == 0:
        return float('nan'), float('nan')
    r = stats.rankdata(np.abs(d))
    wpos = r[d > 0].sum()
    mu = n * (n + 1) / 4.0
    _, cnt = np.unique(np.abs(d), return_counts=True)
    var = n * (n + 1) * (2 * n + 1) / 24.0 - (cnt ** 3 - cnt).sum() / 48.0
    z = (wpos - mu) / np.sqrt(var)
    return z, 2 * stats.norm.sf(abs(z))


def srm(x, y):
    d = y - x  # follow-up minus baseline
    return d.mean() / d.std(ddof=1)


def compute(df):
    res = {}
    for rid, (b, f) in ROWS.items():
        x, y = paired(df, b, f)
        z, p = wilcoxon_spss(x, y)
        if rid == 'chair':
            # medians and Wilcoxon: unable = 10,000 s (ranks last); SRM: only pairs with both times observed
            fin = (x < UNABLE) & (y < UNABLE)
            s = srm(x[fin], y[fin]); n_srm = int(fin.sum())
        else:
            s = srm(x, y); n_srm = len(x)
        res[rid] = dict(n=len(x), med_b=float(np.median(x)), med_f=float(np.median(y)),
                        z=float(z), p=float(p), srm=float(s), n_srm=n_srm)
        print(f"{rid:10s} n={len(x):2d} med_b={np.median(x):9.4f} med_f={np.median(y):9.4f} "
              f"z={z:7.4f} p={p:.5f} SRM={s:7.4f} (n_srm={n_srm})")
        # scipy cross-check
        try:
            sp = stats.wilcoxon(y, x, zero_method='wilcox', correction=False, method='approx')
            print(f"{'':10s} scipy approx p={sp.pvalue:.5f}; exact/auto p={stats.wilcoxon(y, x).pvalue:.5f}")
        except Exception as e:
            print('   scipy check failed:', e)
    return res


def main():
    os.makedirs(OUT, exist_ok=True)
    df = load(DATA)
    print('participants:', len(df))
    res = compute(df)
    with open(TEMPLATE) as fh:
        tpl = json.load(fh)
    for key, cell in tpl['cells'].items():
        rid, col = key.split('|')
        r = res[rid]
        if col in ('med_b', 'med_f'):
            cell['value'] = r[col]; cell['stars'] = ''
            cell['source'] = 'compute(): np.median over paired participants' + (
                ' (unable = 10000 s)' if rid == 'chair' else '')
        elif col == 'p':
            cell['value'] = r['p']; cell['stars'] = 'a' if r['p'] < 0.05 else ''
            cell['source'] = 'wilcoxon_spss(): asymptotic Wilcoxon signed-rank, zeros dropped, tie-corrected, no continuity correction' + (
                ' (unable = 10000 s)' if rid == 'chair' else '')
        elif col == 'srm':
            cell['value'] = r['srm']; cell['stars'] = ''
            cell['source'] = 'srm(): mean(F-B)/SD(F-B, ddof=1)' + (
                ' over pairs with both chair-rise times observed' if rid == 'chair' else '')
    with open(os.path.join(OUT, 'filled.json'), 'w') as fh:
        json.dump(tpl, fh, indent=1)
    print('wrote', os.path.join(OUT, 'filled.json'))


if __name__ == '__main__':
    main()
