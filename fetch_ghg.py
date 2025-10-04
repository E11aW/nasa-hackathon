#!/usr/bin/env python3
import os, sqlite3, tempfile, json
from datetime import datetime
import cdsapi
import xarray as xr

DB = os.path.join(os.path.dirname(__file__), "..", "sqlpage", "sqlpage.db")

# Keep your ~/.cdsapirc set with your CDS key (required by cdsapi)

DATASET = "cams-global-greenhouse-gas-forecasts"

# Request a tiny bbox around each marker to keep files small (0.25° grid)
def cams_request(lat, lon, date_from="2025-04-04", date_to="2025-10-02"):
    dlat = 0.25
    dlon = 0.25
    north = lat + dlat
    south = lat - dlat
    west  = lon - dlon
    east  = lon + dlon

    return {
        "date": [f"{date_from}/{date_to}"],
        "time": ["00:00"],
        "leadtime_hour": ["0"],
        "type": ["forecast"],
        "format": "grib",
        # Some CAMS endpoints use 'area' as N/W/S/E and 'grid' as "0.25/0.25"
        "area": [north, west, south, east],
        "grid": "0.25/0.25",
        # Request a tractable subset (adjust to your needs)
        "variable": [
            "carbon_dioxide",
            "methane",
            "carbon_monoxide",
            "co2_column_mean_molar_fraction",
            "ch4_column_mean_molar_fraction",
            "total_column_carbon_monoxide"
        ],
        # A minimal pressure/model level set (var dependent, remove if unsupported)
        "pressure_level": ["1000"],
    }

def nearest_point(ds, lat, lon):
    """Return ds at nearest lat/lon."""
    lat_name = "latitude" if "latitude" in ds.coords else "lat"
    lon_name = "longitude" if "longitude" in ds.coords else "lon"
    return ds.sel({lat_name: lat, lon_name: lon}, method="nearest")

def save_observations(conn, marker_id, ts_iso, rows):
    conn.executemany(
        "INSERT INTO ghg_observation (marker_id, obs_time, variable, value, unit) VALUES (?,?,?,?,?)",
        [(marker_id, ts_iso, var, val, unit) for (var, val, unit) in rows]
    )
    conn.commit()

def process_one_job(conn, job):
    jid, marker_id, lat, lon = job
    print(f"Fetching CAMS for marker {marker_id} at {lat},{lon}")
    req = cams_request(lat, lon)

    with tempfile.TemporaryDirectory() as d:
        out = os.path.join(d, "cams.grib")
        c = cdsapi.Client()
        c.retrieve(DATASET, req).download(out)

        # Open GRIB and take the nearest grid cell to our point
        ds = xr.open_dataset(out, engine="cfgrib")
        # Many CAMS products carry time/step dimensions; take first time slice for demo
        if "time" in ds.dims:
            ds = ds.isel(time=0)
        if "step" in ds.dims:
            ds = ds.isel(step=0)

        ds_pt = nearest_point(ds, lat, lon)

        # Build rows (variable, value, unit)
        rows = []
        for v in ds_pt.data_vars:
            da = ds_pt[v]
            try:
                val = float(da.values)
            except Exception:
                continue
            unit = da.attrs.get("units", "")
            rows.append((v, val, unit))

        ts = ds_pt.coords["valid_time"].values if "valid_time" in ds_pt.coords else ds_pt.coords.get("time", datetime.utcnow()).values
        ts_iso = str(ts) if not isinstance(ts, datetime) else ts.isoformat()

        save_observations(conn, marker_id, ts_iso, rows)

    conn.execute("UPDATE ghg_fetch_queue SET processed_at=CURRENT_TIMESTAMP WHERE id=?", (jid,))
    conn.commit()

def main():
    conn = sqlite3.connect(DB)
    cur = conn.execute(
        "SELECT id, marker_id, lat, lon FROM ghg_fetch_queue WHERE processed_at IS NULL ORDER BY enqueued_at LIMIT 1"
    )
    row = cur.fetchone()
    if not row:
        print("No jobs.")
        return
    process_one_job(conn, row)

if __name__ == "__main__":
    main()