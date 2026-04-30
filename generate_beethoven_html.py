#!/usr/bin/env python3
"""Generate self-contained HTML report for Beethoven symphonies from beethoven.db."""

import sqlite3, os

DB  = os.path.join(os.path.dirname(os.path.abspath(__file__)), "beethoven.db")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "beethoven.html")

def fmt_duration(mins):
    m = int(mins); s = int(round((mins - m) * 60))
    return f"{m}′" if s == 0 else f"{m}′{s:02d}″"

def bar_width(dur, max_dur):
    return max(4, int(dur / max_dur * 100))

# Warm amber/parchment palette — distinct from Mahler's cool steel tones
CAT_ORDER  = ["Woodwind","Brass","Percussion","Strings","Voice"]
CAT_COLORS = {
    "Woodwind":   "#6bba80",
    "Brass":      "#d4841a",
    "Percussion": "#b85040",
    "Strings":    "#90b840",
    "Voice":      "#b870a0",
}

# Key-inspired hues per symphony (musically motivated)
# C=0°, D=40°, Eb=160°, Bb=200°, Cm=320°, F=90°, A=30°, F=90°, Dm=260°
SYMPHONY_HUES = {1:0, 2:40, 3:160, 4:200, 5:320, 6:90, 7:30, 8:90, 9:260}

conn = sqlite3.connect(DB); conn.row_factory = sqlite3.Row
symphonies = conn.execute("SELECT * FROM symphonies ORDER BY number").fetchall()

mvt_map, inst_map = {}, {}
for s in symphonies:
    sid = s["id"]
    mvt_map[sid]  = conn.execute(
        "SELECT * FROM movements WHERE symphony_id=? ORDER BY number", (sid,)).fetchall()
    rows = conn.execute(
        """SELECT ic.name cat, inst.name instrument, si.count, si.notes
           FROM symphony_instruments si
           JOIN instruments inst ON inst.id=si.instrument_id
           JOIN instrument_categories ic ON ic.id=inst.category_id
           WHERE si.symphony_id=? ORDER BY ic.id, inst.id""", (sid,)).fetchall()
    grouped = {}
    for r in rows: grouped.setdefault(r["cat"], []).append(r)
    inst_map[sid] = grouped
conn.close()

ROMANS = ["","I","II","III","IV","V","VI","VII","VIII","IX"]

def render_symphony(s):
    sid      = s["id"]
    mvts     = mvt_map[sid]
    inst_grps= inst_map[sid]
    max_dur  = max(m["duration_min"] for m in mvts)
    roman    = ROMANS[s["number"]]
    hue      = SYMPHONY_HUES[s["number"]]

    subtitle_html = (f'<span class="subtitle">"{s["subtitle"]}"</span>'
                     if s["subtitle"] else "")

    mvt_rows = ""
    for m in mvts:
        label   = f'<span class="mvt-label">{m["label"]}</span> ' if m["label"] else ""
        voices  = f'<div class="mvt-voices">{m["voices"]}</div>' if m["voices"] else ""
        tip     = f' title="{m["notes"]}"' if m["notes"] else ""
        bw      = bar_width(m["duration_min"], max_dur)
        mvt_rows += f"""
        <tr{tip}>
          <td class="mvt-num">{roman}.{m["number"]}</td>
          <td class="mvt-tempo">{label}{m["tempo_marking"]}{voices}</td>
          <td class="mvt-dur">{fmt_duration(m["duration_min"])}</td>
          <td class="mvt-bar-cell">
            <div class="mvt-bar" style="width:{bw}%; background:hsla({hue},55%,55%,0.7)"></div>
          </td>
        </tr>"""

    inst_html = ""
    for cat in CAT_ORDER:
        if cat not in inst_grps: continue
        color = CAT_COLORS[cat]
        pills = ""
        for r in inst_grps[cat]:
            cnt  = f"×{r['count']}" if r["count"] else ""
            tip  = f' title="{r["notes"]}"' if r["notes"] else ""
            pills += (f'<span class="pill" style="--pill-color:{color}"{tip}>'
                      f'{r["instrument"]}'
                      f'{(" <em>"+cnt+"</em>") if cnt else ""}'
                      f'</span>')
        inst_html += f"""
        <div class="inst-group">
          <span class="inst-cat" style="color:{color}">{cat}</span>
          <div class="pills">{pills}</div>
        </div>"""

    notes_html = f'<p class="sym-note">{s["notes"]}</p>' if s["notes"] else ""
    opus_tag   = f'<span class="tag opus-tag">{s["opus"]}</span>'

    return f"""
  <section class="sym-card" id="sym{s['number']}" style="--hue:{hue}">
    <header class="sym-header">
      <div class="sym-numeral">{roman}</div>
      <div class="sym-meta">
        <h2>Symphony No.&nbsp;{s['number']} <span class="in-key">in {s['key']}</span>
          {subtitle_html}</h2>
        <div class="sym-tags">
          {opus_tag}
          <span class="tag">&#9836; {s['year_composed']}</span>
          <span class="tag">Premiere: {s['year_premiered']}</span>
          <span class="tag total-time">Total: {fmt_duration(s['total_duration_min'])}</span>
        </div>
      </div>
    </header>
    {notes_html}
    <div class="sym-body">
      <div class="panel movements-panel">
        <h3 class="panel-title">Movements</h3>
        <table class="mvt-table"><tbody>{mvt_rows}
        </tbody></table>
      </div>
      <div class="panel inst-panel">
        <h3 class="panel-title">Instrumentation</h3>
        {inst_html}
      </div>
    </div>
  </section>"""

