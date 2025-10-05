# worker/load_vemap.py
# Downloads the VEMAP-2 annual ecosystem results bundle from ORNL DAAC (Earthdata login),
# reads a variable (e.g., NPP) from NetCDF/ASCII, and loads into ghg_surface.
# Requires: requests xarray netCDF4

import os, sqlite3, pathlib, zipfile, tempfile, datetime, requests
import xarray as xr

DB = pathlib.Path(__file__).resolve().parents[1] / "sqlpage" / "sqlpage.db"
# Earthdata credentials from environment or .netrc:
ED_USER = os.environ.get("EARTHDATA_USER")
ED_PASS = os.environ.get("EARTHDATA_PASS")
VEMAP_ZIP = "https://data.ornldaac.earthdata.nasa.gov/protected/bundle/vemap-2_results_annual_766.zip"

def earthdata_session():
    s = requests.Session()
    if ED_USER and ED_PASS:
        s.auth = (ED_USER, ED_PASS)
    return s

def upsert_points(cur, pts, variable, obs_time):
    cur.executemany(
        "INSERT OR REPLACE INTO ghg_surface(lat,lon,variable,value,obs_time) VALUES (?,?,?,?,?)",
        [(float(lat), float(lon), variable, float(val), obs_time) for (lat, lon, val) in pts]
    )

def main():
    obs_time = datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
    s = earthdata_session()
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tf:
        r = s.get(VEMAP_ZIP, allow_redirects=True)
        r.raise_for_status()
        tf.write(r.content)
        zpath = tf.name

    # Extract and try to locate a NetCDF (or ASCII) with annual ecosystem variable (e.g., NPP)
    points = []
    with zipfile.ZipFile(zpath) as z:
        z.extractall(pathlib.Path(zpath).parent)
        for name in z.namelist():
            if name.lower().endswith((".nc", ".nc4")):
                ds = xr.open_dataset(pathlib.Path(zpath).parent / name)
                # guess a variable like NPP; adjust to the exact VEMAP variable name in your bundle
                var = None
                for v in ds.data_vars:
                    if v.lower() in ("npp","net_primary_productivity"):
                        var = ds[v]; break
                if var is None:
                    continue
                # take a single time (or aggregate), and subsample grid
                if "time" in var.dims:
                    var = var.isel(time=0)
                lats = var.lat.values[::2]; lons = var.lon.values[::2]
                for lat in lats:
                    for lon in lons:
                        val = float(var.sel(lat=lat, lon=lon, method="nearest"))
                        lon180 = float(((float(lon) + 180) % 360) - 180)
                        points.append((float(lat), lon180, val))
                break  # one variable is enough for now

    conn = sqlite3.connect(DB); cur = conn.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS ghg_surface(
        lat REAL, lon REAL, variable TEXT, value REAL, obs_time TEXT,
        PRIMARY KEY(lat, lon, variable, obs_time)
    )""")
    upsert_points(cur, points, "npp", obs_time)
    conn.commit(); conn.close()
    print(f"Loaded VEMAP-2 NPP: {len(points)} points @ {obs_time}")

if __name__ == "__main__":
    main()