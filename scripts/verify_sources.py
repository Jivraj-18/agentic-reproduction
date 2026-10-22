"""Acceptance check: every `source_sentence` in methods.json appears verbatim in the PDF.

Comparison ignores whitespace, hyphenation, line breaks and non-ASCII glyphs (the PDF text
layer drops Greek letters, micro signs and superscripts). '…' marks an elision (citation
superscripts) and each fragment must appear, in order.

Usage: python -I verify_sources.py <methods.json> <paper.pdf> <out.json>
"""
import json
import re
import sys
import unicodedata

import pypdfium2 as pdfium


def norm(s):
    s = unicodedata.normalize("NFKD", s)
    s = s.encode("ascii", "ignore").decode()  # also drops curly quotes
    s = re.sub(r"[\x00-\x1f]", "", s)  # control glyphs, e.g. the minus in 'msec-1'
    return re.sub(r"[\s\-\"'`]+", "", s)


def walk(obj, path=""):
    if isinstance(obj, dict):
        if "source_sentence" in obj:
            yield path or obj.get("id", "?"), obj
        for k, v in obj.items():
            yield from walk(v, f"{path}.{k}" if path else k)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from walk(v, f"{path}[{i}]")


def main(methods_path, pdf_path, out_path):
    methods = json.load(open(methods_path, encoding="utf-8"))
    pdf = pdfium.PdfDocument(pdf_path)
    text = norm("\n".join(pdf[i].get_textpage().get_text_range() for i in range(len(pdf))))
    results = []
    for path, item in walk(methods):
        frags = [norm(f) for f in item["source_sentence"].split("…") if norm(f)]
        pos, ok = 0, True
        for f in frags:
            j = text.find(f, pos)
            if j < 0:
                ok = False
                break
            pos = j + len(f)
        results.append({"item": item.get("id", path), "path": path, "verbatim": ok})
    bad = [r for r in results if not r["verbatim"]]
    json.dump({"n": len(results), "n_failed": len(bad), "results": results}, open(out_path, "w"), indent=1)
    print(f"{len(results)} source sentences, {len(bad)} not found")
    for r in bad:
        print("  NOT FOUND:", r["path"])


if __name__ == "__main__":
    main(*sys.argv[1:])
