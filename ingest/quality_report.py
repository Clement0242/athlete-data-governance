"""Write docs/quality.md from the last `dbt build` (target/build_results.json):
every rule, its result, and what the known source defects are. See publish.sh."""

import json
from collections import Counter
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
run = json.loads((ROOT / "target" / "build_results.json").read_text())
manifest = json.loads((ROOT / "target" / "manifest.json").read_text())
con = duckdb.connect(str(ROOT / "warehouse.duckdb"), read_only=True)

# What each warning means, written by a human: a failing rule is only useful
# if someone can say whether it is a defect of the source or of the pipeline.
KNOWN = {
    "assert_provider_daily_load_reconciles": (
        "Source defect. For 3 players the provider's daily load is higher than the sum of the "
        "exported session reports (never lower): sessions are missing from `session.json`. The "
        "warehouse recomputes the load from the sessions it has and never uses the provider's figure."),
    "assert_gps_players_are_known": (
        "Source defect. Players with GNSS recordings but no questionnaire at all. Their identifiers use "
        "another UUID format than PmSys's, and about as many players have questionnaires but no GNSS: "
        "most likely the same players pseudonymised twice. A record linkage on attendance (GNSS days vs "
        "RPE days) was tried and cannot tell them apart, because teammates train on the same days. No "
        "link is guessed: the mapping has to come from the provider. Until then their GNSS data stays "
        "in fct_gps_session but cannot be related to load, wellness or injuries."),
    "assert_gps_player_from_file_name": (
        "Source defect, repaired. GNSS files whose player column is empty although the file name "
        "carries the player identifier. The identifier is recovered from the file name, a rule that "
        "is visible in staging, and the files are listed here."),
    "assert_gps_file_names_unique": (
        "Source defect, quarantined. The 2021 archive of one team holds two *different* recordings "
        "under the same file name for 2 players (distance and duration differ). Nothing says which one "
        "is the player's, so both are flagged duplicate_file_name and neither feeds an indicator."),
    "assert_injury_reports_not_duplicated": (
        "Source defect, harmless. The same body location reported twice on the same day (double "
        "submission). Episodes are built from distinct reports, so they are not affected."),
}

tests = []
for r in run["results"]:
    node = manifest["nodes"].get(r["unique_id"], {})
    if node.get("resource_type") != "test":
        continue
    name = node.get("test_metadata", {}).get("name") or node["name"]
    model = (node.get("attached_node") or "").split(".")[-1] or "several"
    column = node.get("column_name") or ""
    tests.append((r["status"], node["name"], name, model, column, r.get("failures") or 0))

status = Counter(t[0] for t in tests)
rows = {t: con.sql(f"select count(*) from marts.{t}").fetchall()[0][0] for t in
        ["dim_player", "fct_training_session", "fct_gps_session", "fct_injury_episode", "fct_player_day"]}

lines = ["# Data quality report", "",
         f"Generated from the last `dbt build`: **{len(tests)} rules, {status.get('pass', 0)} passed, "
         f"{status.get('warn', 0)} warnings, {status.get('fail', 0) + status.get('error', 0)} failures.**", "",
         "| Mart | Rows |", "|---|---:|"] + [f"| `{k}` | {v:,} |" for k, v in rows.items()] + [
         "", "## Warnings: what the rules found in the source", ""]
for st, full, name, model, col, n in tests:
    if st == "warn":
        key = next((k for k in KNOWN if k in full), None)
        lines += [f"### `{full}` — {n} rows", "", KNOWN.get(key, "To investigate."), ""]
flags = con.sql("""select gps_quality_flag, hr_quality_flag, count(*) as n from marts.fct_gps_session
                   group by all order by n desc""").fetchall()
lines += ["## Quarantined recordings", "",
          "Recordings are never deleted: each one is flagged, and indicators are computed on valid data only.", "",
          "| GNSS | Heart rate | Recordings |", "|---|---|---:|"] + [f"| {a} | {b} | {n:,} |" for a, b, n in flags] + [
          "", "`frozen_sensor`: a constant 82 bpm for most of the session, the strap's default value. "
          "It would pass every range check; it is caught by the share of time spent at a single value.", ""]
lines += ["## All rules", "", "| Result | Rule | Model | Column | Failing rows |", "|---|---|---|---|---:|"]
for st, full, name, model, col, n in sorted(tests, key=lambda t: (t[0] != "warn", t[3], t[2])):
    lines.append(f"| {st} | `{name}` | `{model}` | {col} | {n} |")
(ROOT / "docs" / "quality.md").write_text("\n".join(lines) + "\n")
print("docs/quality.md:", dict(status))
