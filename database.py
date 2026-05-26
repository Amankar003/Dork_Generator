"""
Dork Optimizer — Database Layer.

SQLite connection, 4 tables, all CRUD helpers.
"""

import os
import json
import sqlite3
from config import DB_PATH


def get_db() -> sqlite3.Connection:
    """Return a new SQLite connection with row_factory."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn


def init_db():
    """Create all 4 tables."""
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS source_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_name TEXT,
            source_type TEXT,
            title TEXT,
            url TEXT,
            raw_text TEXT,
            country TEXT,
            region TEXT,
            keyword TEXT,
            published_at TEXT,
            fetched_at TEXT DEFAULT CURRENT_TIMESTAMP,
            source_hash TEXT UNIQUE,
            status TEXT DEFAULT 'fresh'
        );

        CREATE TABLE IF NOT EXISTS trend_analysis (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            analysis_date TEXT DEFAULT (date('now')),
            trend_name TEXT,
            country TEXT,
            region TEXT,
            sector TEXT,
            domain TEXT,
            business_requirements TEXT,
            why_this_region TEXT,
            why_this_sector TEXT,
            recommended_service TEXT,
            confidence_score INTEGER,
            source_ids TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS recommendations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            recommendation_date TEXT DEFAULT (date('now')),
            trend_id INTEGER,
            trend_name TEXT,
            country TEXT,
            region TEXT,
            sector TEXT,
            domain TEXT,
            recommended_service TEXT,
            keywords TEXT,
            dorks TEXT,
            urls TEXT,
            why_this_dork TEXT,
            opportunity_score INTEGER,
            status TEXT DEFAULT 'ready',
            fingerprint TEXT UNIQUE,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS dork_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dork_text TEXT,
            dork_hash TEXT UNIQUE,
            country TEXT,
            region TEXT,
            sector TEXT,
            used_at TEXT DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'used'
        );

        CREATE INDEX IF NOT EXISTS idx_source_data_hash ON source_data(source_hash);
        CREATE INDEX IF NOT EXISTS idx_source_data_fetched ON source_data(fetched_at);
        CREATE INDEX IF NOT EXISTS idx_trend_analysis_date ON trend_analysis(analysis_date);
        CREATE INDEX IF NOT EXISTS idx_recommendations_date ON recommendations(recommendation_date, status);
        CREATE INDEX IF NOT EXISTS idx_recommendations_fingerprint ON recommendations(fingerprint);
        CREATE INDEX IF NOT EXISTS idx_dork_history_hash ON dork_history(dork_hash);

        CREATE TABLE IF NOT EXISTS pipeline_state (
            key TEXT PRIMARY KEY,
            value TEXT
        );
    """)
    conn.commit()
    conn.close()


