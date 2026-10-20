"""Reproduce Table 1 (median change in functional assessments over 6 years).
Usage: python -I out/repro_table.py data out
"""
import sys, os, glob, json
import numpy as np, pandas as pd
from scipy import stats

data_dir, out_dir = sys.argv[1], sys.argv[2]
here = os.path.dirname(os.path.abspath(__file__))
tmpl_path = os.path.join(here, '..', 'template.json')
if not os.path.exists(tmpl_path):
    tmpl_path = os.path.join(data_dir, '..', 'template.json')

UNABLE = 10000.0

# row id -> (baseline column, follow-up column)
ROWS = {
    'fvc_sit':   ('FVC sitting B (%)', 'FVC sitting F (%)'),
    'fvc_lie':   ('FVC lying B (%)', 'FVC lying F (%)'),
    'hip_flex':  ('Hip flexion B (kg)', 'Hip flexion F (kg)'),
    'hip_add':   ('Hip Adduction B (kg)', 'Hip Adduction F (kg)'),
    'hip_abd':   ('Hip Abduction B (kg)', 'Hip Abduction F (kg)'),
    'knee_ext':  ('Knee Extension B (kg)', 'Knee Extension F (kg)'),
    'knee_flex': ('Knee Flexion B (kg)', 'Knee Flexion F (kg)'),
    'ankle_df':  ('Ankle Dorsiflexion B (kg)', 'Ankle Dorsiflexion F (kg)'),
    'smwt':      ('Six minute walk B (m)', 'Six minute walk F (m)'),
    'tug':       ('Timed up and go velocity B (m/s)', 'Timed up and go velocity F (m/s)'),
    'tmwr':      ('Ten metre walk or run velocity B (m/s)', 'Ten metre walk or run velocity F (m/s)'),
    'stair_up':  ('Stair ascent velocity B (steps/s)', 'Stair ascent velocity F (steps/s)'),
    'stair_down':('Stair descent velocity B (steps/s)', 'Stair descent velocity F (steps/s)'),
    'chair':     ('Chair Rise B (s)', 'Chair Rise F (s)'),
}


def load_data():
    f = glob.glob(os.path.join(data_dir, '*.xlsx'))[0]
    df = pd.read_excel(f, header=0)
    df = df[pd.to_numeric(df['Patient no'], errors='coerce').notna()].copy()  # drop NOTES rows
    df.columns = [str(c).strip() for c in df.columns]
    print(f'Loaded {len(df)} participants from {os.path.basename(f)}')
    return df


def paired(df, b, f):
    sub = df[[b, f]].apply(pd.to_numeric, errors='coerce').dropna()
    return sub[b].to_numpy(float), sub[f].to_numpy(float)


def wilcoxon_p(x0, x1):
    """SPSS-style asymptotic Wilcoxon signed-rank: zero differences dropped,
    tie-corrected variance, no continuity correction."""
    d = x1 - x0
    if np.all(d == 0):
        return float('nan')
    r = stats.wilcoxon(x1, x0, zero_method='wilcox', correction=False, method='approx')
    return float(r.pvalue)


def srm(x0, x1):
    d = x1 - x0  # follow-up minus baseline
    return float(np.mean(d) / np.std(d, ddof=1))


def compute_row(df, rid):
    b, f = ROWS[rid]
    x0, x1 = paired(df, b, f)
    res = {'n': len(x0)}
    res['med_b'] = float(np.median(x0))   # median_paired (10,000 s kept for chair rise)
    res['med_f'] = float(np.median(x1))
    res['p'] = wilcoxon_p(x0, x1)
    if rid == 'chair':
        ok = (x0 < UNABLE) & (x1 < UNABLE)
        res['srm'] = srm(x0[ok], x1[ok])
        res['n_srm'] = int(ok.sum())
        res['n_unable_b'] = int((x0 >= UNABLE).sum()); res['n_unable_f'] = int((x1 >= UNABLE).sum())
    else:
        res['srm'] = srm(x0, x1)
    return res


def main():
    df = load_data()
    with open(tmpl_path, encoding='utf-8') as fh:
        tmpl = json.load(fh)
    out = json.loads(json.dumps(tmpl))
    src = {'med_b': 'compute_row: np.median of baseline over paired cases',
           'med_f': 'compute_row: np.median of follow-up over paired cases',
           'p': 'wilcoxon_p: scipy.stats.wilcoxon approx, zero_method=wilcox, no continuity correction',
           'srm': 'srm: mean(F-B)/sd(F-B, ddof=1)'}
    print(f"{'row':<11}{'n':>4}{'med_b':>10}{'med_f':>10}{'p':>12}{'srm':>10}")
    for row in tmpl['rows']:
        rid = row['id']
        r = compute_row(df, rid)
        extra = ''
        if rid == 'chair':
            extra = f"  (SRM on n={r['n_srm']} pairs with both times; unable B={r['n_unable_b']}, F={r['n_unable_f']})"
        print(f"{rid:<11}{r['n']:>4}{r['med_b']:>10.4f}{r['med_f']:>10.4f}{r['p']:>12.6f}{r['srm']:>10.4f}{extra}")
        for col in ['med_b', 'med_f', 'p', 'srm']:
            cell = out['cells'][f'{rid}|{col}']
            v = r[col]
            cell['value'] = None if v != v else round(v, 6)
            if col == 'p':
                cell['stars'] = 'a' if (v == v and v < 0.05) else ''
            else:
                cell['stars'] = ''
            s = src[col]
            if rid == 'chair' and col == 'srm':
                s += ' on pairs where both chair-rise times are finite (10,000 s excluded)'
            cell['source'] = s
            cell['n'] = r['n'] if not (rid == 'chair' and col == 'srm') else r['n_srm']
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, 'filled.json'), 'w', encoding='utf-8') as fh:
        json.dump(out, fh, indent=1)
    print('Wrote', os.path.join(out_dir, 'filled.json'))


if __name__ == '__main__':
    main()
