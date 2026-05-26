"""
Dork Optimizer — FastAPI Entry Point.

Simple backend server with 5 endpoints.
Run with: python app.py
"""

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

from database import init_db
from routes.pipeline_routes import router as pipeline_router
from routes.recommendation_routes import router as recommendation_router
from routes.dork_routes import router as dork_router

# Initialize database
init_db()

app = FastAPI(
    title="Dork Optimizer API",
    description="Simple daily pipeline: sources → trend analysis → dork generation → recommendations",
    version="1.0.0",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routes
app.include_router(pipeline_router)
app.include_router(recommendation_router)
app.include_router(dork_router)

# Serve frontend
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
