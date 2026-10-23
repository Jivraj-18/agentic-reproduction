"""Compare the runs' per-test fits with the authors' deposited per-test endpoint values
(Supplemental Table - Endpoint Values.docx, withheld from the blind runs), and recompute
Table 2 from the authors' own per-test values."""
import sys, os, re, zipfile, json
import xml.etree.ElementTree as ET
import numpy as np, pandas as pd
from scipy.stats import shapiro
HERE = os.path.dirname(os.path.abspath(__file__))
P = os.path.abspath(os.path.join(HERE, '..', '..'))
W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'

def parse_supp():
    root = ET.fromstring(zipfile.ZipFile(os.path.join(P, 'source', 'data',
        'M2CA Study - Supplemental Table - Endpoint Values.docx')).read('word/document.xml'))
    body = root.find(W + 'body')
    combo = None; recs = []
    for el in body:
        if el.tag == W + 'p':
            s = ''.join(x.text or '' for x in el.iter(W + 't'))
            m = re.search(r'Combination \(A-B\):\s*(\S+)', s)
            if m: combo = m.group(1)
        elif el.tag == W + 'tbl':
            rows = [[''.join(x.text or '' for x in tc.iter(W + 't')).strip() for tc in tr.iter(W + 'tc')]
                    for tr in el.iter(W + 'tr')]
            if not rows[0][0] == '' or 'EC25' not in rows[0][2]: continue
            lab = None
            for r in rows[1:]:
                if r[0]: lab = r[0]
                if not r[1]: continue
                r = [x.replace(",", "") for x in r]
                recs.append(dict(combination=combo, part=lab, time=int(r[1]), ec25=float(r[2]), ec50=float(r[3]),
                                 ec75=float(r[4]), slope=float(r[5]), s=float(r[6]), r2=float(r[7]),
                                 tdt=float(r[8]) if len(r) > 8 and r[8] else np.nan))
    return pd.DataFrame(recs)

def stats(v):
    v = np.asarray(v, float); m = v.mean(); sd = v.std(ddof=1)
    return dict(mean=m, sd=sd, cv=sd / m * 100, range=v.max() - v.min(), sw=shapiro(v).statistic)

if __name__ == '__main__':
    sup = parse_supp()
    print('combinations in supplement:', sup.combination.nunique(), ' parts:', sorted(sup.part.unique()))
    A = sup[sup.part == 'A']
    sham = sup[(sup.combination == 'M2CA-M2CA') & (sup.part.str.startswith('B'))]
    print('sham B rows:\n', sham.to_string())
    auth = {}
    for t in (15, 30, 45):
        a = A[A.time == t].set_index('combination')
        sb = sham[(sham.time == t)].iloc[0]
        for q in ('ec25', 'ec50', 'ec75', 'slope', 's', 'r2'):
            auth[f'{q}_{t}'] = list(a[q].values) + [sb[q]]
    tdtA = A[A.time == 45].set_index('combination').tdt
    tdt_sham = sham[sham.time == 45].tdt.dropna()
    auth['tdt_15_45'] = list(tdtA.values) + list(tdt_sham.values[:1])
    pub = json.load(open(os.path.join(P, 'extract', 'tables_full.json'), encoding='utf-8'))['cells']
    print('\nTable 2 recomputed from the AUTHORS\' per-test values (n=%d):' % len(auth['s_30']))
    for row in ('s_30', 'r2_15', 'r2_45', 'r2_30', 's_15', 's_45'):
        st = stats(auth[row])
        print(f'{row:6s}', '  '.join(f'{k}={st[k]:.5g} (pub {pub[row+"|"+k]["raw"]})' for k in st))
    # per-test comparison with the run fits
    for run in ('r_opus', 'r_sonnet'):
        f = pd.read_csv(os.path.join(P, 'sandbox', run, 'out', 'per_test_fits.csv'))
        if 'combo' in f.columns: f['test'] = f.combo + f.test.map({1: ':A', 2: ':B', 3: ':MX'})
        f = f.set_index('test')
        print(f'\n[{run}] per-test differences vs authors (|diff| in s_30 > 0.01, r2 > 0.0003):')
        for t in (15, 30, 45):
            a = A[A.time == t].set_index('combination')
            for c in a.index:
                fr = f.loc[c + ':A']
                ds = fr[f's_{t}'] - a.loc[c, 's']; dr = fr[f'r2_{t}'] - a.loc[c, 'r2']
                if abs(ds) > 0.01 or abs(dr) > 0.0003:
                    print(f'  {c} t={t}: run s={fr[f"s_{t}"]:.4f} auth s={a.loc[c,"s"]:.4f} | run r2={fr[f"r2_{t}"]:.4f} auth r2={a.loc[c,"r2"]:.4f} | run ec50={fr[f"ec50_{t}"]:.3f} auth {a.loc[c,"ec50"]:.3f}')
