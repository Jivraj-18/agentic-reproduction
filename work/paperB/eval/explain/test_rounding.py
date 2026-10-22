"""Test rounding-based readings across ALL rows of Table 2, using the runs' per-test fits (opus)
and the authors' deposited per-test values:
  R1: 'range' = max - min of per-test values first rounded to the printed precision of the range column
  R2: r2 statistics computed from per-test r2 rounded to 3 decimals
Report how many cells match (grade A = within 2% after rounding to the published decimals)."""
import os, sys, json, numpy as np, pandas as pd
from scipy.stats import shapiro
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from compare_authors_fits import parse_supp, P
pub = json.load(open(os.path.join(P, 'extract', 'tables_full.json'), encoding='utf-8'))['cells']
sup = parse_supp(); A = sup[sup.part == 'A']; shamB = sup[(sup.combination == 'M2CA-M2CA') & (sup.part == 'B(M2CA)')]
opus = pd.read_csv(os.path.join(P, 'sandbox', 'r_opus', 'out', 'per_test_fits.csv')).set_index('test')
rows = [f'{q}_{t}' for q in ('ec25', 'ec50', 'ec75', 'slope', 's', 'r2') for t in (15, 30, 45)]
def auth(row):
    q, t = row.rsplit('_', 1); t = int(t)
    return np.r_[A[A.time == t][q].values, shamB[shamB.time == t][q].values]
def grade(x, cell):
    p = pub[cell]; d = p['decimals']; xr = round(x, d)
    return abs(xr - p['value']) / abs(p['value']) * 100 if p['value'] else 0
print('R1: range from per-test values rounded to the range column\'s printed decimals')
for src in ('run', 'authors'):
    nA = 0; out = []
    for row in rows:
        v = opus[row].values if src == 'run' else auth(row)
        d = pub[row + '|range']['decimals']
        plain = v.max() - v.min(); rr = np.round(v, d).max() - np.round(v, d).min()
        gp, gr = grade(plain, row + '|range'), grade(rr, row + '|range')
        if gp > 2 or gr > 2: out.append(f'   {row}: pub {pub[row+"|range"]["raw"]} plain {plain:.4f} (dev {gp:.1f}%)  rounded-first {rr:.4f} (dev {gr:.1f}%)')
        nA += gr <= 2
    print(f'  [{src}] rounded-first range within 2% in {nA}/{len(rows)} rows; rows where either reading misses:'); print('\n'.join(out))
print('\nR2: r2 rows from per-test r2 rounded to 3 decimals')
for src in ('run', 'authors'):
    for row in ('r2_15', 'r2_30', 'r2_45'):
        v = opus[row].values if src == 'run' else auth(row)
        for lab, w in (('4dp-ish (as fitted)', v), ('rounded 3dp', np.round(v, 3)), ('rounded 4dp', np.round(v, 4))):
            sd = w.std(ddof=1); m = w.mean(); c = sd / m * 100
            print(f'  [{src}] {row} {lab:20s} mean={m:.4f} sd={sd:.4f} cv={c:.4f}(pub {pub[row+"|cv"]["raw"]}, dev {grade(c,row+"|cv"):.1f}%) range={w.max()-w.min():.4f}(pub {pub[row+"|range"]["raw"]}) W={shapiro(w).statistic:.3f}(pub {pub[row+"|sw"]["raw"]})')
