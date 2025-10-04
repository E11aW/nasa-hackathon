#!/usr/bin/env python3
"""
fetch_ghg.py
Downloads CAMS (per your working request), ingests values for ONE queued marker, and marks it done.
Run this after users add markers, or on a schedule.

Requirements:
  pip install cdsapi xarray pandas
  # If you keep GRIB: pip install cfgrib  AND install ecCodes (e.g., brew install eccodes)
  # Easier: request NetCDF in CAMS so xarray reads it without cfgrib.
"""

import os, sqlite3, tempfile
from datetime import datetime
import cdsapi
import xarray as xr

ROOT = os.path.dirname(__file__)
DB   = os.path.join(ROOT, "sqlpage", "sqlpage.db")
DATA_DIR = os.path.join(ROOT, "data")
os.makedirs(DATA_DIR, exist_ok=True)

# --- Your exact request (recommend: switch data_format to "netcdf" for simple parsing)
DATASET = "cams-global-greenhouse-gas-forecasts"
REQUEST = {
    "pressure_level": ["1000"],
    "model_level": ["137"],
    "date": ["2025-04-04/2025-10-02"],
    "leadtime_hour": ["0"],
    # Change this to netcdf if you can:
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

def open_ds(path: str):
    try:
        return xr.open_dataset(path)  # NetCDF path
    except Exception:
        # Fall back to GRIB if you used data_format="grib"
        return xr.open_dataset(path, engine="cfgrib")

def nearest_point(ds, lat, lon):
    lat_name = "latitude" if "latitude" in ds.coords else ("lat" if "lat" in ds.coords else None)
    lon_name = "longitude" if "longitude" in ds.coords else ("lon" if "lon" in ds.coords else None)
    if not lat_name or not lon_name:
        raise RuntimeError("Could not find latitude/longitude coords in dataset")
    return ds.sel({lat_name: lat, lon_name: lon}, method="nearest")

def extract_timestamp(ds):
    for k in ("valid_time","time","initial_time","forecast_reference_time"):
        if k in ds.coords:
            v = ds.coords[k].values
            return str(v) if not isinstance(v, datetime) else v.isoformat()
    return datetime.utcnow().isoformat()

def write_rows(conn, marker_id, obs_time, rows):
    conn.executemany(
        "INSERT INTO ghg_observation (marker_id, obs_time, variable, value, unit) VALUES (?,?,?,?,?)",
        [(marker_id, obs_time, var, float(val), unit) for (var, val, unit) in rows]
    )
    conn.commit()

def process_one_job_with_ds(conn, ds, job):
    jid, marker_id, lat, lon = job

    # CAMS files often have time/step dims; take first slice for popup
    d = ds
    for dim in ("time","step"):
        if dim in d.dims:
            d = d.isel({dim: 0})

    pt = nearest_point(d, lat, lon)
    obs_time = extract_timestamp(pt)

    rows = []
    for v in pt.data_vars:
        da = pt[v]
        try:
            val = float(da.values)
        except Exception:
            continue
        unit = da.attrs.get("units", "")
        rows.append((v, val, unit))

    if rows:
        write_rows(conn, marker_id, obs_time, rows)

    conn.execute("UPDATE ghg_fetch_queue SET processed_at=CURRENT_TIMESTAMP WHERE id=?", (jid,))
    conn.commit()
    print(f"Marker {marker_id}: stored {len(rows)} variables @ {obs_time}")

def main():
    conn = sqlite3.connect(DB)
    # Get one unprocessed marker job
    row = conn.execute(
        "SELECT id, marker_id, lat, lon FROM ghg_fetch_queue WHERE processed_at IS NULL ORDER BY enqueued_at LIMIT 1"
    ).fetchone()
    if not row:
        print("No queued jobs.")
        return

    # Download a fresh CAMS file (one file reused for this run)
    out_path = os.path.join(DATA_DIR, "cams_latest.nc")  # .grib if you keep GRIB
    c = cdsapi.Client()
    c.retrieve(DATASET, REQUEST).download(out_path)

    ds = open_ds(out_path)
    process_one_job_with_ds(conn, ds, row)

if __name__ == "__main__":
    main()