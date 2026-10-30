"""Extract per-session features from the SoccerMon objective data on Zenodo.

The four objective archives weigh ~99 GB (one parquet file per player per
day: 10 Hz GNSS + heart rate, 100 Hz accelerometer/gyroscope). They are not
downloaded: each file is fetched by HTTP range requests straight from the zip
on Zenodo, reduced to a few hundred numbers, and dropped. Progress is saved
every few files, so the run can be stopped and resumed.

Outputs (data/derived/):
  sessions-<archive>.parquet  one row per player-day: volumes, zones, efforts,
                              accelerometer load, heart-rate histogram
  epochs-<archive>.parquet    30 s epochs: distance, mean speed, mean HR, load

    python pipeline/extraire_soccermon.py --workers 28
"""

from __future__ import annotations

import argparse
import io
import struct
import sys
import time
import urllib.request
import zlib
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

RECORD = "https://zenodo.org/records/10033832/files/{}?download=1"
ARCHIVES = ["objective-TeamA-2020.zip", "objective-TeamB-2020.zip",
            "objective-TeamA-2021.zip", "objective-TeamB-2021.zip"]
OUT = Path(__file__).resolve().parents[1] / "data" / "derived"

# Speed zones (m/s) commonly used for elite women's football: walking/jogging,
# running, high-speed running (>= 15.5 km/h), sprinting (>= 20 km/h).
ZONES = [0.0, 2.0, 4.3, 5.56, 99.0]
ZONE_NAMES = ["dist_0_2", "dist_2_43", "dist_hsr", "dist_sprint"]
EFFORT_THRESHOLD = 2.0  # m/s², accelerations and decelerations
EFFORT_MIN_S = 0.5      # an effort must last at least this long
EPOCH_S = 30
HR_BINS = np.arange(40, 231)  # 1-bpm histogram from 40 to 230 bpm


# ----------------------------------------------------------- remote zip access

def _get(url: str, start: int, end: int, tries: int = 5) -> bytes:
    for k in range(tries):
        try:
            req = urllib.request.Request(url, headers={"Range": f"bytes={start}-{end}"})
            with urllib.request.urlopen(req, timeout=120) as r:
                return r.read()
        except Exception:
            if k == tries - 1:
                raise
            time.sleep(2 ** k)


def central_directory(url: str) -> list[dict]:
    """Members of a remote zip (name, offset of local header, sizes)."""
    with urllib.request.urlopen(urllib.request.Request(url, method="HEAD")) as r:
        size = int(r.headers["Content-Length"])
    tail = _get(url, size - 65536 - 22, size - 1)
    i = tail.rfind(b"PK\x05\x06")
    cd_size, cd_off = struct.unpack("<II", tail[i + 12:i + 20])
    n_entries = struct.unpack("<H", tail[i + 10:i + 12])[0]
    if cd_off == 0xFFFFFFFF or n_entries == 0xFFFF:  # zip64
        j = tail.rfind(b"PK\x06\x06")
        n_entries, cd_size, cd_off = struct.unpack("<QQQ", tail[j + 32:j + 56])
    cd = _get(url, cd_off, cd_off + cd_size - 1)
    out, p = [], 0
    while p < len(cd) and cd[p:p + 4] == b"PK\x01\x02":
        method, = struct.unpack("<H", cd[p + 10:p + 12])
        csize, usize = struct.unpack("<II", cd[p + 20:p + 28])
        nlen, xlen, clen = struct.unpack("<HHH", cd[p + 28:p + 34])
        off, = struct.unpack("<I", cd[p + 42:p + 46])
        name = cd[p + 46:p + 46 + nlen].decode()
        extra = cd[p + 46 + nlen:p + 46 + nlen + xlen]
        q = 0
        while q + 4 <= len(extra):  # zip64 extended information
            hid, hlen = struct.unpack("<HH", extra[q:q + 4])
            if hid == 1:
                vals, r = [], q + 4
                for flag in (usize, csize, off):
                    if flag == 0xFFFFFFFF:
                        vals.append(struct.unpack("<Q", extra[r:r + 8])[0]); r += 8
                    else:
                        vals.append(flag)
                usize, csize, off = vals
            q += 4 + hlen
        out.append({"name": name, "method": method, "csize": csize, "usize": usize, "offset": off})
        p += 46 + nlen + xlen + clen
    return out


