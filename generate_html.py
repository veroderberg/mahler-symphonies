#!/usr/bin/env python3
"""Generate a self-contained HTML report from mahler.db."""

import sqlite3, os, math

DB   = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mahler.db")
OUT  = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mahler.html")

def fmt_duration(mins: float) -> str:
    m = int(mins)
    s = int(round((mins - m) * 60))
    if s == 0:
        return f"{m}′"
    return f"{m}′{s:02d}″"

def bar_width(dur: float, max_dur: float) -> int:
    return max(4, int(dur / max_dur * 100))

# ── Category display order & accent colours ──────────────────────────────────
CAT_ORDER  = ["Woodwind","Brass","Percussion","Keyboard","Strings","Plucked","Voice"]
CAT_COLORS = {
    "Woodwind":   "#4caf8a",
    "Brass":      "#e8973a",
    "Percussion": "#c0697d",
    "Keyboard":   "#7c8de8",
    "Strings":    "#a3c46a",
    "Plucked":    "#d4ac3e",
    "Voice":      "#b07ec8",
}

conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row

symphonies = conn.execute("SELECT * FROM symphonies ORDER BY number").fetchall()

# Pre-fetch all movements and instrumentation
mvt_map  = {}
inst_map = {}
for s in symphonies:
    sid = s["id"]
    mvt_map[sid] = conn.execute(
        "SELECT * FROM movements WHERE symphony_id=? ORDER BY number", (sid,)
    ).fetchall()
    rows = conn.execute(
        """SELECT ic.name cat, inst.name instrument, si.count, si.notes
           FROM symphony_instruments si
           JOIN instruments inst ON inst.id=si.instrument_id
           JOIN instrument_categories ic ON ic.id=inst.category_id
           WHERE si.symphony_id=?
           ORDER BY ic.id, inst.id""",
        (sid,)
    ).fetchall()
    grouped = {}
    for r in rows:
        grouped.setdefault(r["cat"], []).append(r)
    inst_map[sid] = grouped

conn.close()

# ── Helper: render one symphony card ─────────────────────────────────────────
def render_symphony(s) -> str:
    sid       = s["id"]
    mvts      = mvt_map[sid]
    inst_grps = inst_map[sid]
    max_dur   = max(m["duration_min"] for m in mvts)
    roman     = ["","I","II","III","IV","V","VI","VII","VIII","IX","X"][s["number"]]

    # subtitle tag
    subtitle_html = (
        f'<span class="subtitle">"{s["subtitle"]}"</span>' if s["subtitle"] else ""
    )

    # header bar color — cycle through a palette
    hue = (s["number"] - 1) * 36   # 0..324

    # movements table rows
    mvt_rows = ""
    for m in mvts:
        dur_fmt  = fmt_duration(m["duration_min"])
        bw       = bar_width(m["duration_min"], max_dur)
        label    = f'<span class="mvt-label">{m["label"]}</span> ' if m["label"] else ""
        voices   = (f'<div class="mvt-voices">{m["voices"]}</div>'
                    if m["voices"] else "")
        note_tip = (f' title="{m["notes"]}"' if m["notes"] else "")
        mvt_rows += f"""
        <tr{note_tip}>
          <td class="mvt-num">{roman}.{m["number"]}</td>
          <td class="mvt-tempo">{label}{m["tempo_marking"]}{voices}</td>
          <td class="mvt-dur">{dur_fmt}</td>
          <td class="mvt-bar-cell">
            <div class="mvt-bar" style="width:{bw}%"></div>
          </td>
        </tr>"""

    # instrumentation pills grouped by category
    inst_html = ""
    for cat in CAT_ORDER:
        if cat not in inst_grps:
            continue
        color = CAT_COLORS[cat]
        pills = ""
        for r in inst_grps[cat]:
            cnt  = f"×{r['count']}" if r["count"] else ""
            tip  = f' title="{r["notes"]}"' if r["notes"] else ""
            pills += f'<span class="pill" style="--pill-color:{color}"{tip}>{r["instrument"]}{(" <em>"+cnt+"</em>") if cnt else ""}</span>'
        inst_html += f"""
        <div class="inst-group">
          <span class="inst-cat" style="color:{color}">{cat}</span>
          <div class="pills">{pills}</div>
        </div>"""

    total_fmt = fmt_duration(s["total_duration_min"])

    notes_html = (
        f'<p class="sym-note">{s["notes"]}</p>' if s["notes"] else ""
    )

    return f"""
  <section class="sym-card" id="sym{s['number']}" style="--hue:{hue}">
    <header class="sym-header">
      <div class="sym-numeral">{roman}</div>
      <div class="sym-meta">
        <h2>Symphony No.&nbsp;{s['number']} <span class="in-key">in {s['key']}</span>
          {subtitle_html}</h2>
        <div class="sym-tags">
          <span class="tag">&#9836; {s['year_composed']}</span>
          {"<span class='tag'>Premiere: "+str(s['year_premiered'])+"</span>" if s['year_premiered'] else ""}
          <span class="tag total-time">Total: {total_fmt}</span>
        </div>
      </div>
    </header>

    {notes_html}

    <div class="sym-body">
      <div class="panel movements-panel">
        <h3 class="panel-title">Movements</h3>
        <table class="mvt-table">
          <tbody>{mvt_rows}
          </tbody>
        </table>
      </div>

      <div class="panel inst-panel">
        <h3 class="panel-title">Instrumentation</h3>
        {inst_html}
      </div>
    </div>
  </section>"""


