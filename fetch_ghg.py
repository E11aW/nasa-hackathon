#!/usr/bin/env python3
"""
fetch_ghg.py  (NetCDF, process ALL queued markers)

- Uses an existing NetCDF in ./data if found (fast).
- Otherwise downloads one from ADS.
- Opens .nc via netcdf4 (fallback to h5netcdf).
- Inserts rows into ghg_observation and marks jobs processed.

Requires (in your venv):
  pip install cdsapi xarray netcdf4 h5netcdf cftime pandas
"""

import os, sqlite3, glob, time
from datetime import datetime
import xarray as xr

# Optional (only needed if we must download)
try:
    import cdsapi
except Exception:
    cdsapi = None

ROOT = os.path.dirname(__file__)
DB   = os.path.join(ROOT, "sqlpage", "sqlpage.db")
DATA_DIR = os.path.join(ROOT, "data")
os.makedirs(DATA_DIR, exist_ok=True)

# ADS dataset + request (kept as NetCDF)
DATASET = "cams-global-greenhouse-gas-forecasts"
REQUEST = {
    "pressure_level": ["1000"],
    "model_level": ["137"],
    "date": ["2025-04-04/2025-10-02"],
    "leadtime_hour": ["0"],
    "data_format": "netcdf",
    "variable": [
        "ch4_column_mean_molar_fraction",
        "co2_column_mean_molar_fraction",
        "total_column_carbon_monoxide",
        "accumulated_carbon_dioxide_ecosystem_respiration",
        "accumulated_carbon_dioxide_gross_primary_production",
        "accumulated_carbon_dioxide_net_ecosystem_exchange",
        "flux_of_carbon_dioxide_ecosystem_respiration",
        "flux_of_carbon_dioxide_gross_primary_production",
        "flux_of_carbon_dioxide_net_ecosystem_exchange",
        "gpp_coefficient_from_biogenic_flux_adjustment_system",
        "rec_coefficient_from_biogenic_flux_adjustment_system",
        "land_sea_mask",
        "carbon_dioxide",
        "carbon_monoxide",
        "methane"
    ]
}

def pick_existing_nc() -> str | None:
    """Prefer ./data/cams_latest.nc, else most recent *.nc under data/."""
    preferred = os.path.join(DATA_DIR, "cams_latest.nc")
    if os.path.exists(preferred) and os.path.getsize(preferred) > 0:
        return preferred
    candidates = sorted(
        glob.glob(os.path.join(DATA_DIR, "*.nc")),
        key=lambda p: os.path.getmtime(p),
        reverse=True
    )
    return candidates[0] if candidates else None

def ensure_nc_file() -> str:
    """Return path to a NetCDF we can use (existing or freshly downloaded)."""
    existing = pick_existing_nc()
    if existing:
        print(f"[USE] Using existing NetCDF: {existing}")
        return existing
    if cdsapi is None:
        raise RuntimeError("No NetCDF in ./data and cdsapi not available to download one.")
    out_path = os.path.join(DATA_DIR, "cams_latest.nc")
    print("[DL] Requesting CAMS file from ADS…")
    cdsapi.Client(url="https://ads.atmosphere.copernicus.eu/api").retrieve(DATASET, REQUEST).download(out_path)
    print(f"[DL] Saved: {out_path}")
    return out_path

def open_ds(path: str):
    """Open .nc using netcdf4; fallback to h5netcdf with clear error if both fail."""
    try:
        return xr.open_dataset(path, engine="netcdf4")
    except Exception as e1:
        try:
            return xr.open_dataset(path, engine="h5netcdf")
        except Exception as e2:
            raise RuntimeError(
                f"Failed to open NetCDF with netcdf4 ({e1}) or h5netcdf ({e2}). "
                "Install: pip install netcdf4 h5netcdf cftime"
            )

def nearest_point(ds, lat, lon):
    latn = "latitude" if "latitude" in ds.coords else ("lat" if "lat" in ds.coords else None)
    lonn = "longitude" if "longitude" in ds.coords else ("lon" if "lon" in ds.coords else None)
    if not latn or not lonn:
        raise RuntimeError("Dataset missing latitude/longitude coords")
    return ds.sel({latn: lat, lonn: lon}, method="nearest")

def extract_timestamp(ds):
    for k in ("valid_time","time","initial_time","forecast_reference_time"):
        if k in ds.coords:
            v = ds.coords[k].values
            return str(v) if not isinstance(v, datetime) else v.isoformat()
    return datetime.utcnow().isoformat()

def write_rows(conn, marker_id, obs_time, rows):
    if not rows:
        return 0
    conn.executemany(
        "INSERT INTO ghg_observation (marker_id, obs_time, variable, value, unit) VALUES (?,?,?,?,?)",
        [(marker_id, obs_time, var, float(val), unit) for (var, val, unit) in rows]
    )
    conn.commit()
    return len(rows)

def process_one(conn, ds, job):
    jid, marker_id, lat, lon = job
    d = ds
    # Many files are time/step multidimensional; take first for popup
    for dim in ("time","step"):
        if dim in d.dims:
            d = d.isel({dim: 0})

    pt = nearest_point(d, lat, lon)
    obs_time = extract_timestamp(pt)

    rows = []
    for v in pt.data_vars:
        da = pt[v]
        try:
            val = float(getattr(da, "values"))
        except Exception:
            continue
        unit = da.attrs.get("units", "")
        rows.append((v, val, unit))

    n = write_rows(conn, marker_id, obs_time, rows)
    conn.execute("UPDATE ghg_fetch_queue SET processed_at=CURRENT_TIMESTAMP WHERE id=?", (jid,))
    conn.commit()
    print(f"[OK] job {jid} marker {marker_id}: inserted {n} vars @ {obs_time}")

def main():
    print("[INFO] DB:", DB)
    nc_path = ensure_nc_file()
    ds = open_ds(nc_path)

    conn = sqlite3.connect(DB)
    qn = conn.execute("SELECT COUNT(*) FROM ghg_fetch_queue WHERE processed_at IS NULL").fetchone()[0]
    print(f"[INFO] queued jobs: {qn}")

    while True:
        row = conn.execute(
            "SELECT id, marker_id, lat, lon FROM ghg_fetch_queue WHERE processed_at IS NULL ORDER BY enqueued_at LIMIT 1"
        ).fetchone()
        if not row:
            print("[DONE] no more jobs.")
            break
        print(f"[JOB] processing: {row}")
        try:
            process_one(conn, ds, row)
        except Exception as e:
            print(f"[ERR] job {row[0]} failed: {e}")
            time.sleep(1)

    rows = conn.execute(
        "SELECT marker_id, COUNT(*) AS n, MAX(obs_time) AS latest FROM ghg_observation GROUP BY 1 ORDER BY marker_id DESC"
    ).fetchall()
    if rows:
        print("[INFO] observation counts:")
        for r in rows:
            print("   marker", r[0], "->", r[1], "rows (latest:", r[2], ")")
    conn.close()

if __name__ == "__main__":
    main()