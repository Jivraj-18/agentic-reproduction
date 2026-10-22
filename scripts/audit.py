"""Audits 1 and 2: path/URL audit and hardcoding audit.

1. Path and URL audit: every tool call in the reproducer's transcript (and its run.log) is
   scanned for file paths and URLs. A path is allowed if it resolves inside that run's sandbox,
   or is the Python interpreter named in TASK.md. Web tools and any URL are forbidden.
2. Hardcoding audit: every numeric literal in out/repro_table.py is compared with every published
   value. A literal that equals a published value (at its printed precision) and is not a constant
   stated in methods.json/TASK.md is flagged.

Usage: python -I audit.py <paper_dir> <transcripts_dir> <python_exe> <out.json>
transcripts_dir holds r1.jsonl, r2.jsonl, ... (the reproducer agents' transcripts).
"""
import ast
import json
import re
import sys
from pathlib import Path, PureWindowsPath

WEB_TOOLS = {"WebFetch", "WebSearch"}
PATH_KEYS = ("file_path", "path", "notebook_path")
WIN_PATH = re.compile(r"(?:[A-Za-z]:[\\/]|/[a-zA-Z]/|~[\\/]|\\\\[A-Za-z0-9.-]+\\)[^\s\"'`|;&<>*?]*")
URL = re.compile(r"https?://[^\s\"'`)]+")
PARENT = re.compile(r"(?:^|[\s\"'=(])\.\.(?:[\\/]|$|\s)")


def norm_path(p):
    p = p.strip().strip("\"'")
    m = re.match(r"^/([a-zA-Z])/(.*)", p)  # git-bash /c/Users -> C:/Users
    if m:
        p = f"{m.group(1)}:/{m.group(2)}"
    return str(PureWindowsPath(p)).lower().rstrip("\\")


def tool_calls(transcript):
    for line in open(transcript, encoding="utf-8"):
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        stack = [obj]
        while stack:
            o = stack.pop()
            if isinstance(o, dict):
                if o.get("type") == "tool_use" and "name" in o:
                    yield o["name"], o.get("input") or {}
                else:
                    stack.extend(o.values())
            elif isinstance(o, list):
                stack.extend(o)


def classify(path, root, python):
    n = norm_path(path)
    if n.startswith(root) or n == python or n.startswith(python):
        return "allowed"
    if n.startswith(norm_path(str(Path(python).parent.parent))):  # the venv itself (interpreter internals)
        return "allowed-interpreter"
    return "forbidden"


def path_audit(transcript, run_log, root, python):
    root, python = norm_path(str(root)), norm_path(python)
    accesses, n_calls = [], 0
    for name, inp in tool_calls(transcript):
        n_calls += 1
        if name in WEB_TOOLS:
            accesses.append({"tool": name, "target": json.dumps(inp)[:200], "class": "forbidden-web"})
            continue
        texts = []
        for k in PATH_KEYS:
            if isinstance(inp.get(k), str):
                p = inp[k]
                if not re.match(r"^([A-Za-z]:|/|\\\\|~)", p):  # relative to the working dir (the sandbox)
                    accesses.append({"tool": name, "target": p,
                                     "class": "forbidden" if PARENT.search(" " + p) else "allowed-relative"})
                    continue
                accesses.append({"tool": name, "target": p, "class": classify(p, root, python)})
        for k in ("command", "pattern", "url", "query", "prompt"):
            if isinstance(inp.get(k), str):
                texts.append(inp[k])
        for t in texts:
            for p in WIN_PATH.findall(t):
                accesses.append({"tool": name, "target": p, "class": classify(p, root, python)})
            for u in URL.findall(t):
                accesses.append({"tool": name, "target": u, "class": "forbidden-url"})
            if name in ("Bash", "PowerShell"):
                for m in PARENT.finditer(t):  # keep the surrounding text so a reviewer can see what '..' points at
                    accesses.append({"tool": name, "target": t[max(0, m.start() - 40):m.end() + 40], "class": "review-parent-dir"})
    if run_log.exists():
        log = run_log.read_text(encoding="utf-8", errors="replace")
        for p in WIN_PATH.findall(log):
            accesses.append({"tool": "run.log", "target": p, "class": classify(p, root, python)})
        for u in URL.findall(log):
            accesses.append({"tool": "run.log", "target": u, "class": "forbidden-url"})
    if n_calls == 0:
        raise SystemExit(f"{transcript}: no tool calls found; wrong transcript file?")
    counts = {}
    for a in accesses:
        counts[a["class"]] = counts.get(a["class"], 0) + 1
    flagged = [a for a in accesses if not a["class"].startswith("allowed")]
    return {"tool_calls": n_calls, "accesses": len(accesses), "counts": counts, "flagged": flagged}


