"""Publish the marts as parquet files in data/marts/ (read by the analysis repository)."""

from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "marts"
OUT.mkdir(parents=True, exist_ok=True)
con = duckdb.connect(str(ROOT / "warehouse.duckdb"), read_only=True)
for (table,) in con.sql("select table_name from information_schema.tables where table_schema = 'marts'").fetchall():
    con.sql(f"copy marts.{table} to '{OUT / (table + '.parquet')}' (format parquet, compression zstd)")
    print(table, con.sql(f"select count(*) from marts.{table}").fetchall()[0][0])
