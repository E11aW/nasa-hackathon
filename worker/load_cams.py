# worker/load_cams.py
# Pulls CAMS CO2 forecast (surface) and loads latest step into ghg_surface.
# Requires: pip install cdsapi xarray netCDF4
# Setup ADS API key: create ~/.cdsapirc per ADS instructions.

import sqlite3, pathlib, datetime, tempfile
import xarray as xr
import cdsapi

DB = pathlib.Path(__file__).resolve().parents[1] / "sqlpage" / "sqlpage.db"
obs_time = datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

def upsert_points(cur, points, variable):
    cur.executemany(
        "INSERT OR REPLACE INTO ghg_surface(lat,lon,variable,value,obs_time) VALUES (?,?,?,?,?)",
        [(float(lat), float(lon), variable, float(val), obs_time) for (lat, lon, val) in points]
    )

def main():
    c = cdsapi.Client(url="https://ads.atmosphere.copernicus.eu/api", verify=True)
    # Request: CO2, single level (surface), latest run; use a small area/grid for demo speed.
    # Adjust 'time' / 'leadtime_hour' as desired.
    req = {
        "variable": ["carbon_dioxide"],
        "date": "latest",
        "time": "00:00",
        "leadtime_hour": ["0"],            # t=0 forecast step
        "model_level": ["single_levels"],
        "format": "netcdf"
    }
    with tempfile.NamedTemporaryFile(suffix=".nc", delete=False) as tf:
        c.retrieve("cams-global-greenhouse-gas-forecasts", req, tf.name)
        ds = xr.open_dataset(tf.name)

    # CO2 name can vary; look up by contains
    co2 = None
    for v in ds.data_vars:
        if "co2" in v.lower():
            co2 = ds[v]; break
    if co2 is None:
        raise RuntimeError("CO2 variable not found in CAMS file")

    # Take the first time slice
    if "time" in co2.dims:
        co2 = co2.isel(time=0)

    # Subsample grid for speed (every 4th cell); tune as needed
    lats = co2.lat.values[::4]
    lons = co2.lon.values[::4]

    points = []
    for lat in lats:
        # handle 0..360 lon by converting to -180..180
        for lon in lons:
            val = float(co2.sel(lat=lat, lon=lon, method="nearest"))
            lon180 = float(((lon + 180) % 360) - 180)
            points.append((float(lat), lon180, val))

    conn = sqlite3.connect(DB); cur = conn.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS ghg_surface(
        lat REAL, lon REAL, variable TEXT, value REAL, obs_time TEXT,
        PRIMARY KEY(lat, lon, variable, obs_time)
    )""")
    upsert_points(cur, points, "co2")
    conn.commit(); conn.close()
    print(f"Loaded CAMS CO2: {len(points)} points @ {obs_time}")

if __name__ == "__main__":
    main()