import argparse
import base64
import html
import io
import json
import os
import re
import sys
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image

from ark_service import BRAND_PATH, configure_console, load_brand, load_config

configure_console()


def image_src(path: Path, out_dir: Path, embed: bool, max_side: int, image_dir: Path | None = None) -> str | None:
    """How the page references one render: inline base64 (--embed), a compressed JPEG copy in
    --image-dir (for publishing as a small static site), or a relative link to the original."""
    if not path.exists():
        return None
    if not embed and image_dir is None:
        return urllib.parse.quote(Path(os.path.relpath(path, out_dir)).as_posix())
    img = Image.open(path).convert("RGB")
    img.thumbnail((max_side, max_side))
    if image_dir is not None:
        image_dir.mkdir(parents=True, exist_ok=True)
        dest = image_dir / (path.stem + ".jpg")
        img.save(dest, "JPEG", quality=85, optimize=True, progressive=True)
        return urllib.parse.quote(Path(os.path.relpath(dest, out_dir)).as_posix())
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=85, optimize=True)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


def aspect_of(config: dict, fmt: str | None) -> str:
    """CSS aspect-ratio for an asset's frame, from its config.json format ("2048x2048" → "2048 / 2048")."""
    size = (config.get("image_formats") or {}).get(fmt or "", "")
    m = re.fullmatch(r"(\d+)x(\d+)", size)
    return f"{m.group(1)} / {m.group(2)}" if m else "4 / 3"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build the static evaluation page for the design-idea set: every idea's logo, "
                    "brand story graphic and business card side by side, with a weighted 1–5 "
                    "scoring system (criteria + weights from config.json evaluation_criteria), "
                    "a live leaderboard, notes, "
                    "shortlisting and JSON/CSV export. Local, free; scores are saved in the "
                    "viewer's browser and exported as a file."
    )
    parser.add_argument("--brand",    default=str(BRAND_PATH), help="Path to brand.json (defaults to _project/brand/brand.json)")
    parser.add_argument("--output",   default=None, help="Output HTML (default: <project>/output/evaluation.html)")
    parser.add_argument("--embed",    action="store_true", help="Inline images as compressed JPEGs so the page is one shareable file")
    parser.add_argument("--image-dir", default=None, help="Write compressed JPEG copies here and link them (static-site publishing, e.g. <site>/img)")
    parser.add_argument("--max-side", type=int, default=1600, help="Longest side of embedded images, px")
    args = parser.parse_args()

    brand_path = Path(args.brand).resolve()
    project    = brand_path.parent.parent
    out_path   = Path(args.output).resolve() if args.output else project / "output" / "evaluation.html"
    out_dir    = out_path.parent
    src_dir    = project / "output"

    try:
        config   = load_config()
        brand    = load_brand(brand_path)
        criteria = config["evaluation_criteria"]
        assets   = [{"id": a["id"], "label": a["label"], "aspect": aspect_of(config, a.get("format"))}
                    for a in config["design_set"]["assets"]]
        if not brand.get("ideas"):
            raise ValueError("brand.json has no ideas")
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    missing, ideas = [], []
    for idea in brand["ideas"]:
        images = {}
        for a in assets:
            p = src_dir / f"idea{idea['id']}_{a['id']}.png"
            images[a["id"]] = image_src(p, out_dir, args.embed, args.max_side,
                                        Path(args.image_dir).resolve() if args.image_dir else None)
            if images[a["id"]] is None:
                missing.append(p.name)
        story = idea.get("story") if isinstance(idea.get("story"), dict) else {}
        ideas.append({
            "id":          idea["id"],
            "title":       idea.get("title", f"Idea {idea['id']}"),
            "summary":     idea.get("summary", ""),
            "rationale":   idea.get("rationale", ""),
            "style":       idea.get("style", ""),
            "tagline":     idea.get("tagline", ""),
            "personality": idea.get("personality") or [],
            "palette":     [{"name": c.get("name", ""), "hex": c["hex"].upper(), "role": c.get("role", "")} for c in idea.get("palette") or []],
            "typography":  idea.get("typography") or {},
            "logo":        (idea.get("logo") or {}).get("description", ""),
            "story":       story.get("narrative") or story.get("headline", ""),
            "images":      images,
        })

    company = {k: brand.get(k, "") for k in ("name", "industry", "business_type", "business_idea", "audience")}
    data = {
        "company":     company,
        "criteria":    criteria,
        "assets":      assets,
        "ideas":       ideas,
        "storageKey":  "vid-eval:" + re.sub(r"\W+", "-", company["name"].lower()).strip("-"),
        "generatedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    page = PAGE.replace("__TITLE__", html.escape(f"{company['name']} — Design Evaluation")).replace("__DATA__", payload)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(page, encoding="utf-8")
    if missing:
        print(f"Warning: {len(missing)} image(s) not generated yet, shown as placeholders: {', '.join(missing)}", file=sys.stderr)
    print(str(out_path))
    return 0


PAGE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title>
<style>
  :root {
    --bg: #F6F5F1; --panel: #FFFFFF; --ink: #17171A; --muted: #6A6A70; --line: #E3E1DA;
    --accent: #2F5BEA; --accent-soft: #E6ECFD; --good: #1F8A55; --warn: #B4531A;
    --radius: 10px;
  }
  @media (prefers-color-scheme: dark) {
    :root:not([data-theme="light"]) {
      --bg: #121214; --panel: #1C1C20; --ink: #ECECEF; --muted: #9A9AA3; --line: #2E2E34;
      --accent: #7B9BFF; --accent-soft: #232B45; --good: #4CC48A; --warn: #F0995F;
    }
  }
  * { box-sizing: border-box; }
  body { margin: 0; background: var(--bg); color: var(--ink);
         font: 15px/1.55 ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; }
  .wrap { max-width: 1240px; margin: 0 auto; padding: 0 16px; }
  header.top { padding: 40px 0 24px; }
  .eyebrow { font-size: 12px; letter-spacing: .14em; text-transform: uppercase; color: var(--muted); }
  h1 { font-size: clamp(28px, 4vw, 44px); line-height: 1.1; margin: 6px 0 10px; letter-spacing: -.01em; }
  .meta { display: flex; flex-wrap: wrap; gap: 8px 20px; color: var(--muted); }
  .meta b { color: var(--ink); font-weight: 600; }
  .toolbar { position: sticky; top: 0; z-index: 5; background: color-mix(in srgb, var(--bg) 92%, transparent);
             backdrop-filter: blur(8px); border-bottom: 1px solid var(--line); }
  .toolbar .wrap { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; padding-top: 10px; padding-bottom: 10px; }
  .toolbar label { color: var(--muted); font-size: 13px; }
  input[type=text], textarea { font: inherit; color: var(--ink); background: var(--panel); border: 1px solid var(--line);
                               border-radius: 8px; padding: 7px 10px; }
  .toolbar input { width: 180px; }
  .spacer { flex: 1; }
  button { font: inherit; font-size: 13px; color: var(--ink); background: var(--panel); border: 1px solid var(--line);
           border-radius: 8px; padding: 7px 12px; cursor: pointer; }
  button:hover { border-color: var(--muted); }
  button.primary { background: var(--accent); border-color: var(--accent); color: #fff; }
  section.panel { background: var(--panel); border: 1px solid var(--line); border-radius: var(--radius); padding: 20px; margin: 20px 0; }
  h2 { font-size: 20px; margin: 0 0 12px; }
  h3 { font-size: 14px; margin: 0 0 8px; color: var(--muted); font-weight: 600; text-transform: uppercase; letter-spacing: .08em; }
  details summary { cursor: pointer; font-weight: 600; }
  table { width: 100%; border-collapse: collapse; font-size: 14px; }
  th, td { text-align: left; padding: 8px 10px; border-bottom: 1px solid var(--line); vertical-align: top; }
  th { color: var(--muted); font-weight: 600; font-size: 12px; text-transform: uppercase; letter-spacing: .06em; }
  .num { font-variant-numeric: tabular-nums; }
  /* leaderboard */
  .board { display: grid; gap: 10px; }
  .row { display: grid; grid-template-columns: 28px minmax(120px, 220px) 1fr 120px; gap: 12px; align-items: center; }
  .rank { font-weight: 700; color: var(--muted); }
  .row a { color: var(--ink); text-decoration: none; font-weight: 600; }
  .bar { position: relative; height: 12px; background: var(--accent-soft); border-radius: 99px; overflow: visible; }
  .bar > span { position: absolute; inset: 0 auto 0 0; background: var(--accent); border-radius: 99px; }
  .score-label { text-align: right; font-variant-numeric: tabular-nums; }
  .score-label small { display: block; color: var(--muted); font-size: 12px; }
  /* idea */
  article.idea { background: var(--panel); border: 1px solid var(--line); border-radius: var(--radius); margin: 24px 0; overflow: hidden; scroll-margin-top: 64px; }
  article.idea.shortlisted { border-color: var(--good); box-shadow: 0 0 0 2px color-mix(in srgb, var(--good) 30%, transparent); }
  .idea-head { display: flex; flex-wrap: wrap; gap: 12px; align-items: flex-start; justify-content: space-between; padding: 20px 20px 0; }
  .idea-head h2 { margin: 2px 0 4px; font-size: 24px; }
  .idea-head .sub { color: var(--muted); max-width: 70ch; }
  .total { text-align: right; min-width: 140px; }
  .total .big { font-size: 34px; font-weight: 700; line-height: 1; font-variant-numeric: tabular-nums; }
  .total small { color: var(--muted); font-size: 12px; display: block; margin-top: 4px; }
  .gallery { display: grid; grid-template-columns: 1fr 1.6fr 1.4fr; gap: 12px; padding: 20px; align-items: start; }
  figure { margin: 0; }
  figure .frame { background: var(--bg); border: 1px solid var(--line); border-radius: 8px; overflow: hidden;
                  aspect-ratio: 4 / 3; display: grid; place-items: center; cursor: zoom-in; }
  figure img { width: 100%; height: 100%; object-fit: contain; display: block; }
  figure .missing { color: var(--muted); font-size: 13px; padding: 12px; text-align: center; cursor: default; }
  figcaption { font-size: 12px; color: var(--muted); margin-top: 6px; }
  .details { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; padding: 0 20px 20px; }
  .chips { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 10px; }
  .chip { display: inline-flex; align-items: center; gap: 6px; font-size: 12px; border: 1px solid var(--line); border-radius: 99px; padding: 3px 10px 3px 4px; }
  .chip i { width: 16px; height: 16px; border-radius: 50%; border: 1px solid rgba(0,0,0,.12); display: inline-block; }
  .tag { font-size: 12px; background: var(--accent-soft); color: var(--ink); border-radius: 99px; padding: 2px 10px; }
  .kv { font-size: 14px; margin: 0 0 6px; } .kv b { color: var(--muted); font-weight: 600; margin-right: 6px; }
  /* scoring */
  .scoring { border-top: 1px solid var(--line); padding: 16px 20px 20px; }
  .crit { display: grid; grid-template-columns: minmax(160px, 1fr) auto; gap: 8px 16px; align-items: center; padding: 8px 0; border-bottom: 1px dashed var(--line); }
  .crit:last-of-type { border-bottom: 0; }
  .crit .name { font-weight: 600; } .crit .name small { color: var(--muted); font-weight: 400; margin-left: 6px; }
  .crit .desc { color: var(--muted); font-size: 13px; }
  .pips { display: flex; gap: 6px; }
  .pip { position: relative; width: 40px; height: 36px; padding: 0; font-weight: 600; font-variant-numeric: tabular-nums; }
  .pip[aria-pressed="true"] { background: var(--accent); border-color: var(--accent); color: #fff; }
  .idea-foot { display: flex; flex-wrap: wrap; gap: 12px; align-items: flex-start; margin-top: 14px; }
  .idea-foot textarea { flex: 1; min-width: 240px; min-height: 64px; resize: vertical; }
  .shortlist[aria-pressed="true"] { background: var(--good); border-color: var(--good); color: #fff; }
  /* lightbox */
  .lightbox { position: fixed; inset: 0; background: rgba(10,10,12,.92); display: none; z-index: 20; place-items: center; padding: 24px; }
  .lightbox.open { display: grid; }
  .lightbox img { max-width: 100%; max-height: 86vh; border-radius: 6px; }
  .lightbox p { color: #ddd; text-align: center; margin: 10px 0 0; font-size: 14px; }
  .lightbox button { position: absolute; top: 16px; right: 16px; }
  footer { color: var(--muted); font-size: 12px; padding: 24px 0 48px; }
  @media (max-width: 860px) {
    .gallery, .details { grid-template-columns: 1fr; }
    .row { grid-template-columns: 24px 1fr 80px; } .row .bar { grid-column: 2 / 4; grid-row: 2; }
    .crit { grid-template-columns: 1fr; }
  }
  @media print {
    .toolbar, .lightbox, button:not(.pip) { display: none !important; }
    article.idea { break-inside: avoid-page; }
    body { background: #fff; }
  }
</style>
</head>
<body>
<header class="top wrap">
  <div class="eyebrow">Brand design evaluation</div>
  <h1 id="title"></h1>
  <div class="meta" id="meta"></div>
</header>

<div class="toolbar"><div class="wrap">
  <label for="reviewer">Reviewer</label><input id="reviewer" type="text" placeholder="Your name">
  <span class="spacer"></span>
  <button id="exportJson" class="primary">Export scores (JSON)</button>
  <button id="exportCsv">Export CSV</button>
  <button id="importBtn">Import</button><input id="importFile" type="file" accept="application/json" hidden>
  <button id="reset">Reset</button>
</div></div>

<main class="wrap">
  <section class="panel">
    <h2>Leaderboard</h2>
    <div class="board" id="board"></div>
  </section>

  <section class="panel">
    <details>
      <summary>How scoring works</summary>
      <p>Rate each design 1–5 on every criterion (1 poor · 2 weak · 3 acceptable · 4 strong · 5 excellent). Click a score again to clear it. Scores are weighted into a total out of 100. Your scores are saved in this browser. Use <b>Export scores</b> to share them.</p>
      <table><thead><tr><th>Criterion</th><th class="num">Weight</th><th>What to look for</th></tr></thead><tbody id="critTable"></tbody></table>
    </details>
  </section>

  <div id="ideas"></div>
</main>

<div class="lightbox" id="lightbox" role="dialog" aria-modal="true"><button id="lbClose">Close (Esc)</button><div><img id="lbImg" alt=""><p id="lbCap"></p></div></div>

<footer class="wrap" id="foot"></footer>

<script>
const DATA = __DATA__;
const C = DATA.criteria, TOTAL_W = C.reduce((s, c) => s + c.weight, 0);
const $ = (s, el = document) => el.querySelector(s);
const esc = s => String(s ?? "").replace(/[&<>"']/g, ch => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[ch]));

let state = { reviewer: "", ideas: {} };
try { const saved = JSON.parse(localStorage.getItem(DATA.storageKey) || "null"); if (saved && saved.ideas) state = saved; } catch (e) {}
const save = () => { try { localStorage.setItem(DATA.storageKey, JSON.stringify(state)); } catch (e) {} };
const ideaState = id => (state.ideas[id] ||= { scores: {}, notes: "", shortlisted: false });

function totalOf(scores) {
  let pts = 0, n = 0;
  for (const c of C) { const v = scores?.[c.id]; if (v) { pts += c.weight * v / 5; n++; } }
  return { score: Math.round(pts * 100 / TOTAL_W), scored: n };
}

function renderHeader() {
  const co = DATA.company;
  $("#title").textContent = co.name;
  $("#meta").innerHTML = [["Industry", co.industry], ["Business type", co.business_type], ["Idea", co.business_idea], ["Audience", co.audience]]
    .filter(([, v]) => v).map(([k, v]) => `<span>${k}: <b>${esc(v)}</b></span>`).join("");
  $("#critTable").innerHTML = C.map(c => `<tr><td><b>${esc(c.label)}</b></td><td class="num">${c.weight}</td><td>${esc(c.description)}</td></tr>`).join("");
  $("#foot").textContent = `${DATA.ideas.length} design ideas · generated ${DATA.generatedAt} · images by Seedream 5.0 Pro. Generated logos are concepts: they need a trademark check and a vector redraw before production use.`;
  $("#reviewer").value = state.reviewer || "";
}

function renderBoard() {
  const rows = DATA.ideas.map(i => ({ i, me: totalOf(ideaState(i.id).scores) }))
    .sort((a, b) => b.me.score - a.me.score);
  $("#board").innerHTML = rows.map((r, k) => `
    <div class="row">
      <span class="rank">${k + 1}</span>
      <a href="#idea-${esc(r.i.id)}">${ideaState(r.i.id).shortlisted ? "★ " : ""}${esc(r.i.title)}</a>
      <div class="bar" title="Your score ${r.me.score}">
        <span style="width:${r.me.score}%"></span>
      </div>
      <div class="score-label"><b>${r.me.score}</b> / 100<small>${r.me.scored}/${C.length} scored</small></div>
    </div>`).join("");
}

function renderIdeas() {
  $("#ideas").innerHTML = DATA.ideas.map(i => {
    const st = ideaState(i.id);
    const gallery = DATA.assets.map(a => {
      const src = i.images[a.id];
      return `<figure><div class="frame" style="aspect-ratio:${a.aspect}">${src ? `<img src="${src}" alt="${esc(i.title)}, ${esc(a.label)}" data-cap="${esc(i.title)}: ${esc(a.label)}" loading="lazy">`
        : `<div class="missing">${esc(a.label)}<br>not generated yet</div>`}</div><figcaption>${esc(a.label)}</figcaption></figure>`;
    }).join("");
    const palette = i.palette.map(p => `<span class="chip" title="${esc(p.role)}"><i style="background:${esc(p.hex)}"></i>${esc(p.name)} <span class="num">${esc(p.hex)}</span></span>`).join("");
    const traits = i.personality.map(t => `<span class="tag">${esc(t)}</span>`).join("");
    const crits = C.map(c => {
      const mine = st.scores[c.id];
      const pips = [1,2,3,4,5].map(v => `<button class="pip" data-idea="${esc(i.id)}" data-crit="${c.id}" data-v="${v}" aria-pressed="${mine === v}" aria-label="${esc(c.label)} ${v}">${v}</button>`).join("");
      return `<div class="crit"><div><div class="name">${esc(c.label)}<small>×${c.weight}</small></div><div class="desc">${esc(c.description)}</div></div><div class="pips">${pips}</div></div>`;
    }).join("");
    const t = totalOf(st.scores);
    return `
    <article class="idea${st.shortlisted ? " shortlisted" : ""}" id="idea-${esc(i.id)}">
      <div class="idea-head">
        <div><div class="eyebrow">Idea ${esc(i.id)}${i.style ? " · " + esc(i.style) : ""}</div><h2>${esc(i.title)}</h2><div class="sub">${esc(i.summary)}</div></div>
        <div class="total"><div class="big" data-total="${esc(i.id)}">${t.score}</div><small data-scored="${esc(i.id)}">of 100 · ${t.scored}/${C.length} scored</small></div>
      </div>
      <div class="gallery">${gallery}</div>
      <div class="details">
        <div>
          <h3>Concept</h3>
          ${i.tagline ? `<p class="kv"><b>Tagline</b>“${esc(i.tagline)}”</p>` : ""}
          ${i.logo ? `<p class="kv"><b>Logo</b>${esc(i.logo)}</p>` : ""}
          ${i.story ? `<p class="kv"><b>Story</b>${esc(i.story)}</p>` : ""}
          ${i.rationale ? `<p class="kv"><b>Why</b>${esc(i.rationale)}</p>` : ""}
          <div class="chips">${traits}</div>
        </div>
        <div>
          <h3>Palette &amp; type</h3>
          <div class="chips">${palette}</div>
          ${i.typography.display || i.typography.body ? `<p class="kv"><b>Type</b>${esc([i.typography.display, i.typography.body].filter(Boolean).join(" + "))}${i.typography.feel ? " · " + esc(i.typography.feel) : ""}</p>` : ""}
        </div>
      </div>
      <div class="scoring">
        <h3>Your scores</h3>
        ${crits}
        <div class="idea-foot">
          <textarea data-notes="${esc(i.id)}" placeholder="Notes: what works, what to change">${esc(st.notes)}</textarea>
          <button class="shortlist" data-short="${esc(i.id)}" aria-pressed="${st.shortlisted}">${st.shortlisted ? "★ Shortlisted" : "☆ Shortlist"}</button>
        </div>
      </div>
    </article>`;
  }).join("");
}

function refreshTotals(id) {
  const t = totalOf(ideaState(id).scores);
  $(`[data-total="${CSS.escape(String(id))}"]`).textContent = t.score;
  $(`[data-scored="${CSS.escape(String(id))}"]`).textContent = `of 100 · ${t.scored}/${C.length} scored`;
  renderBoard();
}

document.addEventListener("click", e => {
  const pip = e.target.closest(".pip");
  if (pip) {
    const st = ideaState(pip.dataset.idea), v = +pip.dataset.v;
    st.scores[pip.dataset.crit] = st.scores[pip.dataset.crit] === v ? undefined : v;
    pip.parentElement.querySelectorAll(".pip").forEach(b => b.setAttribute("aria-pressed", String(+b.dataset.v === st.scores[pip.dataset.crit])));
    save(); refreshTotals(pip.dataset.idea); return;
  }
  const sh = e.target.closest("[data-short]");
  if (sh) {
    const st = ideaState(sh.dataset.short); st.shortlisted = !st.shortlisted; save();
    sh.setAttribute("aria-pressed", String(st.shortlisted)); sh.textContent = st.shortlisted ? "★ Shortlisted" : "☆ Shortlist";
    sh.closest("article").classList.toggle("shortlisted", st.shortlisted); renderBoard(); return;
  }
  const img = e.target.closest(".frame img");
  if (img) { $("#lbImg").src = img.src; $("#lbCap").textContent = img.dataset.cap; $("#lightbox").classList.add("open"); return; }
  if (e.target.id === "lightbox" || e.target.id === "lbClose") $("#lightbox").classList.remove("open");
});
document.addEventListener("keydown", e => { if (e.key === "Escape") $("#lightbox").classList.remove("open"); });
document.addEventListener("input", e => {
  if (e.target.dataset.notes) { ideaState(e.target.dataset.notes).notes = e.target.value; save(); }
  if (e.target.id === "reviewer") { state.reviewer = e.target.value; save(); }
});

function exportObj() {
  return {
    company: DATA.company.name, reviewer: state.reviewer, exported_at: new Date().toISOString(),
    criteria: C.map(c => ({ id: c.id, label: c.label, weight: c.weight })),
    ideas: DATA.ideas.map(i => { const st = ideaState(i.id), t = totalOf(st.scores);
      return { id: i.id, title: i.title, scores: st.scores, total: t.score, scored: t.scored, notes: st.notes, shortlisted: st.shortlisted }; })
      .sort((a, b) => b.total - a.total),
  };
}
function download(name, text, type) {
  const a = document.createElement("a"); a.href = URL.createObjectURL(new Blob([text], { type })); a.download = name; a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 1000);
}
const fileBase = () => `${DATA.storageKey.replace("vid-eval:", "")}_scores${state.reviewer ? "_" + state.reviewer.replace(/\W+/g, "-") : ""}`;
$("#exportJson").onclick = () => download(fileBase() + ".json", JSON.stringify(exportObj(), null, 2), "application/json");
$("#exportCsv").onclick = () => {
  const q = v => `"${String(v ?? "").replace(/"/g, '""')}"`;
  const head = ["id", "title", ...C.map(c => c.label), "total", "shortlisted", "notes"];
  const rows = exportObj().ideas.map(i => [i.id, i.title, ...C.map(c => i.scores[c.id] ?? ""), i.total, i.shortlisted, i.notes]);
  download(fileBase() + ".csv", [head, ...rows].map(r => r.map(q).join(",")).join("\n"), "text/csv");
};
$("#importBtn").onclick = () => $("#importFile").click();
$("#importFile").onchange = async e => {
  try {
    const obj = JSON.parse(await e.target.files[0].text());
    state = { reviewer: obj.reviewer || "", ideas: {} };
    for (const i of obj.ideas || []) state.ideas[i.id] = { scores: i.scores || {}, notes: i.notes || "", shortlisted: !!i.shortlisted };
    save(); renderAll();
  } catch (err) { alert("Couldn't read that file: " + err.message); }
  e.target.value = "";
};
$("#reset").onclick = () => { if (confirm("Clear all your scores, notes and shortlist?")) { state = { reviewer: state.reviewer, ideas: {} }; save(); renderAll(); } };

function renderAll() { renderHeader(); renderIdeas(); renderBoard(); }
renderAll();
</script>
</body>
</html>
"""


if __name__ == "__main__":
    raise SystemExit(main())
