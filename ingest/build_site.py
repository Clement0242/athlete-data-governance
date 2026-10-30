"""Build the GitHub Pages site (docs/) from dbt's own artefacts.

The page is generated from target/manifest.json and run_results.json, so the
dictionary, the lineage and the quality results shown are always those of the
last build, never a hand-written copy. Run after `dbt build` and
`dbt docs generate --static`.
"""

from __future__ import annotations

import html
import json
import shutil
from collections import defaultdict
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
REPO = "https://github.com/Clement0242/athlete-data-governance"

manifest = json.loads((ROOT / "target/manifest.json").read_text())
# `dbt docs generate` overwrites run_results.json: publish.sh keeps the build's copy.
run = json.loads((ROOT / "target/build_results.json").read_text())
con = duckdb.connect(str(ROOT / "warehouse.duckdb"), read_only=True)
e = html.escape

nodes = {**manifest["nodes"], **manifest["sources"]}
models = {k: v for k, v in manifest["nodes"].items() if v["resource_type"] in ("model", "seed")}
tests = {k: v for k, v in manifest["nodes"].items() if v["resource_type"] == "test"}
status = {r["unique_id"]: r for r in run["results"]}


def layer(uid: str) -> int:
    n = nodes[uid]
    if n["resource_type"] in ("source", "seed"):
        return 0
    return {"staging": 1, "intermediate": 2, "marts": 3}.get(n["fqn"][1] if len(n["fqn"]) > 2 else "", 3)


# ------------------------------------------------------------- lineage (SVG)

GROUPS = {  # several raw files of the same kind are drawn as one box
    "wellness": ("soccermon.wellness_* (7 files)", lambda n: n["name"].startswith("wellness_")),
    "provider_load": ("soccermon.load metrics (4 files)", lambda n: n["name"] in ("daily_load_wide", "atl_wide", "ctl28_wide", "acwr_wide")),
}


def _group(uid: str) -> str:
    n = nodes[uid]
    if n["resource_type"] == "source":
        for g, (_, test) in GROUPS.items():
            if test(n):
                return "group." + g
    return uid


def lineage_svg() -> str:
    graph = defaultdict(set)
    label, desc, lv_of = {}, {}, {}
    for uid, n in nodes.items():
        if n["resource_type"] not in ("source", "seed", "model"):
            continue
        g = _group(uid)
        lv_of[g] = layer(uid)
        if g.startswith("group."):
            label[g], desc[g] = GROUPS[g[6:]][0], "Wide files: one column per player, unpivoted by a macro."
        else:
            label[g] = n["name"] if n["resource_type"] != "source" else f'{n["source_name"]}.{n["name"]}'
            desc[g] = n.get("description") or label[g]
        for p in n.get("depends_on", {}).get("nodes", []):
            if p in nodes:
                graph[g].add(_group(p))
    cols = defaultdict(list)
    for g, lv in lv_of.items():
        cols[lv].append(g)
    order = {}
    for lv in sorted(cols):  # order each column by the mean position of its parents
        def key(u):
            ps = [order[p] for p in graph[u] if p in order]
            return (sum(ps) / len(ps) if ps else 0, label[u])
        for i, u in enumerate(sorted(cols[lv], key=key)):
            order[u] = i
    W, colw, boxw, boxh, gap = 1150, 286, 246, 30, 12
    height = max(len(c) for c in cols.values()) * (boxh + gap) + 60
    pos = {}
    for lv, us in cols.items():
        top = 46 + (height - 46 - len(us) * (boxh + gap)) / 2
        for u in us:
            pos[u] = (16 + lv * colw, top + order[u] * (boxh + gap))
    titles = ["Sources & reference", "Staging", "Intermediate", "Marts"]
    fills = ["var(--creux)", "var(--surface)", "var(--surface)", "var(--accent-w)"]
    out = [f'<svg viewBox="0 0 {W} {height}" role="img" aria-label="Lineage of the warehouse, from sources to marts">']
    for lv, t in enumerate(titles):
        out.append(f'<text x="{16 + lv * colw}" y="22" font-size="12" font-weight="600" '
                   f'letter-spacing="1.2" style="fill:var(--mut)">{t.upper()}</text>')
    for u, (x, y) in pos.items():
        for p in graph[u]:
            if p not in pos or p == u:
                continue
            px, py = pos[p]
            if lv_of[p] == lv_of[u]:  # mart built on another mart: arc on the right
                x1, y1, y2 = px + boxw, py + boxh / 2, y + boxh / 2
                d = f"M{x1},{y1} C{x1 + 34},{y1} {x1 + 34},{y2} {x1},{y2}"
            else:
                x1, y1, x2, y2 = px + boxw, py + boxh / 2, x, y + boxh / 2
                d = f"M{x1},{y1} C{x1 + 26},{y1} {x2 - 26},{y2} {x2},{y2}"
            out.append(f'<path d="{d}" fill="none" style="stroke:var(--ligne-2)" stroke-width="1.2"/>')
    for u, (x, y) in pos.items():
        lv = lv_of[u]
        out.append(f'<g><title>{e(desc[u])}</title>'
                   f'<rect x="{x}" y="{y}" width="{boxw}" height="{boxh}" rx="7" '
                   f'style="fill:{fills[lv]};stroke:var(--ligne-2)"/>'
                   f'<text x="{x + 10}" y="{y + 19.5}" font-size="11.5">{e(label[u][:40])}</text></g>')
    out.append("</svg>")
    return "".join(out)


