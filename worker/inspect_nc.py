# worker/inspect_nc.py
# Print variables, dims, and attributes from the newest .nc under ./data

import pathlib, sys
import xarray as xr

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"

def pick_nc():
    files = sorted(DATA_DIR.glob("*.nc"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not files:
        sys.exit("No .nc files found under ./data")
    return files[0]

def open_ds(path: pathlib.Path):
    try:
        return xr.open_dataset(path, engine="netcdf4")
    except Exception:
        try:
            return xr.open_dataset(path, engine="h5netcdf")
        except Exception as e:
            sys.exit(f"Failed to open NetCDF: {e}\nInstall: pip install netcdf4 h5netcdf cftime")

def main():
    nc = pick_nc()
    print(f"=== File ===\n{nc}\n")
    ds = open_ds(nc)
    print("=== Coordinates ===")
    for k in ds.coords:
        da = ds[k]
        print(f"  - {k}: shape={tuple(da.shape)} dtype={da.dtype} attrs={dict(da.attrs)}")
    print("\n=== Data variables ===")
    for k in ds.data_vars:
        da = ds[k]
        dims = ", ".join(da.dims)
        print(f"  - {k}: dims=[{dims}] shape={tuple(da.shape)} dtype={da.dtype}")
        if da.attrs:
            for ak,av in da.attrs.items():
                print(f"      {ak}: {av}")
    print("\nTIP: Choose one variable name above to use with --var in the loader.")

if __name__ == "__main__":
    main()