cards     = "\n".join(render_symphony(s) for s in symphonies)
nav_links = " ".join(
    f'<a href="#sym{s["number"]}">{ROMANS[s["number"]]}</a>' for s in symphonies)

html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Ludwig van Beethoven — Complete Symphonies</title>
<style>
/* ── Reset ─────────────────────────────────────────────────── */
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}

:root {{
  /* Warm parchment-dark palette — distinct from Mahler's cool steel */
  --bg:          #0d0a06;
  --bg2:         #161009;
  --bg3:         #20180e;
  --border:      #362a18;
  --text:        #e2d4b8;
  --text-dim:    #8a7255;
  --text-bright: #f5ead2;
  --accent:      #d4901c;
  --radius:      12px;
  --font-serif:  'Georgia','Times New Roman',serif;
  --font-sans:   'Segoe UI',system-ui,sans-serif;
}}

html{{scroll-behavior:smooth}}
body{{background:var(--bg);color:var(--text);font-family:var(--font-sans);font-size:14px;line-height:1.6}}

/* ── Nav ────────────────────────────────────────────────────── */
.site-nav{{
  position:sticky;top:0;z-index:100;
  background:rgba(13,10,6,0.92);
  backdrop-filter:blur(10px);
  border-bottom:1px solid var(--border);
  display:flex;align-items:center;gap:1rem;
  padding:0.55rem 2rem;
}}
.site-nav .brand{{
  font-family:var(--font-serif);font-size:1rem;
  color:var(--accent);white-space:nowrap;margin-right:auto;
}}
.site-nav a{{
  color:var(--text-dim);text-decoration:none;font-size:0.85rem;
  font-weight:600;padding:0.25rem 0.5rem;border-radius:6px;
  transition:background 0.15s,color 0.15s;
}}
.site-nav a:hover{{background:var(--bg3);color:var(--accent)}}
.site-nav .back-link{{
  font-size:0.8rem;color:var(--text-dim);
  border:1px solid var(--border);border-radius:6px;
  padding:0.2rem 0.6rem;margin-left:auto;
}}
.site-nav .back-link:hover{{background:var(--bg3);color:var(--accent)}}

