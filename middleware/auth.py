"""
Authentication Middleware — API Client Management.

Multi-client API key system with usage tracking.
Supports multiple clients (LeadPilot, Dashboard, Admin, etc.)
with individual API keys, status tracking, and request counting.

Database table: api_clients
"""

import secrets
import os
from datetime import datetime

from fastapi import Header, HTTPException
from database import get_db


def init_api_clients_table():
    """Create the api_clients table if it doesn't exist."""
    conn = get_db()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS api_clients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_name TEXT NOT NULL UNIQUE,
                api_key TEXT NOT NULL UNIQUE,
                status TEXT DEFAULT 'active',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                last_used TEXT,
                request_count INTEGER DEFAULT 0
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_api_clients_key
            ON api_clients(api_key)
        """)
        conn.commit()
    finally:
        conn.close()


def ensure_default_clients():
    """Ensure default API clients exist. Creates them on first run.

    Reads DORK_API_KEY from env as the LeadPilot key.
    Generates keys for Dashboard and Admin if not present.
    """
    conn = get_db()
    try:
        # Check if any clients exist
        count = conn.execute("SELECT COUNT(*) AS c FROM api_clients").fetchone()["c"]
        if count > 0:
            return  # Already initialized

        # Default clients
        leadpilot_key = os.getenv("DORK_API_KEY", "") or os.getenv("LEADPILOT_API_KEY", "")
        if not leadpilot_key:
            leadpilot_key = "lpk_" + secrets.token_hex(24)
            print(f"\n{'=' * 60}")
            print(f"[AUTH] Generated LeadPilot API Key: {leadpilot_key}")
            print(f"[AUTH] Add to .env: DORK_API_KEY={leadpilot_key}")
            print(f"{'=' * 60}\n")

        dashboard_key = "dshk_" + secrets.token_hex(24)
        admin_key = "admk_" + secrets.token_hex(24)

        clients = [
            ("LeadPilot", leadpilot_key, "active"),
            ("Dashboard", dashboard_key, "active"),
            ("Admin", admin_key, "active"),
        ]

        for name, key, status in clients:
            try:
                conn.execute(
                    "INSERT OR IGNORE INTO api_clients (client_name, api_key, status) VALUES (?, ?, ?)",
                    (name, key, status),
                )
            except Exception:
                pass

        conn.commit()

        print("[AUTH] Default API clients created:")
        for name, key, _ in clients:
            print(f"  {name}: {key}")

    except Exception as e:
        print(f"[AUTH] Error creating default clients: {e}")
    finally:
        conn.close()


def verify_api_key(x_api_key: str = Header(..., alias="X-API-KEY")) -> dict:
    """FastAPI dependency that validates the X-API-KEY header.

    Returns the client info dict if valid.
    Raises HTTPException(401) if missing, HTTPException(403) if invalid/inactive.
    """
    if not x_api_key:
        raise HTTPException(
            status_code=401,
            detail={"success": False, "error": "Unauthorized", "message": "X-API-KEY header is required"},
        )

    conn = get_db()
    try:
        row = conn.execute(
            "SELECT id, client_name, api_key, status, request_count FROM api_clients WHERE api_key = ?",
            (x_api_key,),
        ).fetchone()

        if not row:
            raise HTTPException(
                status_code=403,
                detail={"success": False, "error": "Forbidden", "message": "Invalid API key"},
            )

        if row["status"] != "active":
            raise HTTPException(
                status_code=403,
                detail={"success": False, "error": "Forbidden", "message": f"API client '{row['client_name']}' is {row['status']}"},
            )

        # Update usage tracking
        conn.execute(
            "UPDATE api_clients SET last_used = ?, request_count = request_count + 1 WHERE id = ?",
            (datetime.utcnow().isoformat(), row["id"]),
        )
        conn.commit()

        return {
            "client_id": row["id"],
            "client_name": row["client_name"],
            "request_count": row["request_count"] + 1,
        }

    finally:
        conn.close()


def get_all_clients() -> list[dict]:
    """Get all API clients (for admin use)."""
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT id, client_name, api_key, status, created_at, last_used, request_count FROM api_clients ORDER BY id"
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def create_client(client_name: str, api_key: str | None = None) -> dict:
    """Create a new API client. Returns the client info including the API key."""
    if not api_key:
        api_key = "clk_" + secrets.token_hex(24)

    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO api_clients (client_name, api_key, status) VALUES (?, ?, 'active')",
            (client_name, api_key),
        )
        conn.commit()
        return {"client_name": client_name, "api_key": api_key, "status": "active"}
    finally:
        conn.close()


def revoke_client(client_name: str) -> bool:
    """Revoke (deactivate) an API client."""
    conn = get_db()
    try:
        result = conn.execute(
            "UPDATE api_clients SET status = 'revoked' WHERE client_name = ?",
            (client_name,),
        )
        conn.commit()
        return result.rowcount > 0
    finally:
        conn.close()
