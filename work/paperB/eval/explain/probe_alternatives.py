"""Try alternative readings for the four non-A cells (s_30 mean/range, r2_15 CV, r2_45 CV)
using (a) the runs' per-test fits and (b) the authors' deposited per-test values."""
import os, sys, numpy as np, pandas as pd
from scipy.stats import shapiro
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from compare_authors_fits import parse_supp, P

sup = parse_supp(); A = sup[sup.part == 'A']; shamB = sup[(sup.combination == 'M2CA-M2CA') & (sup.part == 'B(M2CA)')]
def auth(q, t):
    return np.r_[A[A.time == t][q].values, shamB[shamB.time == t][q].values]
opus = pd.read_csv(os.path.join(P, 'sandbox', 'r_opus', 'out', 'per_test_fits.csv')).set_index('test')
def cv(v, ddof=1): v = np.asarray(v, float); return v.std(ddof=ddof) / v.mean() * 100

print('=== s_30 (published mean 0.55, SD 0.084, CV 15.7, range 0.34) ===')
for lab, v in [('run (opus)', opus.s_30.values), ('authors supplement', auth('s', 30))]:
    print(f'{lab:20s} mean={v.mean():.4f} median={np.median(v):.4f} sd={v.std(ddof=1):.4f} cv={cv(v):.2f} range={v.max()-v.min():.4f}')
print('implied mean from printed SD/CV: 0.084/0.157 =', round(0.084 / 0.157, 4))
print('printed mean with printed SD gives CV', round(0.084 / 0.55 * 100, 2), '(printed 15.7)')
v = auth('s', 30)
print('range double-rounded: %.4f -> %.3f -> %.2f' % (v.max() - v.min(), round(v.max() - v.min(), 3), round(round(v.max() - v.min(), 3) + 1e-12, 2)))
print('max/min s_30 authors:', v.max(), v.min())
# drop-one / swap sham variants
vals = auth('s', 30); m = [np.delete(vals, i).mean() for i in range(len(vals))]
print('drop-one means range: %.4f..%.4f' % (min(m), max(m)))
print('needed sum for mean 0.545 (lowest value rounding to 0.55):', round(0.545 * 31, 3), 'actual sum', round(vals.sum(), 3))
# what if s_30 used other time columns by mistake
for t in (15, 45):
    w = auth('s', t); print(f'  s_{t} authors mean {w.mean():.4f}')
# mean of the 15/30/45 B(M2CA) tests or including all B-alone tests? (not M2CA) skip

print('\n=== r2_15 CV (published 0.17; SD printed 0.002, mean 0.9977) ===')
for lab, v in [('run (opus)', opus.r2_15.values), ('authors supplement', auth('r2', 15))]:
    print(f'{lab:20s} mean={v.mean():.5f} sd={v.std(ddof=1):.6f} cv(n-1)={cv(v):.4f} cv(n)={cv(v,0):.4f} sw={shapiro(v).statistic:.4f}')
v = auth('r2', 15)
print('rounded r2 to 3 dp: cv=%.4f ; CV from printed SD/mean: %.4f' % (cv(np.round(v, 3)), 0.002 / 0.9977 * 100))
dm = [cv(np.delete(v, i)) for i in range(len(v))]; print('drop-one CVs: %.4f..%.4f' % (min(dm), max(dm)))
print('SD needed for CV to round to 0.17: >= %.6f' % (0.165 / 100 * v.mean()))

print('\n=== r2_45 CV (published 0.06) ===')
for lab, v in [('run (opus)', opus.r2_45.values), ('authors supplement', auth('r2', 45))]:
    print(f'{lab:20s} mean={v.mean():.5f} sd={v.std(ddof=1):.6f} cv={cv(v):.4f} -> {round(cv(v), 2)} sw={shapiro(v).statistic:.4f}')
# swap only the two tests whose 45-min fits differ
rv = opus.r2_45.copy()
for c in ('M2CA-4NBB', 'M2CA-EUG'):
    rv[c + ':A'] = A[(A.combination == c) & (A.time == 45)].r2.iloc[0]
print('run values with authors\' 4NBB and EUG 45-min r2 swapped in: cv=%.4f -> %.2f' % (cv(rv.values), round(cv(rv.values), 2)))
rv = opus.r2_45.copy(); rv['M2CA-4NBB:A'] = 0.9982
print('only 4NBB swapped: cv=%.4f' % cv(rv.values))