# ── Assemble full page ────────────────────────────────────────────────────────
cards = "\n".join(render_symphony(s) for s in symphonies)

# nav links
nav_links = " ".join(
    f'<a href="#sym{s["number"]}">{["","I","II","III","IV","V","VI","VII","VIII","IX","X"][s["number"]]}</a>'
    for s in symphonies
)

html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Gustav Mahler — Complete Symphonies</title>
<style>
/* ── Reset & base ──────────────────────────────────────────── */
*, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

:root {{
  --bg:        #0f1117;
  --bg2:       #171b26;
  --bg3:       #1e2334;
  --border:    #2c3250;
  --text:      #d4d8e8;
  --text-dim:  #7a82a0;
  --text-bright: #edf0fb;
  --accent:    #c4a84a;
  --radius:    12px;
  --font-serif: 'Georgia', 'Times New Roman', serif;
  --font-sans:  'Segoe UI', system-ui, sans-serif;
}}

html {{ scroll-behavior: smooth; }}

body {{
  background: var(--bg);
  color: var(--text);
  font-family: var(--font-sans);
  font-size: 14px;
  line-height: 1.6;
}}

/* ── Top nav ───────────────────────────────────────────────── */
.site-nav {{
  position: sticky; top: 0; z-index: 100;
  background: rgba(15,17,23,0.92);
  backdrop-filter: blur(10px);
  border-bottom: 1px solid var(--border);
  display: flex; align-items: center; gap: 1rem;
  padding: 0.55rem 2rem;
}}
.site-nav .brand {{
  font-family: var(--font-serif);
  font-size: 1rem;
  color: var(--accent);
  white-space: nowrap;
  margin-right: auto;
}}
.site-nav a {{
  color: var(--text-dim);
  text-decoration: none;
  font-size: 0.85rem;
  font-weight: 600;
  padding: 0.25rem 0.5rem;
  border-radius: 6px;
  transition: background 0.15s, color 0.15s;
}}
.site-nav a:hover {{
  background: var(--bg3);
  color: var(--accent);
}}