# ═══════════════════════════════════════════════════════════
# SOURCE DATA
# ═══════════════════════════════════════════════════════════
def save_source_data(items: list[dict]) -> dict:
    """Save source items. Deduplicates via source_hash. Returns insert stats."""
    from services.dedupe import generate_source_hash

    conn = get_db()
    inserted = 0
    skipped = 0
    try:
        for item in items:
            source_hash = generate_source_hash(item)
            try:
                conn.execute(
                    """INSERT OR IGNORE INTO source_data
                       (source_name, source_type, title, url, raw_text, country, region, keyword, published_at, source_hash)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        item.get("source_name", ""),
                        item.get("source_type", ""),
                        item.get("title", ""),
                        item.get("url", ""),
                        item.get("raw_text", ""),
                        item.get("country", ""),
                        item.get("region", ""),
                        item.get("keyword", ""),
                        item.get("published_at", ""),
                        source_hash,
                    ),
                )
                if conn.total_changes:
                    inserted += 1
                else:
                    skipped += 1
            except sqlite3.IntegrityError:
                skipped += 1
        conn.commit()
    finally:
        conn.close()
    return {"inserted": inserted, "skipped": skipped}


def get_today_source_data() -> list[dict]:
    """Get only today's fresh source data."""
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT * FROM source_data WHERE date(fetched_at) = date('now') AND status = 'fresh' ORDER BY id DESC"
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_source_summary() -> dict:
    """Get summary stats of today's source data."""
    conn = get_db()
    try:
        total = conn.execute("SELECT COUNT(*) AS c FROM source_data WHERE date(fetched_at) = date('now')").fetchone()["c"]
        by_source = {}
        rows = conn.execute(
            "SELECT source_name, COUNT(*) AS c FROM source_data WHERE date(fetched_at) = date('now') GROUP BY source_name"
        ).fetchall()
        for r in rows:
            by_source[r["source_name"]] = r["c"]
        has_seed = conn.execute(
            "SELECT COUNT(*) AS c FROM source_data WHERE date(fetched_at) = date('now') AND source_type = 'seed'"
        ).fetchone()["c"] > 0
        return {"total_today": total, "by_source": by_source, "seed_used": has_seed}
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════
# TREND ANALYSIS
# ═══════════════════════════════════════════════════════════
def save_trend_analysis(trends: list[dict]) -> list[dict]:
    """Save trend analysis results. Returns saved trends with IDs."""
    conn = get_db()
    saved = []
    try:
        for trend in trends:
            cur = conn.execute(
                """INSERT INTO trend_analysis
                   (trend_name, country, region, sector, domain, business_requirements,
                    why_this_region, why_this_sector, recommended_service, confidence_score, source_ids)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    trend.get("trend_name", ""),
                    trend.get("country", ""),
                    trend.get("region", ""),
                    trend.get("sector", ""),
                    trend.get("domain", ""),
                    json.dumps(trend.get("business_requirements", [])),
                    trend.get("why_this_region", ""),
                    trend.get("why_this_sector", ""),
                    trend.get("recommended_service", ""),
                    trend.get("confidence_score", 0),
                    json.dumps(trend.get("source_ids", [])),
                ),
            )
            trend["id"] = cur.lastrowid
            saved.append(trend)
        conn.commit()
    finally:
        conn.close()
    return saved


def get_today_trends() -> list[dict]:
    """Get today's trend analysis."""
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT * FROM trend_analysis WHERE analysis_date = date('now') ORDER BY confidence_score DESC"
        ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            try:
                d["business_requirements"] = json.loads(d.get("business_requirements") or "[]")
            except (json.JSONDecodeError, TypeError):
                d["business_requirements"] = []
            try:
                d["source_ids"] = json.loads(d.get("source_ids") or "[]")
            except (json.JSONDecodeError, TypeError):
                d["source_ids"] = []
            result.append(d)
        return result
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════
# RECOMMENDATIONS
# ═══════════════════════════════════════════════════════════
def save_recommendation(rec: dict) -> int:
    """Save or update a recommendation. Deduplicates via fingerprint."""
    from services.dedupe import generate_fingerprint

    fingerprint = generate_fingerprint(
        rec.get("trend_name", ""),
        rec.get("country", ""),
        rec.get("region", ""),
        rec.get("sector", ""),
        rec.get("recommended_service", ""),
    )

    conn = get_db()
    try:
        # Check if fingerprint exists today
        existing = conn.execute(
            "SELECT id, opportunity_score FROM recommendations WHERE fingerprint = ? AND recommendation_date = date('now')",
            (fingerprint,),
        ).fetchone()

        if existing:
            # Update only if new score is higher
            if rec.get("opportunity_score", 0) > (existing["opportunity_score"] or 0):
                conn.execute(
                    """UPDATE recommendations SET
                       keywords = ?, dorks = ?, urls = ?, why_this_dork = ?,
                       opportunity_score = ?, status = ?
                       WHERE id = ?""",
                    (
                        json.dumps(rec.get("keywords", [])),
                        json.dumps(rec.get("dorks", [])),
                        json.dumps(rec.get("urls", [])),
                        json.dumps(rec.get("why_this_dork", [])),
                        rec.get("opportunity_score", 0),
                        rec.get("status", "ready"),
                        existing["id"],
                    ),
                )
                conn.commit()
            return existing["id"]
        else:
            cur = conn.execute(
                """INSERT INTO recommendations
                   (trend_id, trend_name, country, region, sector, domain,
                    recommended_service, keywords, dorks, urls, why_this_dork,
                    opportunity_score, status, fingerprint)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    rec.get("trend_id"),
                    rec.get("trend_name", ""),
                    rec.get("country", ""),
                    rec.get("region", ""),
                    rec.get("sector", ""),
                    rec.get("domain", ""),
                    rec.get("recommended_service", ""),
                    json.dumps(rec.get("keywords", [])),
                    json.dumps(rec.get("dorks", [])),
                    json.dumps(rec.get("urls", [])),
                    json.dumps(rec.get("why_this_dork", [])),
                    rec.get("opportunity_score", 0),
                    rec.get("status", "ready"),
                    fingerprint,
                ),
            )
            conn.commit()
            return cur.lastrowid
    finally:
        conn.close()


def get_today_recommendations() -> list[dict]:
    """Get today's ready recommendations only."""
    from datetime import date
    today_str = str(date.today())
    
    conn = get_db()
    try:
        # 1. Try fetching today's recommendations
        rows = conn.execute(
            """SELECT * FROM recommendations
               WHERE recommendation_date = ? AND status = 'ready'
               ORDER BY opportunity_score DESC""",
            (today_str,)
        ).fetchall()
        
        # 2. Fallback: If empty, get the latest 20 ready recommendations
        if not rows:
            rows = conn.execute(
                """SELECT * FROM recommendations
                   WHERE status = 'ready'
                   ORDER BY id DESC LIMIT 20"""
            ).fetchall()

        return [_parse_recommendation(r) for r in rows]
    finally:
        conn.close()


def get_recommendation_history(limit: int = 100) -> list[dict]:
    """Get all historical recommendations."""
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT * FROM recommendations ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [_parse_recommendation(r) for r in rows]
    finally:
        conn.close()


def _parse_recommendation(row) -> dict:
    """Parse a recommendation row, decoding JSON fields."""
    d = dict(row)
    for field in ["keywords", "dorks", "urls", "why_this_dork"]:
        try:
            d[field] = json.loads(d.get(field) or "[]")
        except (json.JSONDecodeError, TypeError):
            d[field] = []
    return d


# ═══════════════════════════════════════════════════════════
# DORK HISTORY
# ═══════════════════════════════════════════════════════════
def mark_dork_used(dork_text: str, dork_hash: str, country: str = "", region: str = "", sector: str = ""):
    """Mark a dork as used."""
    conn = get_db()
    try:
        conn.execute(
            "INSERT OR IGNORE INTO dork_history (dork_text, dork_hash, country, region, sector) VALUES (?, ?, ?, ?, ?)",
            (dork_text, dork_hash, country, region, sector),
        )
        conn.commit()
    finally:
        conn.close()


def is_dork_used(dork_hash: str) -> bool:
    """Check if a dork hash is already used."""
    conn = get_db()
    try:
        row = conn.execute("SELECT 1 FROM dork_history WHERE dork_hash = ?", (dork_hash,)).fetchone()
        return row is not None
    finally:
        conn.close()


def get_used_dork_hashes() -> set:
    """Get all used dork hashes."""
    conn = get_db()
    try:
        rows = conn.execute("SELECT dork_hash FROM dork_history").fetchall()
        return {r["dork_hash"] for r in rows}
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════
# PIPELINE STATUS
# ═══════════════════════════════════════════════════════════
def save_pipeline_status(status: str, message: str = ""):
    """Save or update the pipeline status and error message."""
    conn = get_db()
    try:
        conn.execute("INSERT OR REPLACE INTO pipeline_state (key, value) VALUES ('status', ?)", (status,))
        conn.execute("INSERT OR REPLACE INTO pipeline_state (key, value) VALUES ('message', ?)", (message,))
        conn.commit()
    finally:
        conn.close()


def get_pipeline_status() -> dict:
    """Get the current pipeline status and message."""
    conn = get_db()
    try:
        # Check if table exists (handles case where db not initialized yet)
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='pipeline_state'")
        if not cursor.fetchone():
            return {"status": "idle", "message": ""}
        
        status_row = conn.execute("SELECT value FROM pipeline_state WHERE key = 'status'").fetchone()
        message_row = conn.execute("SELECT value FROM pipeline_state WHERE key = 'message'").fetchone()
        
        status = status_row["value"] if status_row else "idle"
        message = message_row["value"] if message_row else ""
        return {"status": status, "message": message}
    finally:
        conn.close()


def delete_india_recommendations() -> int:
    """
    Delete old India recommendations and weak/invalid recommendations from SQLite,
    and remove weak dorks from the dorks JSON arrays of existing rows.
    """
    from services.market_filter import is_india_market
    from llm.dork_generator import is_weak_dork
    
    conn = get_db()
    deleted_count = 0
    updated_count = 0
    try:
        # Fetch all recommendations
        cursor = conn.execute("SELECT id, country, region, trend_name, dorks, why_this_dork FROM recommendations")
        rows = cursor.fetchall()
        
        ids_to_delete = []
        for row in rows:
            rec_id = row["id"]
            
            # Reconstruct minimal dict to pass to is_india_market
            item_dict = {
                "country": row["country"],
                "region": row["region"],
                "trend_name": row["trend_name"]
            }
            
            # Try to load dorks list
            dorks_list = []
            dorks_raw = row["dorks"]
            if dorks_raw:
                try:
                    dorks_list = json.loads(dorks_raw)
                except Exception:
                    dorks_list = [dorks_raw]
            
            item_dict["dorks"] = dorks_list
            
            # 1. Check if it is Indian market
            if is_india_market(item_dict):
                ids_to_delete.append(rec_id)
                continue
                
            # 2. Filter out weak dorks
            valid_dorks = [d for d in dorks_list if not is_weak_dork(d)]
            
            # Delete if no valid dorks remain
            if not valid_dorks:
                ids_to_delete.append(rec_id)
            else:
                # Update the row to only contain valid dorks!
                # Let's clean up why_this_dork to match too
                why_raw = row["why_this_dork"]
                why_list = []
                if why_raw:
                    try:
                        why_list = json.loads(why_raw)
                    except Exception:
                        pass
                
                valid_why = []
                if why_list:
                    valid_why = [w for w in why_list if isinstance(w, dict) and "dork" in w and not is_weak_dork(w["dork"])]
                
                # If the dorks list actually changed, update it
                if len(valid_dorks) < len(dorks_list):
                    conn.execute(
                        "UPDATE recommendations SET dorks = ?, why_this_dork = ? WHERE id = ?",
                        (json.dumps(valid_dorks), json.dumps(valid_why), rec_id)
                    )
                    updated_count += 1
                
        if ids_to_delete:
            placeholders = ",".join("?" for _ in ids_to_delete)
            cur = conn.execute(f"DELETE FROM recommendations WHERE id IN ({placeholders})", ids_to_delete)
            deleted_count = cur.rowcount
            
        conn.commit()
    finally:
        conn.close()
    print(f"[Cleanup] Updated dorks list for {updated_count} rows.")
    return deleted_count + updated_count