# --------------------------------------------------------------- dictionary

def tests_of(uid: str, column: str | None) -> list[str]:
    out = []
    for tid, t in tests.items():
        if t.get("attached_node") == uid and (t.get("column_name") or None) == column:
            name = t.get("test_metadata", {}).get("name", t["name"])
            kw = t.get("test_metadata", {}).get("kwargs", {})
            if name == "accepted_range":
                name = f"range {kw.get('min_value', '')}–{kw.get('max_value', '')}"
            elif name == "relationships":
                name = "→ " + str(kw.get("to", "")).replace("ref('", "").replace("')", "")
            out.append(name)
    return out


def sens_badge(s: str) -> str:
    cls = {"health": "sante", "pseudonymised identifier": "pseudo"}.get(s, "")
    return f'<span class="pastille {cls}">{e(s)}</span>'


def dictionary() -> str:
    parts = []
    marts = sorted((u for u, n in models.items() if n["resource_type"] == "model" and layer(u) == 3),
                   key=lambda u: models[u]["name"])
    for u in marts:
        m = models[u]
        n_rows = con.sql(f"select count(*) from marts.{m['name']}").fetchall()[0][0]
        grain = m.get("meta", {}).get("grain") or m.get("config", {}).get("meta", {}).get("grain", "")
        rows = []
        for c in m["columns"].values():
            meta = c.get("meta") or c.get("config", {}).get("meta", {})
            ts = tests_of(u, c["name"])
            rows.append(f'<tr><td><code>{e(c["name"])}</code></td><td>{e((c.get("data_type") or "").lower())}</td>'
                        f'<td>{e(meta.get("unit", ""))}</td><td>{sens_badge(meta.get("sensitivity", ""))}</td>'
                        f'<td>{e(c.get("description", ""))}</td><td>{e(", ".join(ts))}</td></tr>')
        table_tests = tests_of(u, None)
        parts.append(
            f'<details><summary><code>{e(m["name"])}</code> <small>{e(grain)} · {n_rows:,} rows · '
            f'{len(m["columns"])} columns · contract enforced</small></summary>'
            f'<p>{e(m["description"])}</p>'
            + (f'<p><strong>Table rules:</strong> {e(", ".join(table_tests))}</p>' if table_tests else "")
            + '<div class="tableau"><table><thead><tr><th>Column</th><th>Type</th><th>Unit</th><th>Sensitivity</th>'
              '<th>Definition</th><th>Rules</th></tr></thead><tbody>' + "".join(rows) + "</tbody></table></div></details>")
    return "\n".join(parts)