def fetch_member(url: str, m: dict) -> bytes:
    head = _get(url, m["offset"], m["offset"] + 29)
    nlen, xlen = struct.unpack("<HH", head[26:30])
    start = m["offset"] + 30 + nlen + xlen
    data = _get(url, start, start + m["csize"] - 1)
    return zlib.decompress(data, -15) if m["method"] == 8 else data


# -------------------------------------------------------------- feature extraction

def _runs(mask: np.ndarray, min_len: int) -> int:
    """Number of runs of True lasting at least min_len samples."""
    d = np.diff(np.concatenate(([0], mask.astype(np.int8), [0])))
    starts, ends = np.flatnonzero(d == 1), np.flatnonzero(d == -1)
    return int(np.sum(ends - starts >= min_len))


def features(raw: bytes, name: str) -> tuple[dict, pd.DataFrame] | None:
    cols = ["player_name", "time", "speed", "heart_rate", "accl_x", "accl_y", "accl_z"]
    df = pq.read_table(io.BytesIO(raw), columns=cols).to_pandas()
    if df.empty:
        return None
    player, day = df["player_name"].iloc[0], name.split("/")[-1][:10]

    # Accelerometer load at 100 Hz (PlayerLoad-type: summed change of acceleration, in g / 100)
    acc = df[["accl_x", "accl_y", "accl_z"]].to_numpy()
    jerk = np.sqrt(np.sum(np.diff(acc, axis=0) ** 2, axis=1))
    df["load"] = np.concatenate(([0.0], jerk)) / 100.0

    # Collapse to the 10 Hz GNSS clock
    g = df.groupby("time", sort=False).agg(speed=("speed", "first"), hr=("heart_rate", "first"),
                                            load=("load", "sum"))
    t = pd.to_timedelta(g.index.astype(str)).total_seconds().to_numpy()
    order = np.argsort(t, kind="stable")
    t, v, hr, load = t[order], g["speed"].to_numpy()[order], g["hr"].to_numpy()[order].astype(float), g["load"].to_numpy()[order]
    dt = np.clip(np.diff(t, append=t[-1] + 0.1), 0, 1.0)  # gaps > 1 s are not moving time

    v = np.clip(v, 0, 11.0)
    dist = v * dt
    sm = pd.Series(v).rolling(5, center=True, min_periods=1).mean().to_numpy()  # 0.5 s
    a = np.gradient(sm, t) if len(t) > 2 else np.zeros_like(sm)
    n_min = int(EFFORT_MIN_S / 0.1)

    hr_ok = (hr >= 40) & (hr <= 230)
    zones = {nm: float(dist[(v >= lo) & (v < hi)].sum()) for nm, lo, hi in zip(ZONE_NAMES, ZONES[:-1], ZONES[1:])}
    row = {
        "player": player, "date": day, "start_s": float(t[0]), "duration_min": float(dt.sum() / 60),
        "distance": float(dist.sum()), **zones,
        "speed_max": float(np.nanpercentile(sm, 99.9)) if len(sm) else np.nan,
        "n_acc": _runs(a > EFFORT_THRESHOLD, n_min), "n_dec": _runs(a < -EFFORT_THRESHOLD, n_min),
        "acc_load": float(load.sum()),
        "hr_coverage": float(hr_ok.mean()), "hr_mean": float(hr[hr_ok].mean()) if hr_ok.any() else np.nan,
        "hr_peak": float(np.percentile(hr[hr_ok], 99.5)) if hr_ok.sum() > 100 else np.nan,
        "hr_hist": np.histogram(hr[hr_ok], bins=np.append(HR_BINS, 231), weights=dt[hr_ok])[0].round(1).tolist(),
    }

    ep = (t - t[0]) // EPOCH_S
    e = pd.DataFrame({"epoch": ep, "dist": dist, "dt": dt, "load": load,
                      "hr": np.where(hr_ok, hr, np.nan), "hr_dt": np.where(hr_ok, dt, 0.0)})
    e["hr_w"] = e["hr"].fillna(0) * e["hr_dt"]
    ag = e.groupby("epoch").agg(dist=("dist", "sum"), dt=("dt", "sum"), load=("load", "sum"),
                                hr_w=("hr_w", "sum"), hr_dt=("hr_dt", "sum")).reset_index()
    ag = ag[ag["dt"] > EPOCH_S * 0.8]
    epochs = pd.DataFrame({
        "player": player, "date": day, "epoch": ag["epoch"].astype(int),
        "speed": ag["dist"] / ag["dt"], "load": ag["load"],
        "hr": np.where(ag["hr_dt"] > EPOCH_S * 0.8, ag["hr_w"] / ag["hr_dt"].replace(0, np.nan), np.nan),
    })
    return row, epochs


