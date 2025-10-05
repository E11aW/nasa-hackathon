# worker/load_agro.py
# Pulls one agroclimatic indicator (e.g., precipitation) and loads into ghg_surface.
# Requires: cdsapi xarray netCDF4

import sqlite3, pathlib, datetime, tempfile
import xarray as xr
import cdsapi

DB = pathlib.Path(__file__).resolve().parents[1] / "sqlpage" / "sqlpage.db"
obs_time = datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

def upsert(cur, pts, variable):
    cur.executemany(
        "INSERT OR REPLACE INTO ghg_surface(lat,lon,variable,value,obs_time) VALUES (?,?,?,?,?)",
        [(float(lat), float(lon), variable, float(val), obs_time) for (lat, lon, val) in pts]
    )

def main():
    c = cdsapi.Client()  # uses ~/.cdsapirc (CDS key)
    req = {
        "format": "netcdf",
        "variable": ["precipitation"],      # pick an indicator; see dataset docs for full list
        "temporal_aggregation": "annual",
        "experiment": "rcp45",              # example scenario; pick what you need
        "gcm_model": "hadgem2-es",          # one of the CMIP5 models used
        "year": ["2010"],
    }
    with tempfile.NamedTemporaryFile(suffix=".nc", delete=False) as tf:
        c.retrieve("sis-agroclimatic-indicators", req, tf.name)
        ds = xr.open_dataset(tf.name)

    varname = list(ds.data_vars)[0]  # first variable is our indicator
    field = ds[varname]

    points = []
    # dataset is 0.5° global grid (NetCDF-4)
    for lat in field.lat.values[::2]:
        for lon in field.lon.values[::2]:
            val = float(field.sel(lat=lat, lon=lon))
            lon180 = float(((lon + 180) % 360) - 180)
            points.append((float(lat), lon180, val))

    conn = sqlite3.connect(DB); cur = conn.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS ghg_surface(
        lat REAL, lon REAL, variable TEXT, value REAL, obs_time TEXT,
        PRIMARY KEY(lat, lon, variable, obs_time)
    )""")
    upsert(cur, points, "precip")
    conn.commit(); conn.close()
    print(f"Loaded Agroclimatic precip: {len(points)} points @ {obs_time}")

if __name__ == "__main__":
    main()