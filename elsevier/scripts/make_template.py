"""Derive this client's report_template.html from the Wiley template, changing only what is Wiley-specific.

Same tabs, headline, tiles, drill-down, cause cards and evidence sections as the Wiley page. Changes:
two models (Opus 5.5 / Sonnet 5.5) instead of three runs, with a switch inside each paper tab; table layouts,
column names and glossary from work/meta.json; costs from the cost records; client name and data repository.
Every replacement must match exactly once, so a changed Wiley template fails loudly instead of silently.

Usage: python -I make_template.py <wiley_report_template.html> <out.html>
"""
import sys
from pathlib import Path

REPLACEMENTS = [
    ("<title>Reproducibility Check</title>", "<title>Reproducibility Check · {{CLIENT}}</title>"),
    ('<div class="brand">Reproducibility check<span>two Wiley papers</span></div>',
     '<div class="brand">Reproducibility check<span>two {{CLIENT}} papers</span></div>'),
    ("Nothing on this page is calculated live.",
     "Nothing on this page is calculated live. The publisher's name says whose papers were used; the page is not produced by or for the publisher."),
    ('const fmtDev = d => d == null ? "–" : (d === Infinity ? "∞" : (d < 0.05 ? "0%" : d.toFixed(d < 10 ? 1 : 0) + "%"));',
     'const fmtDev = d => d == null ? "–" : (d === Infinity || d >= 1000 ? "more than 10 times" : (d < 0.05 ? "0%" : d.toFixed(d < 10 ? 1 : 0) + "%"));'),
    ("const PL = DATA.plain, COST = DATA.cost;",
     """const PL = DATA.plain, COST = DATA.cost, MODELS = DATA.models;
/* Each paper was rebuilt once per model. SEL holds the model shown in each paper tab. */
const SEL = {};
Object.keys(DATA.byModel[MODELS[0].id]).forEach(pid => { SEL[pid] = MODELS[0].id; });
{ const h = (location.hash || "").slice(1).split("/"); const m = MODELS.find(x => x.id === "r_" + h[1]); if (m && h[0] in SEL) SEL[h[0]] = m.id; }
function use(pid) { DATA.papers[pid] = DATA.byModel[SEL[pid]][pid]; PL.papers[pid] = DATA.plainByModel[SEL[pid]][pid]; }
Object.keys(SEL).forEach(use);
const mlabel = id => (MODELS.find(m => m.id === id) || {}).label || id;
const usd = x => "$" + Number(x).toFixed(2);
const dataLink = x => /^10\\./.test(x) ? `https://doi.org/${x}` : `https://${x}`;
const paperCost = (pid, model) => (COST[pid][model] ? COST[pid][model].at_least : 0) + (COST[pid].explainer ? COST[pid].explainer.at_least : 0);"""),
    ('const RUN_LABEL = {r1:"Run 1", r2:"Run 2", r3:"Run 3", med:"Combined (middle of the 3 runs)"};',
     'const RUN_LABEL = {r_opus: "Claude Opus 5.5", r_sonnet: "Claude Sonnet 5.5", med: "Combined"};'),
    ("    const tds = L.flatMap(g => g.cols).map(col => {\n",
     "    const tds = L.flatMap(g => g.cols).map(col => {\n"
     "      if ([...col.fmt.matchAll(/\\{(\\w+)\\}/g)].some(mm => !p.cells[`${r.id}|${mm[1]}`])) return `<td class=\"v\"></td>`;\n"),
    ('            ${["med", ...runs].map((r, i) => `<button type="button" data-view="${r}" aria-pressed="${i === 0}">${RUN_LABEL[r]}</button>`).join("")}',
     '            ${MODELS.map(x => `<button type="button" data-model="${x.id}" aria-pressed="${x.id === SEL[pid]}">${esc(x.short)}</button>`).join("")}'),
    ('<div class="seg" role="group" aria-label="Which run to show" id="seg-${pid}">',
     '<div class="seg" role="group" aria-label="Which AI model" id="tseg-${pid}">'),
    ('<div class="pair ${pid === "B" ? "wide" : ""}" id="pair-${pid}"></div>',
     '<div class="pair ${m.layout.flatMap(g => g.cols).length > 4 ? "wide" : ""}" id="pair-${pid}"></div>'),
    ("see the published value, all three runs and how far off each was. Grey numbers are not graded because the paper prints no number there.",
     "see the published value, both models' values and how far off each was. Grey numbers are not graded: the paper prints no number there, or the shared data cannot give it."),
    ('<div class="eyebrow">Paper ${pid} · ${esc(m.field)} · Wiley</div>',
     '<div class="eyebrow">Paper ${pid} · ${esc(m.field)} · ${esc(DATA.client)}</div>'),
    ('· Data on Dryad <a href="https://doi.org/${esc(m.dryad)}" target="_blank" rel="noopener">${esc(m.dryad)}</a>',
     '· Data on ${esc(m.data_repo)} <a href="${esc(dataLink(m.data_doi))}" target="_blank" rel="noopener">${esc(m.data_doi)}</a>'),
    ('  <div class="answer">\n    <div class="eyebrow">The answer</div>',
     '  <div class="answer">\n    <div class="sc-controls" style="margin:0 0 10px"><span class="small muted">Results from</span>'
     '<div class="seg" role="group" aria-label="Which AI model" id="mseg-${pid}">${MODELS.map(x => `<button type="button" data-model="${x.id}" '
     'aria-pressed="${x.id === SEL[pid]}">${esc(x.short)}</button>`).join("")}</div></div>\n    <div class="eyebrow">The answer · ${esc(mlabel(SEL[pid]))}</div>'),
    ('<div class="callout"><div class="eyebrow" style="color:var(--accent)">What this means</div><p>${esc(fill(pl.implication, v))}</p></div>',
     '<div class="callout"><div class="eyebrow" style="color:var(--accent)">What this means</div><p>${esc(fill(pl.implication, v))}</p></div>'
     '${pl.model_note ? `<div class="callout" style="margin-top:12px"><div class="eyebrow" style="color:var(--accent)">Opus 5.5 and Sonnet 5.5 on this paper</div><p>${esc(pl.model_note)}</p></div>` : ""}'),
    ("We read all ${totalCalls} commands the three runs made", "We read all ${totalCalls} commands the run made"),
    ("among ${lits} numbers in the three scripts", "among ${lits} numbers in the script"),
    ("Found: <b>${leakIn}</b>.${p.leak.unsearchable.length ?",
     "Found: <b>${leakIn}</b>.${(p.leak.reviewed || []).length ? ` Short numbers that also appear in the Methods wording were checked one by one: ${esc(p.leak.reviewed.join(\"; \"))}.` : \"\"}${p.leak.unsearchable.length ?"),
    ("""  const perRun = runs.map(r => {
    const ok = s.keys.filter(k => ["A", "B"].includes(p.cells[k].runs[r].g)).length;
    return `<li>${RUN_LABEL[r]}: ${ok} of ${s.n} within 20% (${pc(ok, s.n)}%)</li>`;
  }).join("");
  const same = s.keys.filter(k => new Set(p.cells[k].rg).size === 1).length;""",
     """  const perRun = MODELS.map(x => {
    const t = stats(DATA.byModel[x.id][pid]);
    return `<li>${esc(x.label)}: ${t.exact.length} of ${t.n} almost exact (${pc(t.exact.length, t.n)}%), ${t.close.length} within 20% (${pc(t.close.length, t.n)}%)</li>`;
  }).join("");
  const same = s.keys.filter(k => new Set(MODELS.map(x => p.cells[k].runs[x.id].g)).size === 1).length;"""),
    ("<details class=\"more\"><summary>How much the three runs agreed</summary>",
     "<details class=\"more\"><summary>How the two models compare</summary>"),
    ("<p>${same} of ${s.n} numbers got the same result in all three runs.</p>",
     "<p>${same} of ${s.n} numbers got the same grade from both models. One run per model, so a difference can be chance.</p>"),
    ("""  const cost = pid === "A"
    ? `<div class="money"><div><div class="big">About ${money(COST.A.mid)}</div><div class="cap">to check this paper. Estimated range ${range(COST.A)}.</div></div><div><div class="big">${PL.minutes_per_paper} min</div><div class="cap">of AI time once set up.</div></div></div>`
    : `<div class="money"><div><div class="big">About ${money(COST.B_clean.mid)}</div><div class="cap">for one clean pass. Estimated range ${range(COST.B_clean)}.</div></div><div><div class="big">About ${money(COST.B_all.mid)}</div><div class="cap">including our first attempt.</div></div><div><div class="big">${PL.minutes_per_paper} min</div><div class="cap">of AI time per pass once set up.</div></div></div>`;""",
     """  const cst = COST[pid];
  const cost = `<div class="money">${MODELS.map(x => cst[x.id] ? `<div><div class="big">${usd(cst[x.id].at_least)}</div><div class="cap">or more: the ${esc(x.short)} rebuild run</div></div>` : "").join("")}${cst.explainer ? `<div><div class="big">${usd(cst.explainer.at_least)}</div><div class="cap">or more: explaining every difference (Opus 5.5)</div></div>` : ""}</div>`;"""),
    ("Estimated from the AI's token use at published prices. It covers three independent AI runs and the explanation of every difference. Summarising the Methods and building this page were done once and are not included.",
     "From each AI run's own record of tokens used, at published prices. These are lower bounds: the records count input exactly but log most replies with a placeholder output size, so we add the output we can see (code and text); the AI's hidden reasoning cannot be counted. Each rebuild run took 1 to 4 minutes. Summarising the Methods and building this page were done once and are not included."),
    ('${pid === "B" ? `<ul class="glossary"><li><b>Potency (pEC50):</b> a higher number means the drug works at a lower dose.</li><li><b>Biggest effect (Emax):</b> the largest response seen.</li><li><b>Steepness (Hill slope):</b> how sharply the response rises as the dose goes up.</li><li><b>±:</b> the uncertainty the paper gives for each value.</li></ul>` : `<ul class="glossary"><li><b>Size of change (SRM):</b> the average change divided by how much it varies between people.</li><li><b>P value:</b> how likely a change this large is by chance. Marked <sup>a</sup> when below 0.05.</li></ul>`}',
     '${(m.glossary || []).length ? `<ul class="glossary">${m.glossary.map(([t, d]) => `<li><b>${esc(t)}:</b> ${esc(d)}</li>`).join("")}</ul>` : ""}'),
    ('selectTab((location.hash || "").slice(1));',
     """Object.keys(SEL).forEach(pid => { document.getElementById("tab-" + pid).textContent = DATA.papers[pid].meta.tab; });
document.addEventListener("click", e => {
  const b = e.target.closest("[data-model]"); if (!b) return;
  const panel = b.closest(".tabpanel"); if (!panel) return;
  const pid = panel.id.replace("panel-", "");
  if (!(pid in SEL) || SEL[pid] === b.dataset.model) return;
  const open = [...panel.querySelectorAll("details")].map(d => d.open), y = window.scrollY;
  SEL[pid] = b.dataset.model; use(pid); renderPaper(pid); renderMethod();
  panel.querySelectorAll("details").forEach((d, i) => { if (open[i]) d.open = true; });
  window.scrollTo(0, y);
  try { history.replaceState(null, "", "#" + pid + "/" + SEL[pid].replace(/^r_/, "")); } catch (err) {}
});
selectTab((location.hash || "").slice(1).split("/")[0]);"""),
]

