#!/usr/bin/env python3
import sys, csv, re, os, glob

PATTERN = re.compile(r'sst_(?:climate_1d_1971-2000-(\d{2}))\.asc$', re.IGNORECASE)

def convert_one(asc_path: str):
    fn = os.path.basename(asc_path)
    m = PATTERN.search(fn)
    if not m:
        raise SystemExit(f"Unrecognized SST filename (expect climatology MM): {fn}")
    period = m.group(1)  # '01','04','07','10'
    out_path = asc_path[:-4] + '.csv'  # .asc -> .csv
    r = 0
    wrote = 0
    with open(asc_path, 'r') as f, open(out_path, 'w', newline='') as out:
        w = csv.writer(out)
        for line in f:
            line = line.strip()
            if not line:
                continue
            vals = line.split()
            if len(vals) != 360:
                # defensively skip non-data lines
                continue
            for c, v in enumerate(vals):
                # kind='clim'
                w.writerow(['clim', period, r, c, v])
                wrote += 1
            r += 1
    print(f"Wrote {out_path} ({wrote} cells)")

def main():
    args = sys.argv[1:]
    if not args:
        print("Usage:\n  asc_to_csv.py <asc files...>\n  asc_to_csv.py <directory>")
        sys.exit(2)

    paths = []
    for arg in args:
        if os.path.isdir(arg):
            paths.extend(glob.glob(os.path.join(arg, "sst_climate_1d_1971-2000-*.asc")))
        else:
            paths.extend(glob.glob(arg))

    want = {'01','04','07','10'}
    found = set()
    for p in sorted(paths):
        m = PATTERN.search(os.path.basename(p))
        if m:
            found.add(m.group(1))
    missing = want - found
    if missing:
        print("Missing months:", ", ".join(sorted(missing)))
        # still proceeds with what exists

    if not paths:
        print("No matching .asc files found.")
        sys.exit(2)

    for p in sorted(paths):
        convert_one(p)

if __name__ == "__main__":
    main()