def numbers_in(text):
    return {float(x) for x in re.findall(r"(?<![\w.])-?\d+(?:\.\d+)?", text)}


def hardcoding_audit(script, full, allowed_consts):
    tree = ast.parse(script.read_text(encoding="utf-8"))
    lits = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
            v = float(node.value)
            neg = False
            lits.append((v, node.lineno))
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub) and isinstance(node.operand, ast.Constant) \
                and isinstance(node.operand.value, (int, float)):
            lits.append((-float(node.operand.value), node.lineno))
    lines = script.read_text(encoding="utf-8").splitlines()
    flags = []
    for key, c in full["cells"].items():
        if not c["graded"] or c["value"] is None:
            continue
        p, d = c["value"], c["decimals"]
        if d == 0 and abs(p) < 10:  # single-digit integers ('-1', '5') are not identifiable
            continue
        for v, ln in lits:
            if round(v, d) == p and len(repr(v).split(".")[-1]) <= d + 1:
                status = "explained (constant stated in methods)" if v in allowed_consts or abs(v) in allowed_consts else "FLAG"
                flags.append({"cell": key, "published": c["raw"], "literal": v, "line": ln,
                              "code": lines[ln - 1].strip()[:160], "status": status})
    return {"numeric_literals": len(lits), "matches": flags,
            "flagged": [f for f in flags if f["status"] == "FLAG"]}


def main(paper_dir, transcripts, python, out_path):
    paper_dir, transcripts = Path(paper_dir), Path(transcripts)
    full = json.load(open(paper_dir / "extract" / "tables_full.json", encoding="utf-8"))
    rp = paper_dir / "eval" / "audit_review.json"
    review = json.load(open(rp, encoding="utf-8")) if rp.exists() else {}
    report = {}
    for sb in sorted((paper_dir / "sandbox").glob("r*")):
        consts = numbers_in((sb / "methods.json").read_text(encoding="utf-8")) | numbers_in((sb / "TASK.md").read_text(encoding="utf-8"))
        t = transcripts / f"{sb.name}.jsonl"
        pa = path_audit(t, sb / "out" / "run.log", sb.resolve(), python) if t.exists() else {"error": "no transcript"}
        script = sb / "out" / "repro_table.py"
        ha = hardcoding_audit(script, full, consts) if script.exists() else {"error": "no script"}
        for f in pa.get("flagged", []):
            for rv in review.get("paths", []):
                if rv["match"] in f["target"]:
                    f["review"] = {"verdict": rv["verdict"], "reason": rv["reason"]}
        for f in ha.get("flagged", []):
            for rv in review.get("hardcoding", []):
                if rv["run"] == sb.name and rv["line"] == f["line"]:
                    f["review"] = {"verdict": rv["verdict"], "reason": rv["reason"]}
        pa["unreviewed"] = sum(1 for f in pa.get("flagged", []) if "review" not in f)
        ha["unreviewed"] = sum(1 for f in ha.get("flagged", []) if "review" not in f)
        report[sb.name] = {"path_audit": pa, "hardcoding": ha}
        print(sb.name, "paths:", pa.get("counts"), "flagged:", len(pa.get("flagged", [])),
              "| literals:", ha.get("numeric_literals"), "hardcode flags:", len(ha.get("flagged", [])), "| unreviewed:", pa.get("unreviewed"), ha.get("unreviewed"))
    json.dump(report, open(out_path, "w", encoding="utf-8"), indent=1, ensure_ascii=False)


if __name__ == "__main__":
    main(*sys.argv[1:])