/* ── Hero ───────────────────────────────────────────────────── */
.page-hero{{
  text-align:center;
  padding:4rem 1rem 3rem;
  background:linear-gradient(180deg,#1a1006 0%,var(--bg) 100%);
}}
.page-hero h1{{
  font-family:var(--font-serif);
  font-size:clamp(1.8rem,4vw,3.2rem);
  color:var(--text-bright);
  letter-spacing:0.04em;
}}
.page-hero h1 span{{
  display:block;font-size:0.45em;font-weight:normal;
  color:var(--accent);letter-spacing:0.2em;
  text-transform:uppercase;margin-bottom:0.5rem;
}}
.page-hero p{{color:var(--text-dim);margin-top:0.75rem;font-size:0.9rem}}

/* ── Decorative score line ──────────────────────────────────── */
.score-line{{
  display:flex;align-items:center;justify-content:center;
  gap:1.5rem;padding:1.5rem 2rem;
  color:var(--text-dim);font-size:1.6rem;letter-spacing:0.4em;
  opacity:0.3;
}}

/* ── Container ──────────────────────────────────────────────── */
.container{{max-width:1200px;margin:0 auto;padding:0 1.5rem 4rem}}

/* ── Card ───────────────────────────────────────────────────── */
.sym-card{{
  background:var(--bg2);
  border:1px solid var(--border);
  border-radius:var(--radius);
  margin-bottom:2.5rem;
  overflow:hidden;
  transition:box-shadow 0.2s;
}}
.sym-card:hover{{
  box-shadow:0 0 0 1px hsla(var(--hue),55%,50%,0.4),
             0 8px 32px rgba(0,0,0,0.55);
}}
.sym-header{{
  display:flex;align-items:center;gap:1.5rem;
  padding:1.4rem 1.8rem;
  background:linear-gradient(
    135deg,
    color-mix(in oklch, hsl(var(--hue),35%,18%) 100%, #1a1006 0%) 0%,
    color-mix(in oklch, hsl(var(--hue),20%,10%) 100%, #0d0a06 0%) 100%
  );
  border-bottom:1px solid var(--border);
}}
.sym-numeral{{
  font-family:var(--font-serif);
  font-size:2.8rem;font-weight:normal;line-height:1;
  color:hsla(var(--hue),65%,70%,1);
  min-width:4.5rem;text-align:center;
  text-shadow:0 0 20px hsla(var(--hue),60%,50%,0.3);
}}
.sym-meta h2{{
  font-family:var(--font-serif);font-size:1.25rem;
  font-weight:normal;color:var(--text-bright);margin-bottom:0.45rem;
}}
.in-key{{color:var(--text-dim);font-size:0.95em}}
.subtitle{{color:hsla(var(--hue),65%,70%,1);font-style:italic;font-size:0.95em}}
.sym-tags{{display:flex;flex-wrap:wrap;gap:0.4rem}}
.tag{{
  font-size:0.78rem;padding:0.2rem 0.6rem;border-radius:20px;
  background:rgba(255,255,255,0.06);color:var(--text-dim);
  border:1px solid rgba(255,255,255,0.08);
}}
.opus-tag{{
  color:var(--accent);
  border-color:rgba(212,144,28,0.35);
  background:rgba(212,144,28,0.08);
  font-weight:600;
}}
.total-time{{
  color:#c8b870;
  border-color:rgba(200,184,112,0.3);
  background:rgba(200,184,112,0.07);
}}
.sym-note{{
  font-size:0.82rem;color:var(--text-dim);
  padding:0.7rem 1.8rem;
  border-bottom:1px solid var(--border);
  background:rgba(0,0,0,0.2);font-style:italic;
}}

/* ── Body layout ────────────────────────────────────────────── */
.sym-body{{display:grid;grid-template-columns:1fr 1.35fr}}
@media(max-width:760px){{.sym-body{{grid-template-columns:1fr}}}}
.panel{{padding:1.4rem 1.8rem}}
.movements-panel{{border-right:1px solid var(--border)}}
@media(max-width:760px){{
  .movements-panel{{border-right:none;border-bottom:1px solid var(--border)}}
}}
.panel-title{{
  font-size:0.7rem;font-weight:700;text-transform:uppercase;
  letter-spacing:0.12em;color:var(--text-dim);
  margin-bottom:1rem;padding-bottom:0.4rem;
  border-bottom:1px solid var(--border);
}}

/* ── Movement table ─────────────────────────────────────────── */
.mvt-table{{width:100%;border-collapse:collapse}}
.mvt-table tr:hover td{{background:rgba(255,255,255,0.03)}}
.mvt-table td{{
  padding:0.45rem 0.3rem;vertical-align:top;
  border-bottom:1px solid rgba(255,255,255,0.04);
}}
.mvt-table tr:last-child td{{border-bottom:none}}
.mvt-num{{
  font-variant-numeric:tabular-nums;color:var(--text-dim);
  font-size:0.78rem;white-space:nowrap;padding-right:0.6rem;padding-top:0.55rem;
}}
.mvt-tempo{{font-size:0.83rem;color:var(--text);padding-right:0.8rem}}
.mvt-label{{font-style:italic;color:var(--accent);font-size:0.78rem}}
.mvt-voices{{font-size:0.72rem;color:var(--text-dim);margin-top:0.15rem;font-style:italic}}
.mvt-dur{{
  font-variant-numeric:tabular-nums;color:var(--text-bright);
  font-size:0.82rem;white-space:nowrap;text-align:right;
  padding-right:0.6rem;padding-top:0.55rem;
}}
.mvt-bar-cell{{width:110px;vertical-align:middle;padding-top:0.55rem}}
.mvt-bar{{
  height:5px;border-radius:0;  /* flat bars — different from Mahler's rounded */
  min-width:4px;
}}

/* ── Instrumentation ────────────────────────────────────────── */
.inst-group{{
  margin-bottom:0.85rem;display:flex;
  flex-wrap:wrap;align-items:baseline;gap:0.3rem 0.5rem;
}}
.inst-cat{{
  font-size:0.68rem;font-weight:700;text-transform:uppercase;
  letter-spacing:0.1em;min-width:5.5rem;flex-shrink:0;
}}
.pills{{display:flex;flex-wrap:wrap;gap:0.3rem}}
.pill{{
  font-size:0.75rem;padding:0.18rem 0.5rem;
  border-radius:3px;  /* square corners — distinct from Mahler's pill shape */
  background:rgba(255,255,255,0.05);
  border-left:2px solid var(--pill-color);
  color:color-mix(in srgb,var(--pill-color) 85%,white);
  cursor:default;transition:background 0.15s;
}}
.pill:hover{{background:color-mix(in srgb,var(--pill-color) 18%,transparent)}}
.pill em{{font-style:normal;opacity:0.65;font-size:0.9em;margin-left:0.15rem}}

/* ── Footer ─────────────────────────────────────────────────── */
.site-footer{{
  text-align:center;padding:2rem 1rem;
  color:var(--text-dim);font-size:0.78rem;
  border-top:1px solid var(--border);
}}
</style>
</head>
<body>

<nav class="site-nav">
  <span class="brand">Beethoven · Complete Symphonies</span>
  {nav_links}
  <a class="back-link" href="index.html">&#8592; All Composers</a>
</nav>

<div class="page-hero">
  <h1>
    <span>Ludwig van Beethoven · 1770 – 1827</span>
    Complete Symphonies
  </h1>
  <p>Instrumentation &amp; movement running times &middot; 9 symphonies &middot; approx. durations based on standard performances</p>
</div>

<div class="score-line" aria-hidden="true">
  &#9834; &nbsp; &#9833; &nbsp; &#9835; &nbsp; &#9834; &nbsp; &#9833; &nbsp; &#9835; &nbsp; &#9834;
</div>

<div class="container">
{cards}
</div>

<footer class="site-footer">
  Running times are representative averages and vary by conductor.
  Instrumentation notes reflect forces at first publication unless otherwise stated.
  Hover movements for additional notes.
</footer>

</body>
</html>"""

with open(OUT, "w", encoding="utf-8") as f:
    f.write(html)
print(f"HTML written to {OUT}")
