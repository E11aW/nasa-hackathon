# worker/process_queue.py
# Processes ghg_fetch_queue and writes ghg_observation records per marker.
# Replace fetch_cams_at() with your real CAMS/NASA lookup.

import sqlite3, time, datetime, random, pathlib, sys

DB = pathlib.Path(__file__).resolve().parents[1] / "sqlpage" / "sqlpage.db"

def fetch_cams_at(lat, lon):
    """
    TODO: Replace with real CAMS retrieval (e.g., from local NetCDF or API).
    Return dict: variable -> (value, unit).
    """
    # Demo: CO2-ish baseline with tiny perturbation
    co2 = 410.0 + ((lat % 1.0) * 5) + ((lon % 1.0) * 5) + random.uniform(-0.5, 0.5)
    return {"co2": (co2, "ppm")}

def main():
    conn = sqlite3.connect(str(DB))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    while True:
        cur.execute("""
            SELECT id, marker_id, lat, lon
            FROM ghg_fetch_queue
            WHERE processed_at IS NULL
            ORDER BY enqueued_at ASC
            LIMIT 1
        """)
        row = cur.fetchone()
        if not row:
            break  # nothing to do

        qid = row["id"]; marker_id = row["marker_id"]
        lat = float(row["lat"]); lon = float(row["lon"])

        try:
            measures = fetch_cams_at(lat, lon)
            obs_time = datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

            for variable, (value, unit) in measures.items():
                cur.execute("""
                    INSERT INTO ghg_observation (marker_id, obs_time, variable, value, unit)
                    VALUES (?, ?, ?, ?, ?)
                """, (marker_id, obs_time, variable, float(value), unit))

            cur.execute("UPDATE ghg_fetch_queue SET processed_at = ? WHERE id = ?", (obs_time, qid))
            conn.commit()
            print(f"Processed marker {marker_id} at ({lat:.4f},{lon:.4f})")
        except Exception as e:
            conn.rollback()
            print("Error processing job", qid, e, file=sys.stderr)
            # leave job unprocessed for retry

    conn.close()

if __name__ == "__main__":
    main()