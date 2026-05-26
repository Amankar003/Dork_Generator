"""
Pipeline Routes — POST /run-daily-pipeline
"""

from fastapi import APIRouter, HTTPException

from services.pipeline import run_daily_pipeline

router = APIRouter()


@router.post("/run-daily-pipeline", summary="Run full daily pipeline")
def run_pipeline():
    """
    Runs the complete daily intelligence pipeline:
    sources → save → LLM-1 trend analysis → LLM-2 dork generation → save recommendations.
    """
    try:
        result = run_daily_pipeline()
        return {
            "status": "success",
            "source_stats": result["source_stats"],
            "trend_count": result["trend_count"],
            "recommendation_count": result["recommendation_count"],
            "recommendations": result["recommendations"],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pipeline failed: {str(e)}")
