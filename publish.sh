#!/usr/bin/env bash
# Build, test, document and publish, in that order.
set -euo pipefail
cd "$(dirname "$0")"
export DBT_PROFILES_DIR=.
dbt build
cp target/run_results.json target/build_results.json   # docs generate overwrites it
python ingest/quality_report.py                          # docs/quality.md
dbt docs generate --static                               # target/static_index.html
python ingest/build_site.py                              # docs/index.html + docs/dbt/
python ingest/export_marts.py                            # data/marts/*.parquet
