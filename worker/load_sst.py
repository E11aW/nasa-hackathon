# worker/load_sst.py
# Loads a monthly sea-surface temperature field into ghg_surface.
# If you have a specific ISLSCP II SST file (NetCDF), point to it; otherwise you can
# use an Earthdata/NOAA SST dataset exposed via OPeNDAP and xarray.

import sqlite3, pathlib, datetime
import xarray as xr

DB = pathlib.Path(__file__).resolve().parents[1] / "sqlpage" / "sqlpage.db"
obs_time = datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

# Example: swap this for your ISLSCP II NetCDF file path or OPeNDAP URL
SST_SOURCE = "your_islsciip_sst_monthly.nc"  # or OPeNDAP URL

def main():
    ds = xr.open_dataset(SST_SOURCE)
    # pick the SST variable (names vary by product)
    vname = [v for v in ds.data_vars if "sst" in v.lower()][0]
    sst = ds[vname]
    # take latest time slice
    if "time" in sst.dims:
        sst = sst.isel(time=-1)

    points = []
    for lat in sst.lat.values[::2]:
        for lon in sst.lon.values[::2]:
            val = float(sst.sel(lat=lat, lon=lon))
            lon180 = float(((float(lon) + 180) % 360) - 180)
            points.append((float(lat), lon180, val))

    conn = sqlite3.connect(DB); cur = conn.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS ghg_surface(
        lat REAL, lon REAL, variable TEXT, value REAL, obs_time TEXT,
        PRIMARY KEY(lat, lon, variable, obs_time)
    )""")
    cur.executemany(
        "INSERT OR REPLACE INTO ghg_surface(lat,lon,variable,value,obs_time) VALUES (?,?,?,?,?)",
        [(lat, lon, "sst", val, obs_time) for (lat, lon, val) in points]
    )
    conn.commit(); conn.close()
    print(f"Loaded SST: {len(points)} points @ {obs_time}")

if __name__ == "__main__":
    main()