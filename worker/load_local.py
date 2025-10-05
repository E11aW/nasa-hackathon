# worker/load_local.py
# Robust loader for local NetCDFs in /data -> ghg_surface using xarray + h5netcdf.
# - Detects lat/lon (1D or 2D)
# - Picks a real data variable (not bounds)
# - Skips NaN/Inf values so NOT NULL doesn't fail

import sqlite3, pathlib, datetime
import xarray as xr
import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[1]
DB = ROOT / "sqlpage" / "sqlpage.db"
DATA = ROOT / "data"
OBS_TIME = datetime.datetime.now(datetime.UTC).replace(microsecond=0).isoformat().replace("+00:00","Z")

# ---------------- DB helpers ----------------
def upsert(cur, pts, variable):
    cur.executemany(
        "INSERT OR REPLACE INTO ghg_surface(lat,lon,variable,value,obs_time) VALUES (?,?,?,?,?)",
        pts
    )

def lon_to_180(lon):
    return float(((float(lon) + 180.0) % 360.0) - 180.0)

# ---------------- NetCDF helpers ----------------
def open_ds(path):
    try:
        return xr.open_dataset(path, engine="h5netcdf")
    except Exception:
        try:
            return xr.open_dataset(path, engine="scipy")
        except Exception:
            return xr.open_dataset(path)

def is_lat_var(var):
    u = str(var.attrs.get("units","")).lower()
    sn = str(var.attrs.get("standard_name","")).lower()
    ln = str(var.attrs.get("long_name","")).lower()
    nm = var.name.lower()
    return ("degrees_north" in u) or ("latitude" in sn) or ("latitude" in ln) or nm in ("lat","latitude","nav_lat","grid_lat","y")

def is_lon_var(var):
    u = str(var.attrs.get("units","")).lower()
    sn = str(var.attrs.get("standard_name","")).lower()
    ln = str(var.attrs.get("long_name","")).lower()
    nm = var.name.lower()
    return ("degrees_east" in u) or ("longitude" in sn) or ("longitude" in ln) or nm in ("lon","longitude","nav_lon","grid_lon","x")

def pick_lat_lon_vars(ds: xr.Dataset):
    lat_cands = [v for v in ds.variables if is_lat_var(ds[v])]
    lon_cands = [v for v in ds.variables if is_lon_var(ds[v])]
    if not lat_cands:
        for n in ("lat","latitude","nav_lat","grid_lat","y"):
            if n in ds.variables: lat_cands.append(n); break
    if not lon_cands:
        for n in ("lon","longitude","nav_lon","grid_lon","x"):
            if n in ds.variables: lon_cands.append(n); break
    if not lat_cands or not lon_cands:
        raise RuntimeError(f"Could not detect latitude/longitude variables (have: {list(ds.variables)[:30]}...)")
    return lat_cands[0], lon_cands[0]

def looks_like_bounds(name: str):
    n = name.lower()
    return ("bnds" in n) or ("bounds" in n) or n.endswith("_bnds")

def squeeze_time(field: xr.DataArray):
    for dim in list(field.dims):
        d = dim.lower()
        if d in ("time","step","forecast_time","valid_time"):
            field = field.isel({dim: 0})
    return field