/* ── Page header ───────────────────────────────────────────── */
.page-hero {{
  text-align: center;
  padding: 4rem 1rem 3rem;
  background: linear-gradient(180deg, #12192e 0%, var(--bg) 100%);
}}
.page-hero h1 {{
  font-family: var(--font-serif);
  font-size: clamp(1.8rem, 4vw, 3.2rem);
  color: var(--text-bright);
  letter-spacing: 0.05em;
}}
.page-hero h1 span {{
  display: block;
  font-size: 0.45em;
  font-weight: normal;
  color: var(--accent);
  letter-spacing: 0.2em;
  text-transform: uppercase;
  margin-bottom: 0.5rem;
}}
.page-hero p {{
  color: var(--text-dim);
  margin-top: 0.75rem;
  font-size: 0.9rem;
}}

/* ── Container ─────────────────────────────────────────────── */
.container {{
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 1.5rem 4rem;
}}

/* ── Symphony card ─────────────────────────────────────────── */
.sym-card {{
  background: var(--bg2);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  margin-bottom: 2.5rem;
  overflow: hidden;
  transition: box-shadow 0.2s;
}}
.sym-card:hover {{
  box-shadow: 0 0 0 1px hsla(var(--hue),60%,55%,0.35),
              0 8px 32px rgba(0,0,0,0.5);
}}

.sym-header {{
  display: flex;
  align-items: center;
  gap: 1.5rem;
  padding: 1.4rem 1.8rem;
  background: linear-gradient(
    135deg,
    hsla(var(--hue),45%,18%,1) 0%,
    hsla(var(--hue),30%,12%,1) 100%
  );
  border-bottom: 1px solid var(--border);
}}

.sym-numeral {{
  font-family: var(--font-serif);
  font-size: 2.8rem;
  font-weight: normal;
  color: hsla(var(--hue),70%,72%,1);
  min-width: 4rem;
  text-align: center;
  line-height: 1;
  opacity: 0.9;
}}

.sym-meta h2 {{
  font-family: var(--font-serif);
  font-size: 1.25rem;
  font-weight: normal;
  color: var(--text-bright);
  margin-bottom: 0.45rem;
}}
.sym-meta .in-key {{
  color: var(--text-dim);
  font-size: 0.95em;
}}
.subtitle {{
  color: hsla(var(--hue),70%,72%,1);
  font-style: italic;
  font-size: 0.95em;
}}

.sym-tags {{ display: flex; flex-wrap: wrap; gap: 0.5rem; }}
.tag {{
  font-size: 0.78rem;
  padding: 0.2rem 0.6rem;
  border-radius: 20px;
  background: rgba(255,255,255,0.07);
  color: var(--text-dim);
  border: 1px solid rgba(255,255,255,0.1);
}}
.total-time {{
  color: var(--accent);
  border-color: rgba(196,168,74,0.3);
  background: rgba(196,168,74,0.08);
}}

.sym-note {{
  font-size: 0.82rem;
  color: var(--text-dim);
  padding: 0.7rem 1.8rem;
  border-bottom: 1px solid var(--border);
  background: rgba(0,0,0,0.15);
  font-style: italic;
}}

/* ── Body two-column ───────────────────────────────────────── */
.sym-body {{
  display: grid;
  grid-template-columns: 1fr 1.35fr;
  gap: 0;
}}
@media (max-width: 760px) {{
  .sym-body {{ grid-template-columns: 1fr; }}
}}

.panel {{
  padding: 1.4rem 1.8rem;
}}
.movements-panel {{
  border-right: 1px solid var(--border);
}}
@media (max-width: 760px) {{
  .movements-panel {{ border-right: none; border-bottom: 1px solid var(--border); }}
}}

.panel-title {{
  font-size: 0.7rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  color: var(--text-dim);
  margin-bottom: 1rem;
  padding-bottom: 0.4rem;
  border-bottom: 1px solid var(--border);
}}

/* ── Movement table ────────────────────────────────────────── */
.mvt-table {{
  width: 100%;
  border-collapse: collapse;
}}
.mvt-table tr {{
  cursor: default;
}}
.mvt-table tr:hover td {{
  background: rgba(255,255,255,0.03);
}}
.mvt-table td {{
  padding: 0.45rem 0.3rem;
  vertical-align: top;
  border-bottom: 1px solid rgba(255,255,255,0.04);
}}
.mvt-table tr:last-child td {{ border-bottom: none; }}

.mvt-num {{
  font-variant-numeric: tabular-nums;
  color: var(--text-dim);
  font-size: 0.78rem;
  white-space: nowrap;
  padding-right: 0.6rem;
  padding-top: 0.55rem;
}}
.mvt-tempo {{
  font-size: 0.83rem;
  color: var(--text);
  padding-right: 0.8rem;
}}
.mvt-label {{
  font-style: italic;
  color: var(--accent);
  font-size: 0.78rem;
}}
.mvt-voices {{
  font-size: 0.72rem;
  color: var(--text-dim);
  margin-top: 0.15rem;
  font-style: italic;
}}
.mvt-dur {{
  font-variant-numeric: tabular-nums;
  color: var(--text-bright);
  font-size: 0.82rem;
  white-space: nowrap;
  text-align: right;
  padding-right: 0.6rem;
  padding-top: 0.55rem;
}}
.mvt-bar-cell {{
  width: 120px;
  vertical-align: middle;
  padding-top: 0.55rem;
}}
.mvt-bar {{
  height: 6px;
  border-radius: 3px;
  background: hsla(var(--hue),55%,52%,0.65);
  min-width: 4px;
  transition: width 0.3s;
}}

/* ── Instrumentation pills ─────────────────────────────────── */
.inst-group {{
  margin-bottom: 0.85rem;
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 0.3rem 0.5rem;
}}
.inst-cat {{
  font-size: 0.68rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  min-width: 5.5rem;
  flex-shrink: 0;
}}
.pills {{
  display: flex;
  flex-wrap: wrap;
  gap: 0.3rem;
}}
.pill {{
  font-size: 0.75rem;
  padding: 0.2rem 0.55rem;
  border-radius: 20px;
  background: rgba(255,255,255,0.05);
  border: 1px solid color-mix(in srgb, var(--pill-color) 40%, transparent);
  color: color-mix(in srgb, var(--pill-color) 90%, white);
  cursor: default;
  transition: background 0.15s;
}}
.pill:hover {{
  background: color-mix(in srgb, var(--pill-color) 20%, transparent);
}}
.pill em {{
  font-style: normal;
  opacity: 0.7;
  font-size: 0.9em;
  margin-left: 0.15rem;
}}

/* ── Footer ────────────────────────────────────────────────── */
.site-footer {{
  text-align: center;
  padding: 2rem 1rem;
  color: var(--text-dim);
  font-size: 0.78rem;
  border-top: 1px solid var(--border);
}}
</style>
</head>
<body>

<nav class="site-nav">
  <span class="brand">Mahler · Complete Symphonies</span>
  {nav_links}
</nav>

<div class="page-hero">
  <h1>
    <span>Gustav Mahler · 1860 – 1911</span>
    Complete Symphonies
  </h1>
  <p>Instrumentation &amp; movement running times &middot; 10 symphonies &middot; approx. durations based on standard performances</p>
</div>

<div class="container">
{cards}
</div>

<footer class="site-footer">
  Running times are representative averages; actual durations vary by conductor and edition.
  Symphony No.&nbsp;10 data reflects the Deryck Cooke performing edition (1976).
  Hover movements for additional notes.
</footer>

</body>
</html>"""

with open(OUT, "w", encoding="utf-8") as f:
    f.write(html)

print(f"HTML written to {OUT}")
