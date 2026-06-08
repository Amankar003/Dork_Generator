"""
Cache Service — Response caching for Lead Intelligence API.

SQLite-based cache with 24-hour expiry.
Avoids repeated LLM calls for identical requests.
Falls back gracefully if cache is unavailable.
"""

import json
import time
from datetime import datetime, timedelta

from database import get_db


CACHE_TTL_HOURS = 24


def init_cache_table():
    """Create the cache table if it doesn't exist."""
    conn = get_db()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS intelligence_cache (
                cache_key TEXT PRIMARY KEY,
                response_json TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                expires_at TEXT NOT NULL,
                hit_count INTEGER DEFAULT 0
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_cache_expires
            ON intelligence_cache(expires_at)
        """)
        conn.commit()
    finally:
        conn.close()


def get_cached_response(cache_key: str) -> dict | None:
    """Get a cached response if it exists and hasn't expired.

    Returns the cached response dict, or None if not found/expired.
    """
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT response_json, expires_at FROM intelligence_cache WHERE cache_key = ?",
            (cache_key,),
        ).fetchone()

        if not row:
            return None

        # Check expiry
        expires_at = row["expires_at"]
        if datetime.fromisoformat(expires_at) < datetime.utcnow():
            # Expired — delete it
            conn.execute("DELETE FROM intelligence_cache WHERE cache_key = ?", (cache_key,))
            conn.commit()
            return None

        # Update hit count
        conn.execute(
            "UPDATE intelligence_cache SET hit_count = hit_count + 1 WHERE cache_key = ?",
            (cache_key,),
        )
        conn.commit()

        return json.loads(row["response_json"])

    except Exception as e:
        print(f"[Cache] Read error: {e}")
        return None
    finally:
        conn.close()


def set_cached_response(cache_key: str, response: dict):
    """Cache a response with 24-hour expiry."""
    conn = get_db()
    try:
        expires_at = (datetime.utcnow() + timedelta(hours=CACHE_TTL_HOURS)).isoformat()
        response_json = json.dumps(response, default=str)

        conn.execute(
            """INSERT OR REPLACE INTO intelligence_cache
               (cache_key, response_json, expires_at, hit_count)
               VALUES (?, ?, ?, 0)""",
            (cache_key, response_json, expires_at),
        )
        conn.commit()
    except Exception as e:
        print(f"[Cache] Write error: {e}")
    finally:
        conn.close()


def cleanup_expired_cache():
    """Remove all expired cache entries."""
    conn = get_db()
    try:
        now = datetime.utcnow().isoformat()
        result = conn.execute(
            "DELETE FROM intelligence_cache WHERE expires_at < ?", (now,)
        )
        deleted = result.rowcount
        conn.commit()
        if deleted > 0:
            print(f"[Cache] Cleaned up {deleted} expired entries")
        return deleted
    except Exception as e:
        print(f"[Cache] Cleanup error: {e}")
        return 0
    finally:
        conn.close()


def get_cache_stats() -> dict:
    """Get cache statistics."""
    conn = get_db()
    try:
        total = conn.execute("SELECT COUNT(*) AS c FROM intelligence_cache").fetchone()["c"]
        now = datetime.utcnow().isoformat()
        active = conn.execute(
            "SELECT COUNT(*) AS c FROM intelligence_cache WHERE expires_at >= ?", (now,)
        ).fetchone()["c"]
        total_hits = conn.execute(
            "SELECT COALESCE(SUM(hit_count), 0) AS c FROM intelligence_cache"
        ).fetchone()["c"]
        return {"total_entries": total, "active_entries": active, "total_hits": total_hits}
    except Exception:
        return {"total_entries": 0, "active_entries": 0, "total_hits": 0}
    finally:
        conn.close()