def pick_data_var(ds: xr.Dataset, lat_name: str, lon_name: str, prefer_tokens=()):
    lat = ds[lat_name]; lon = ds[lon_name]
    lat_dims = set(lat.dims); lon_dims = set(lon.dims)

    def ok_numeric(v: xr.DataArray):
        return np.issubdtype(v.dtype, np.number)

    def score(varname):
        if looks_like_bounds(varname): return -999
        if varname in (lat_name, lon_name): return -999
        v = ds[varname]
        if not ok_numeric(v): return -50
        vdims = set(v.dims)
        s = 0
        if lat_dims.issubset(vdims): s += 3
        if lon_dims.issubset(vdims): s += 3
        if any(tok in varname.lower() for tok in prefer_tokens): s += 2
        if "time" in vdims: s += 1
        # prefer >=2 dims (a grid)
        if len(vdims) >= 2: s += 2
        return s

    candidates = sorted(ds.data_vars, key=lambda n: score(n), reverse=True)
    for name in candidates:
        if score(name) < 0: break
        v = squeeze_time(ds[name])
        # quick sample to ensure there are finite values
        try:
            sample = v.values
            # for big arrays, just test a few random points
            arr = np.asarray(sample)
            if arr.size == 0: continue
            # test some elements for finiteness
            flat = arr.ravel()
            sample_vals = flat[:: max(1, flat.size // 1000)]
            if np.any(np.isfinite(sample_vals)):
                return name
        except Exception:
            continue
    # last resort: first numeric 2D var
    for name in ds.data_vars:
        v = ds[name]
        if looks_like_bounds(name) or name in (lat_name, lon_name): continue
        if np.issubdtype(v.dtype, np.number) and len(v.dims) >= 2:
            return name
    raise RuntimeError("No suitable numeric 2D data variable found.")

def subsample_points(field: xr.DataArray, lat_var: xr.DataArray, lon_var: xr.DataArray,
                    lat_name: str, lon_name: str,
                    y_stride=4, x_stride=4, lat_stride=4, lon_stride=4):
    pts = []
    # 2D curvilinear grid
    if lat_var.ndim == 2 and lon_var.ndim == 2 and lat_var.dims == lon_var.dims:
        y_name, x_name = lat_var.dims
        y_idx = np.arange(0, lat_var.sizes[y_name], y_stride)
        x_idx = np.arange(0, lon_var.sizes[x_name], x_stride)
        for i in y_idx:
            for j in x_idx:
                lat = float(lat_var.isel({y_name: i, x_name: j}).values)
                lon = float(lon_var.isel({y_name: i, x_name: j}).values)
                val = float(field.isel({y_name: i, x_name: j}).values)
                if np.isfinite(val):
                    pts.append((lat, lon_to_180(lon), "coerce_me", val))  # placeholder, fixed below
        return pts
    # 1D lat/lon
    lats = lat_var.values[::lat_stride]
    lons = lon_var.values[::lon_stride]
    for lat in lats:
        for lon in lons:
            v = field.sel({lat_name: float(lat), lon_name: float(lon)}, method="nearest")
            val = float(v.values)
            if np.isfinite(val):
                pts.append((float(lat), lon_to_180(lon), "coerce_me", val))
    return pts

# -------------- dataset-specific loaders --------------
def load_any_local(cur, pattern_glob: str, prefer_tokens, var_label: str,
                stride_xy=(4,4), stride_ll=(4,4)):
    files = sorted(DATA.glob(pattern_glob))
    if not files:
        print(f"[WARN] No files match: {pattern_glob}")
        return 0
    ds = open_ds(files[-1])
    lat_name, lon_name = pick_lat_lon_vars(ds)
    data_name = pick_data_var(ds, lat_name, lon_name, prefer_tokens=prefer_tokens)
    field = squeeze_time(ds[data_name])

    print(f"[load] file='{files[-1].name}' var='{data_name}' dims={field.dims} lat='{lat_name}' lon='{lon_name}'")

    pts = subsample_points(
        field, ds[lat_name], ds[lon_name], lat_name, lon_name,
        y_stride=stride_xy[0], x_stride=stride_xy[1],
        lat_stride=stride_ll[0], lon_stride=stride_ll[1]
    )
    # filter out any accidental non-finite values (extra safety)
    clean = [(lat, lon, var_label, val) for (lat, lon, _, val) in pts if np.isfinite(val)]
    if not clean:
        print(f"[WARN] No finite values found for {var_label} in {files[-1].name}")
        return 0

    # prepare tuples in DB shape
    rows = [(lat, lon, var_label, val, OBS_TIME) for (lat, lon, _, val) in clean]
    upsert(cur, rows, var_label)
    print(f"Loaded {var_label} points: {len(rows)}")
    return len(rows)

def load_cams_local(cur):
    # If your CAMS files don’t contain 'co2' token, this still picks the best numeric 2D var
    return load_any_local(cur, "CAMS global greenhouse gas forecasts *.nc",
                        prefer_tokens=("co2","carbon_dioxide","co2_concentration"),
                        var_label="co2",
                        stride_xy=(4,4), stride_ll=(4,4))

def load_agro_local(cur):
    return load_any_local(cur, "Agroclimatic indicators from 1951 to 2099*.nc",
                        prefer_tokens=("precip","pr","rain","gsl","growing_season_length"),
                        var_label="precip",
                        stride_xy=(2,2), stride_ll=(2,2))

# ---------------- main ----------------
def main():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS ghg_surface(
    lat REAL, lon REAL, variable TEXT, value REAL, obs_time TEXT,
    PRIMARY KEY(lat, lon, variable, obs_time)
    )
    """)
    try:
        load_cams_local(cur)
    except Exception as e:
        print(f"[WARN] CAMS load failed: {e}")
    try:
        load_agro_local(cur)
    except Exception as e:
        print(f"[WARN] Agro load failed: {e}")
    conn.commit(); conn.close()
    print(f"Done @ {OBS_TIME}")

if __name__ == "__main__":
    main()