"""
Dork Optimizer & Lead Intelligence API — FastAPI Entry Point.

Serves both the existing Dork Optimizer dashboard AND the new Lead Intelligence API v1.

Existing endpoints (unchanged):
  POST /run-daily-pipeline
  GET  /today-recommendations
  GET  /recommendations/history
  GET  /source-data/today
  POST /recommendations/cleanup
  POST /dorks/mark-used
  GET  /debug-llm-config
  GET  /                           (dashboard)

New Lead Intelligence API v1 (authenticated):
  POST /api/v1/generate
  POST /api/v1/bulk-generate
  GET  /api/v1/trending-opportunities
  GET  /api/v1/countries
  GET  /api/v1/sectors
  GET  /api/v1/platforms
  GET  /api/v1/health

Run with: python app.py
"""

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import ValidationError
import os

from database import init_db
from routes.pipeline_routes import router as pipeline_router
from routes.recommendation_routes import router as recommendation_router
from routes.dork_routes import router as dork_router
from api.v1.endpoints import router as v1_router
from services.cache_service import init_cache_table
from middleware.auth import init_api_clients_table, ensure_default_clients

# ── Initialize database tables ─────────────────────────────
init_db()
init_cache_table()
init_api_clients_table()
ensure_default_clients()

app = FastAPI(
    title="Dork Optimizer & Lead Intelligence API",
    description=(
        "Dork Optimizer daily pipeline + Lead Intelligence API v1 for LeadPilot.\n\n"
        "**Existing Dashboard**: Visit `/` for the dashboard UI.\n\n"
        "**Lead Intelligence API v1**: All `/api/v1/*` endpoints require `X-API-KEY` header."
    ),
    version="2.0.0",
)


# ═══════════════════════════════════════════════════════════
# GLOBAL EXCEPTION HANDLERS
# ═══════════════════════════════════════════════════════════
@app.exception_handler(ValidationError)
async def validation_exception_handler(request: Request, exc: ValidationError):
    """Handle Pydantic validation errors with structured JSON response."""
    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "error": "ValidationError",
            "message": str(exc.errors()[0]["msg"]) if exc.errors() else str(exc),
            "generated_count": 0,
            "dorks": [],
        },
    )


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    """Handle ValueError with structured JSON response."""
    return JSONResponse(
        status_code=400,
        content={
            "success": False,
            "error": "BadRequest",
            "message": str(exc),
            "generated_count": 0,
            "dorks": [],
        },
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """Catch-all handler — returns structured JSON for any unhandled exception."""
    # Only apply to /api/* paths
    if request.url.path.startswith("/api/"):
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": "InternalError",
                "message": str(exc),
                "generated_count": 0,
                "dorks": [],
            },
        )
    # For non-API paths, let FastAPI handle normally
    raise exc


# ═══════════════════════════════════════════════════════════
# CORS
# ═══════════════════════════════════════════════════════════
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ═══════════════════════════════════════════════════════════
# EXISTING ROUTES (unchanged)
# ═══════════════════════════════════════════════════════════
app.include_router(pipeline_router)
app.include_router(recommendation_router)
app.include_router(dork_router)

# ═══════════════════════════════════════════════════════════
# NEW: LEAD INTELLIGENCE API v1
# ═══════════════════════════════════════════════════════════
app.include_router(v1_router)

# ═══════════════════════════════════════════════════════════
# SERVE FRONTEND (must be last to avoid route conflicts)
# ═══════════════════════════════════════════════════════════
frontend_dir = os.path.join(os.path.dirname(__file__), "frontend")
if os.path.exists(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="frontend")


@app.get("/", summary="Dashboard")
def serve_dashboard():
    """Serve the dashboard HTML."""
    index_path = os.path.join(frontend_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "Dork Optimizer API is running. Visit /docs for API documentation."}


@app.get("/debug-llm-config", summary="Debug LLM Config")
def debug_llm_config():
    """Return current LLM config without exposing the actual API key."""
    from config import LLM_PROVIDER, TREND_MODEL, DORK_MODEL, BASE_URL, API_KEY
    return {
        "provider": LLM_PROVIDER,
        "trend_model": TREND_MODEL,
        "dork_model": DORK_MODEL,
        "base_url": BASE_URL,
        "api_key_present": bool(API_KEY)
    }


if __name__ == "__main__":
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
