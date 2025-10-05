# Worker

Background scripts to feed the map.

## Layout
- process_queue.py — processes `ghg_fetch_queue` → updates `ghg_observation` for factory popups.
- load_* — loads gridded "baseline" fields (e.g., CO₂, NPP, precipitation, SST) into `ghg_surface` for overlays.

## Setup
1) `python3 -m venv .venv && source .venv/bin/activate`
2) `pip install -r requirements.txt`
3) Create `~/.cdsapirc` (CDS/ADS key).  
4) (If using Earthdata) copy `.env.example` to `.env` and fill credentials.

## Run manually
- `python worker/load_cams.py`          # or any other loader
- `python worker/process_queue.py`

## Schedule (cron examples)
Every 2 minutes (queue worker):