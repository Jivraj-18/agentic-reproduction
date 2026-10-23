"""Exact cost of one agent run, from the per-request token usage in its transcript.

Each API response is logged several times while it streams (once per content block), and the early
copies carry partial output counts. So requests are deduplicated by message id, keeping the copy
with the largest output count (the final one). Cache writes are priced by their own TTL, using the
5-minute / 1-hour split the transcript records, so the result is one number, not a range.

Prices are USD per million tokens, Anthropic first-party API list prices.

Usage: python -I agent_cost.py <transcript.jsonl> <out.json> [label]
"""
import json
import sys

PRICES = {  # input, output, cache read; cache writes are 1.25x (5 min) and 2x (1 h) the input price
    "claude-opus-5-5": (4.00, 20.00, 0.20),
    "claude-sonnet-5-5": (2.00, 10.00, 0.20),
}
FIELDS = ("input_tokens", "output_tokens", "cache_read_input_tokens", "cache_write_5m_tokens", "cache_write_1h_tokens")


def visible_output_chars(path):
    """Characters the agent visibly generated (text and tool-call inputs), counted once per content block."""
    seen, chars = set(), 0
    for line in open(path, encoding="utf-8"):
        try:
            ev = json.loads(line)
        except ValueError:
            continue
        msg = ev.get("message") or {}
        if ev.get("type") != "assistant":
            continue
        for i, b in enumerate(msg.get("content") or []):
            key = (msg.get("id"), b.get("id") or i, b.get("type"))
            if key in seen:
                continue
            seen.add(key)
            if b.get("type") == "tool_use":
                chars += len(json.dumps(b.get("input", {}), ensure_ascii=False))
            elif b.get("type") == "text":
                chars += len(b.get("text", ""))
    return chars


def requests(path):
    """Final usage per API request (message id), with its model."""
    best = {}
    for line in open(path, encoding="utf-8"):
        try:
            ev = json.loads(line)
        except ValueError:
            continue
        msg = ev.get("message") or {}
        usage, mid = msg.get("usage"), msg.get("id")
        if ev.get("type") != "assistant" or not usage or not mid or msg.get("model") == "<synthetic>":
            continue
        if mid not in best or (usage.get("output_tokens") or 0) >= (best[mid][1].get("output_tokens") or 0):
            best[mid] = (msg.get("model"), usage)
    return best.values()


def main(path, out, label=""):
    totals = {}
    n = 0
    for model, u in requests(path):
        n += 1
        cc = u.get("cache_creation") or {}
        w5, w1 = cc.get("ephemeral_5m_input_tokens") or 0, cc.get("ephemeral_1h_input_tokens") or 0
        if w5 + w1 == 0:  # no split recorded: count the write at the 5-minute rate
            w5 = u.get("cache_creation_input_tokens") or 0
        t = totals.setdefault(model, dict.fromkeys(FIELDS, 0))
        t["input_tokens"] += u.get("input_tokens") or 0
        t["output_tokens"] += u.get("output_tokens") or 0
        t["cache_read_input_tokens"] += u.get("cache_read_input_tokens") or 0
        t["cache_write_5m_tokens"] += w5
        t["cache_write_1h_tokens"] += w1
    cost = 0.0
    for model, t in totals.items():
        pin, pout, pread = PRICES[model]
        t["cost_usd"] = round((t["input_tokens"] * pin + t["output_tokens"] * pout + t["cache_read_input_tokens"] * pread
                               + t["cache_write_5m_tokens"] * pin * 1.25 + t["cache_write_1h_tokens"] * pin * 2) / 1e6, 4)
        cost += t["cost_usd"]
    # Subagent transcripts keep only the streaming-start usage for most requests, so logged output tokens are
    # far too low. Replace them by the visible output (about 3.5 characters per token) where that is larger.
    # Hidden thinking tokens cannot be counted, so cost_at_least_usd is a lower bound, not an exact figure.
    vis_tokens = round(visible_output_chars(path) / 3.5)
    logged_out = sum(t["output_tokens"] for t in totals.values())
    model = max(totals, key=lambda m: totals[m]["cost_usd"]) if totals else None
    extra = max(0, vis_tokens - logged_out) * PRICES[model][1] / 1e6 if model else 0.0
    rec = {"label": label, "transcript": path.replace("\\", "/").rsplit("/", 1)[-1], "api_requests": n,
           "cost_usd": round(cost, 4), "visible_output_tokens_est": vis_tokens,
           "cost_at_least_usd": round(cost + extra, 4),
           "note": "cost_usd prices the tokens as logged; logged output is undercounted in subagent transcripts. "
                   "cost_at_least_usd uses the visible output instead; hidden thinking tokens are not included.",
           "by_model": totals,
           "prices_per_mtok": {m: {"input": p[0], "output": p[1], "cache_read": p[2], "cache_write_5m": p[0] * 1.25,
                                   "cache_write_1h": p[0] * 2} for m, p in PRICES.items() if m in totals}}
    json.dump(rec, open(out, "w", encoding="utf-8"), indent=1)
    print(f"{label}: logged ${rec['cost_usd']:.2f}, at least ${rec['cost_at_least_usd']:.2f}, {n} requests ->", out)


if __name__ == "__main__":
    main(*sys.argv[1:])