# ------------------------------------------------------------------- quality

def quality() -> tuple[str, dict]:
    res = [status[t] for t in tests if t in status]
    counts = defaultdict(int)
    for r in res:
        counts[r["status"]] += 1
    rows = []
    for tid, t in sorted(tests.items(), key=lambda kv: (status.get(kv[0], {}).get("status") != "warn", kv[1]["name"])):
        r = status.get(tid, {})
        st = r.get("status", "skipped")
        badge = {"pass": "ok", "warn": "warn", "fail": "ko", "error": "ko"}.get(st, "")
        model = (t.get("attached_node") or "").split(".")[-1]
        name = t.get("test_metadata", {}).get("name", t["name"])
        rows.append(f'<tr><td><span class="pastille {badge}">{st}</span></td><td><code>{e(name)}</code></td>'
                    f'<td><code>{e(model)}</code></td><td>{e(t.get("column_name") or "")}</td>'
                    f'<td class="num">{r.get("failures") or 0}</td></tr>')
    table = ('<details><summary>All rules <small>' + f'{len(res)} rules · {counts["pass"]} passed · '
             f'{counts["warn"]} warnings · {counts["fail"] + counts["error"]} failures</small></summary>'
             '<div class="tableau"><table><thead><tr><th>Result</th><th>Rule</th><th>Model</th><th>Column</th>'
             '<th class="num">Rows</th></tr></thead><tbody>' + "".join(rows) + "</tbody></table></div></details>")
    return table, counts


def warn_count(name: str) -> int:
    for tid, t in tests.items():
        if t["name"] == name:
            return status.get(tid, {}).get("failures") or 0
    return 0


def main() -> None:
    DOCS.mkdir(exist_ok=True)
    shutil.copy(ROOT / "docs" / "assets" / "projet.css", DOCS / "projet.css") if (ROOT / "docs/assets/projet.css").exists() else None
    (DOCS / "dbt").mkdir(exist_ok=True)
    shutil.copy(ROOT / "target" / "static_index.html", DOCS / "dbt" / "index.html")

    q_table, counts = quality()
    n = lambda sql: con.sql(sql).fetchall()[0][0]
    flags = con.sql("""select gps_quality_flag, hr_quality_flag, count(*) from marts.fct_gps_session
                       group by all order by 3 desc""").fetchall()
    flag_rows = "".join(f'<tr><td><span class="pastille {"ok" if a == "ok" else "warn"}">{e(a)}</span></td>'
                        f'<td><span class="pastille {"ok" if b == "ok" else "warn"}">{e(b)}</span></td>'
                        f'<td class="num">{c:,}</td></tr>' for a, b, c in flags)
    frozen = sum(c for a, b, c in flags if b == "frozen_sensor")
    implausible = sum(c for a, b, c in flags if a != "ok")
    hr_ok = sum(c for a, b, c in flags if a == "ok" and b == "ok")
    stats = {
        "players": n("select count(*) from marts.dim_player"),
        "player_days": n("select count(*) from marts.fct_player_day"),
        "sessions": n("select count(*) from marts.fct_training_session"),
        "gps": n("select count(*) from marts.fct_gps_session"),
        "episodes": n("select count(*) from marts.fct_injury_episode"),
        "repeats": n("select count(*) from staging.stg_soccermon__training_sessions where is_exact_repeat"),
    }
    page = TEMPLATE.format(
        repo=REPO, lineage=lineage_svg(), dictionary=dictionary(), quality_table=q_table, flag_rows=flag_rows,
        n_rules=sum(counts.values()), n_pass=counts["pass"], n_warn=counts["warn"],
        n_reconcile=warn_count("assert_provider_daily_load_reconciles"),
        n_orphans=warn_count("assert_gps_players_are_known"),
        n_dup_inj=warn_count("assert_injury_reports_not_duplicated"),
        n_dup_files=warn_count("assert_gps_file_names_unique"),
        n_from_name=warn_count("assert_gps_player_from_file_name"),
        frozen=frozen, implausible=implausible, hr_ok=hr_ok, **{k: f"{v:,}" for k, v in stats.items()},
    )
    (DOCS / "index.html").write_text(page)
    print("docs/index.html written,", sum(counts.values()), "rules")


TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Athlete data governance</title>
<meta name="description" content="A governed warehouse for athlete monitoring data (dbt + DuckDB) on the SoccerMon open dataset: data dictionary, lineage, quality rules and what they found.">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1&family=Instrument+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="projet.css">
</head>
<body>
<header class="barre"><div class="enveloppe">
  <a class="marque" href="https://clement0242.github.io"><b>CV</b> Clément Verdier</a>
  <nav aria-label="Sections">
    <a href="#architecture">Architecture</a><a href="#dictionary">Dictionary</a>
    <a href="#quality">Quality</a><a href="#privacy">Privacy</a><a href="#run">Run it</a>
  </nav>
</div></header>

<main>
<div class="tete"><div class="enveloppe">
  <p class="surtitre">Data governance · dbt · DuckDB</p>
  <h1>One definition per indicator, <em>tested on every run</em></h1>
  <p class="chapeau">A governed warehouse for athlete monitoring data (questionnaires, injuries,
  GNSS and heart rate), built on SoccerMon, the open dataset of two elite women's football teams.
  The defects of the source are written down, not silently patched.</p>
  <div class="boutons">
    <a class="bouton" href="{repo}">Code on GitHub</a>
    <a class="bouton creux" href="dbt/">Full dbt documentation</a>
  </div>
  <div class="chiffres">
    <div><b>{n_rules}</b><span>quality rules run on every build ({n_pass} pass, {n_warn} documented warnings)</span></div>
    <div><b>{player_days}</b><span>player-days aligned across every source</span></div>
    <div><b>{gps}</b><span>GNSS + heart-rate recordings, from 99 GB streamed and never stored</span></div>
    <div><b>{frozen:,}</b><span>heart-rate traces found frozen at 82 bpm by one rule</span></div>
  </div>
</div></div>

<section id="architecture"><div class="enveloppe">
  <p class="etiq">Architecture</p>
  <h2>From raw files to contracts</h2>
  <div class="prose">
    <p>Each layer has one job. <strong>Staging</strong> only types and reshapes (wide files to long,
    JSON to rows). <strong>Intermediate</strong> holds every business rule, each in one place: what a
    duplicate is, what an injury episode is, how heart-rate zones are computed. <strong>Marts</strong>
    are the only tables anyone reads: every column is documented and their types are enforced, so a
    change that would break a consumer fails the build instead.</p>
  </div>
  <figure><div class="lignage">{lineage}</div>
  <figcaption>Lineage generated from the dbt manifest. Hover a box for its definition.</figcaption></figure>
</div></section>

<section id="dictionary"><div class="enveloppe">
  <p class="etiq">Data dictionary</p>
  <h2>Every published column, defined</h2>
  <div class="prose"><p>Unit, sensitivity level, definition and the rules that guard it. A day without a report is
  <strong>null, never zero</strong>, and <code>has_rpe</code>, <code>has_gps</code> and <code>has_wellness</code> say
  which sources reported it.</p></div>
  {dictionary}
</div></section>

