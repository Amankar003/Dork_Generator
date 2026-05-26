"""Debug script to check why dashboard shows no data."""
import sqlite3, json, os

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "dork_optimizer.db")
print(f"DB Path: {DB_PATH}")
print(f"DB exists: {os.path.exists(DB_PATH)}")
print(f"DB size: {os.path.getsize(DB_PATH) if os.path.exists(DB_PATH) else 0} bytes")

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row

# Check what date SQLite thinks "today" is
today = conn.execute("SELECT date('now') as today").fetchone()["today"]
print(f"\nSQLite date('now'): {today}")

# Check all recommendations
print("\n--- ALL RECOMMENDATIONS ---")
rows = conn.execute("SELECT id, recommendation_date, trend_name, country, status, dorks FROM recommendations ORDER BY id DESC LIMIT 20").fetchall()
print(f"Total rows: {len(rows)}")
for r in rows:
    dorks = []
    try:
        dorks = json.loads(r["dorks"] or "[]")
    except:
        pass
    print(f"  id={r['id']} | date={r['recommendation_date']} | status={r['status']} | dorks={len(dorks)} | {r['trend_name'][:60]} | country={r['country']}")

# Check today's specifically
print("\n--- TODAY'S READY RECOMMENDATIONS ---")
rows2 = conn.execute(
    "SELECT id, recommendation_date, trend_name, status, dorks FROM recommendations WHERE recommendation_date = date('now') AND status = 'ready'"
).fetchall()
print(f"Count: {len(rows2)}")

# Check pipeline status
print("\n--- PIPELINE STATUS ---")
try:
    status = conn.execute("SELECT * FROM pipeline_state").fetchall()
    for s in status:
        print(f"  {s['key']}: {s['value'][:200] if s['value'] else 'NULL'}")
except Exception as e:
    print(f"  Error: {e}")

conn.close()