# ---------------------------------------------------------------------- driver

def run(archive: str, workers: int, limit: int | None) -> None:
    url = RECORD.format(archive)
    stem = archive.removesuffix(".zip")
    OUT.mkdir(parents=True, exist_ok=True)
    parts = OUT / f"_parts-{stem}"
    parts.mkdir(exist_ok=True)
    members = [m for m in central_directory(url) if m["name"].endswith(".parquet")]
    done = set()
    for f in parts.glob("sessions-*.parquet"):
        done.update(pd.read_parquet(f, columns=["file"])["file"])
    todo = [m for m in members if m["name"] not in done][:limit]
    print(f"{archive}: {len(members)} files, {len(done)} already done, {len(todo)} to do", flush=True)

    rows, eps, k, t0, failed = [], [], len(list(parts.glob("sessions-*.parquet"))), time.time(), 0

    def flush():
        nonlocal rows, eps, k
        if rows:
            pd.DataFrame(rows).to_parquet(parts / f"sessions-{k:05d}.parquet")
            pd.concat(eps).to_parquet(parts / f"epochs-{k:05d}.parquet")
            k, rows, eps = k + 1, [], []

    def work(m):
        res = features(fetch_member(url, m), m["name"])
        if res:
            res[0]["file"] = m["name"]
        return res

    with ThreadPoolExecutor(workers) as ex:
        futures = {ex.submit(work, m): m for m in todo}
        for n, fut in enumerate(as_completed(futures), 1):
            try:
                res = fut.result()
            except Exception as exc:  # one bad file must not stop the run
                failed += 1
                print(f"  FAILED {futures[fut]['name']}: {exc}", flush=True)
                continue
            if res:
                rows.append(res[0]); eps.append(res[1])
            if len(rows) >= 50:
                flush()
            if n % 50 == 0:
                el = time.time() - t0
                print(f"  {n}/{len(todo)}  {el/60:.1f} min  ~{el/n*(len(todo)-n)/60:.0f} min left", flush=True)
    flush()

    s = pd.concat([pd.read_parquet(f) for f in sorted(parts.glob("sessions-*.parquet"))])
    e = pd.concat([pd.read_parquet(f) for f in sorted(parts.glob("epochs-*.parquet"))])
    s.to_parquet(OUT / f"sessions-{stem}.parquet")
    e.to_parquet(OUT / f"epochs-{stem}.parquet")
    print(f"{archive}: {len(s)} sessions, {len(e)} epochs, {failed} failures", flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--archives", nargs="*", default=ARCHIVES)
    ap.add_argument("--workers", type=int, default=28)
    ap.add_argument("--limit", type=int, help="process at most N files per archive (test)")
    a = ap.parse_args()
    for arc in a.archives:
        run(arc, a.workers, a.limit)
    sys.exit(0)