<section id="quality"><div class="enveloppe">
  <p class="etiq">Quality</p>
  <h2>What the rules found in the published dataset</h2>
  <div class="cartes">
    <div class="carte"><h3>Daily load ≠ its sessions</h3><p>On {n_reconcile} player-days (3 players) the provider's daily load is
      higher than the sum of the sessions it was computed from, never lower: sessions are missing from the export.
      The warehouse recomputes the load from the sessions it has.</p><p class="meta">assert_provider_daily_load_reconciles</p></div>
    <div class="carte"><h3>Heart rate frozen at 82 bpm</h3><p>{frozen:,} recordings show one value for most of the session,
      the strap's default. It passes every range check; the share of time at a single value catches it.</p>
      <p class="meta">hr_quality_flag = frozen_sensor</p></div>
    <div class="carte"><h3>Players pseudonymised twice</h3><p>{n_orphans} players have GNSS data but no questionnaire, under another
      UUID format. A linkage on attendance was tried: teammates train on the same days, so it cannot tell them apart.
      No link is guessed.</p><p class="meta">assert_gps_players_are_known</p></div>
    <div class="carte"><h3>Two recordings, one file name</h3><p>{n_dup_files} file names hold two <em>different</em> recordings
      (distance and duration differ). Nothing says which one is the player's: both are quarantined.</p>
      <p class="meta">gps_quality_flag = duplicate_file_name</p></div>
    <div class="carte"><h3>Player missing inside the file</h3><p>{n_from_name} recordings have an empty player column although the
      file name carries the identifier. It is recovered from the name, by a rule that stays visible.</p>
      <p class="meta">assert_gps_player_from_file_name</p></div>
    <div class="carte"><h3>Duplicates</h3><p>{repeats} exact repeat sessions and {n_dup_inj} injury reports submitted twice, flagged in
      staging and removed in one documented model.</p><p class="meta">is_exact_repeat</p></div>
  </div>
  <h3>Quarantine, not deletion</h3>
  <div class="prose"><p>Every recording keeps its row and gets two flags. Indicators are computed on valid data only:
  {hr_ok:,} recordings have usable heart rate; {implausible} were set aside (unit left recording all day, GNSS jump).</p></div>
  <div class="tableau"><table><thead><tr><th>GNSS</th><th>Heart rate</th><th class="num">Recordings</th></tr></thead>
  <tbody>{flag_rows}</tbody></table></div>
  {quality_table}
</div></section>

<section id="privacy"><div class="enveloppe">
  <p class="etiq">Personal data</p>
  <h2>Health data, handled as such</h2>
  <div class="prose">
    <ul>
      <li>Health data is a special category under GDPR (art. 9), pseudonymised or not.</li>
      <li>Players are pseudonymised by the provider; no other identifier enters the warehouse.</li>
      <li>Every published column carries a sensitivity tag (<span class="pastille">operational</span>
        <span class="pastille pseudo">pseudonymised identifier</span> <span class="pastille sante">health</span>)
        that an access policy or a BI tool can read: the medical staff sees injury episodes, a coach sees availability.</li>
      <li>The raw 100 Hz files are never stored, only the features needed downstream.</li>
    </ul>
  </div>
</div></section>

<section id="run"><div class="enveloppe">
  <p class="etiq">Run it</p>
  <h2>Three commands</h2>
<pre><code>pip install -r requirements.txt
export DBT_PROFILES_DIR=.
dbt build                          # seeds, models, rules, contracts
./publish.sh                       # + quality report, site, published marts</code></pre>
  <div class="prose"><p>Data: Midoglu C. et al. (2024), <em>Scientific Data</em> 11, 553; Zenodo 10033832,
  CC-BY 4.0. The marts feed the analysis
  <a href="https://clement0242.github.io/football-load-injury/">Load states, heart rate × GPS and injuries</a>.</p></div>
</div></section>
</main>

<footer><div class="enveloppe">
  <a href="https://clement0242.github.io">Clément Verdier</a> · data engineer & sport scientist ·
  <a href="{repo}">source</a>
</div></footer>
</body>
</html>
"""

if __name__ == "__main__":
    main()