LABELS_OLD_START, LABELS_OLD_END = "const COLS = {", "const pubText"
LABELS_NEW = """function cellLabel(p, key) {
  const [rid, cid] = key.split("|");
  const row = p.rows.find(r => r.id === rid), col = p.columns.find(c => c.id === cid);
  return `${row ? row.label : rid}: ${(p.meta.col_labels || {})[cid] || (col ? col.label : cid)}`;
}
"""
TIP_START, TIP_END = "function tipHTML(pid, key) {", "/* ---------- home tab ---------- */"
TIP_NEW = """function tipHTML(pid, key) {
  const p = DATA.papers[pid], c = p.cells[key];
  let rows = `<tr><td>Published</td><td>${esc(pubText(c) || "not printed")}${c.pstars ? " " + esc(c.pstars) : ""}</td><td></td></tr>`;
  for (const m of MODELS) {
    const x = c.runs[m.id];
    const val = x.u != null ? likePub(x.u, c.pub) : roundText(x.raw ?? "—");
    rows += `<tr><td>${esc(m.short)}</td><td>${esc(String(val))}</td><td>${c.graded && x.g ? `<span class="g g${x.g}">${x.g}</span> ${fmtDev(x.d)}` : ""}</td></tr>`;
  }
  if (!c.graded) rows += `<tr><td colspan="3">Not graded: ${esc(c.why_not || "the paper prints no number here")}.</td></tr>`;
  return `<h4>${esc(cellLabel(p, key))}</h4><table>${rows}</table>`;
}

"""
HOME_START, HOME_END = "function renderMethod() {", "/* ---------- paper tab ---------- */"
HOME_NEW = """function renderMethod() {
  const pids = Object.keys(DATA.papers);
  const card = pid => {
    const p = DATA.papers[pid], s = stats(p), v = vars(pid);
    const bar = (lab, n) => `<div class="mb"><span>${lab}</span><span class="track"><span class="fill" style="width:${pc(n, s.n)}%;display:block"></span></span><span class="p">${pc(n, s.n)}%</span></div>`;
    const other = MODELS.filter(x => x.id !== SEL[pid]).map(x => { const t = stats(DATA.byModel[x.id][pid]); return `${esc(x.short)}: ${pc(t.exact.length, t.n)}% almost exact, ${pc(t.close.length, t.n)}% within 20%`; }).join("; ");
    return `<button class="sheet pcard stack" data-go="${pid}">
      <div class="eyebrow">Paper ${pid} · ${esc(p.meta.field)}</div>
      <h3>${esc(PL.papers[pid].short)}</h3>
      <div class="muted small"><i>${esc(p.meta.journal)}</i>. ${s.n} numbers checked.</div>
      <p style="margin:0;font:600 18px/1.4 var(--serif)">${esc(fill(PL.papers[pid].verdict, v))}</p>
      <div class="small muted">${esc(mlabel(SEL[pid]))}:</div>
      <div class="minibars" style="margin-top:0">${bar("Almost exactly right", s.exact.length)}${bar("Within 20%", s.close.length)}${bar("Same direction", s.sign.length)}</div>
      <div class="small muted">${other}</div>
      <div class="small muted">About ${usd(paperCost(pid, SEL[pid]))} or more to check · see the details</div>
    </button>`;
  };
  const costs = pids.map(pid => `<div><div class="big">${usd(paperCost(pid, MODELS[0].id))}</div><div class="cap">or more to check Paper ${pid} with ${esc(MODELS[0].short)} (the ${esc(MODELS[1].short)} run adds ${usd(COST[pid][MODELS[1].id] ? COST[pid][MODELS[1].id].at_least : 0)})</div></div>`).join("");
  document.getElementById("panel-method").innerHTML = `
  <div class="hero">
    <div class="eyebrow">Reproducibility check</div>
    <h1>Can a paper's results be rebuilt from its Methods?</h1>
    <p class="lead">We gave an AI only the written Methods and the data a paper shares. It had to rebuild one results table without seeing the paper, its results or its code. Then we compared every number with the published one. Each paper was rebuilt twice: once by Claude Opus 5.5 and once by Claude Sonnet 5.5.</p>
  </div>
  <section class="band">
    <h2>Two ${esc(DATA.client)} papers <span class="sub">select a paper for the full picture</span></h2>
    <div class="grid2" style="margin-top:14px">${pids.map(card).join("")}</div>
  </section>
  <section class="band">
    <h2>How it works</h2>
    <div class="flow" aria-label="Steps">
      <div class="step"><div class="n">1</div><h3>Summarise</h3><p>We turn the Methods into a checklist, each point with the sentence it came from. We also blank out the results table.</p></div>
      <div class="step"><div class="n">2</div><h3>Rebuild</h3><p>An AI sees only the checklist, the blank table and the shared data. It writes code to fill the table. Two different AI models each do this once, from scratch.</p></div>
      <div class="step"><div class="n">3</div><h3>Compare</h3><p>A fixed script compares each number with the published one. No AI is involved in the marking.</p></div>
      <div class="step"><div class="n">4</div><h3>Explain</h3><p>For each number that differs, an AI finds the reason. It then tests whether a different reading of the Methods fixes it.</p></div>
    </div>
  </section>
  <section class="band grid2">
    <div class="sheet prose">
      <h3>What a publisher could do with this</h3>
      <p>Run the check when an author submits data with a paper. The editor gets a short report. It says which results the data reproduce, and which sentences in the Methods left the AI guessing. Each comes with a suggested fix.</p>
      <p>Run it over a whole journal archive to see how complete the Methods are, journal by journal.</p>
      <p>It flags issues for editors. It does not judge papers. A mismatch usually means the Methods left a choice open, not that a result is wrong.</p>
    </div>
    <div class="sheet prose">
      <h3>What it cost</h3>
      <div class="money">${costs}</div>
      <p class="small muted">Each figure covers one AI rebuild and the explanation of every difference. A rebuild takes 1 to 4 minutes of AI time. These are lower bounds from each run's own token record at published prices: the hidden reasoning tokens cannot be counted. Building the pipeline and this page was a one-off and is not included.</p>
      <p class="small muted">The rebuilds were done by Claude Opus 5.5 and Claude Sonnet 5.5; the explanations by Claude Opus 5.5. Each rebuild worked in its own folder with only the Methods and the data. We checked afterwards that none saw the answers.</p>
    </div>
  </section>
  <section class="band">
    <div class="sheet prose">
      <h3>Limits</h3>
      <ul class="caveats small">
        <li>Two papers and two tables. This shows the method works. It is not a measure of how common the problems are.</li>
        <li>One run per model. Where Opus and Sonnet differ, it can be chance: the same model can choose differently on another run. The page shows both, not the better one.</li>
        <li>The explanations of why numbers differ are AI judgements. We tested each by re-running a different reading of the Methods, but no human reviewer has checked them yet.</li>
        <li>Neither paper shared its analysis code, so we cannot see what the authors actually ran.</li>
        <li>The publisher's name says whose papers were used. This page is not produced by or for the publisher.</li>
      </ul>
    </div>
  </section>`;
  document.querySelectorAll("[data-go]").forEach(b => b.addEventListener("click", () => selectTab(b.dataset.go)));
}

"""


def splice(s, start, end, new):
    a, b = s.index(start), s.index(end)
    assert a < b and s.count(start) == 1, start
    return s[:a] + new + s[b:]


def main(src, out):
    s = Path(src).read_text(encoding="utf-8")
    for old, new in REPLACEMENTS:
        assert s.count(old) == 1, f"expected exactly one match for: {old[:80]!r}"
        s = s.replace(old, new)
    s = splice(s, LABELS_OLD_START, LABELS_OLD_END, LABELS_NEW)
    s = splice(s, TIP_START, TIP_END, TIP_NEW)
    s = splice(s, HOME_START, HOME_END, HOME_NEW)
    Path(out).write_text(s, encoding="utf-8")
    print("wrote", out)


if __name__ == "__main__":
    main(*sys.argv[1:])
