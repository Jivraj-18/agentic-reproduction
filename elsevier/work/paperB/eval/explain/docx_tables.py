"""Extract tables from a .docx (stdlib only) and print them as tab-separated rows."""
import sys, zipfile, re
import xml.etree.ElementTree as ET
W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
def tables(path):
    root = ET.fromstring(zipfile.ZipFile(path).read('word/document.xml'))
    out = []
    for t in root.iter(W + 'tbl'):
        rows = []
        for tr in t.iter(W + 'tr'):
            rows.append([''.join(x.text or '' for x in tc.iter(W + 't')).strip() for tc in tr.iter(W + 'tc')])
        out.append(rows)
    return out, root
if __name__ == '__main__':
    tb, root = tables(sys.argv[1])
    if len(sys.argv) > 2 and sys.argv[2] == 'text':
        for p in root.iter(W + 'p'):
            s = ''.join(x.text or '' for x in p.iter(W + 't'))
            if s.strip(): print(s)
    for i, t in enumerate(tb):
        print('== table', i, len(t), 'rows')
        for r in t: print('\t'.join(r))
