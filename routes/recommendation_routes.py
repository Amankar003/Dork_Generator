"""
Recommendation Routes — Today's recommendations, history, source data.
"""

from fastapi import APIRouter

from database import (
    get_today_recommendations,
    get_recommendation_history,
    get_today_source_data,
    get_source_summary,
    get_pipeline_status,
    delete_india_recommendations,
)
from services.market_filter import is_india_market

router = APIRouter()


@router.get("/today-recommendations", summary="Get today's recommendations")
def today_recommendations():
    """Returns today's ready recommendations only."""
    recs = get_today_recommendations()
    
    # Filter out India recommendations, weak dorks, and individual dorks containing site:.in or India
    filtered_recs = []
    for rec in recs:
        if is_india_market(rec):
            continue
        if "dorks" in rec and isinstance(rec["dorks"], list):
            # Only remove dorks that target Indian domains (site:.in)
            # Do NOT remove dorks containing "-india" which is a negative exclusion filter
            rec["dorks"] = [d for d in rec["dorks"] if "site:.in" not in d.lower()]
            if "why_this_dork" in rec and isinstance(rec["why_this_dork"], list):
                rec["why_this_dork"] = [w for w in rec["why_this_dork"] if isinstance(w, dict) and "dork" in w and "site:.in" not in w["dork"].lower()]
        
        # If no active dorks remain, omit
        if not rec.get("dorks"):
            continue
            
        filtered_recs.append(rec)

    summary = get_source_summary()
    status_info = get_pipeline_status()
    return {
        "count": len(filtered_recs),
        "recommendations": filtered_recs,
        "source_summary": summary,
        "pipeline_status": status_info["status"],
        "pipeline_message": status_info["message"],
    }


@router.get("/recommendations/history", summary="Get recommendation history")
def recommendation_history(limit: int = 100):
    """Returns all historical recommendations."""
    recs = get_recommendation_history(limit=limit)
    
    # Filter out India recommendations, weak dorks, and individual dorks containing site:.in or India
    filtered_recs = []
    for rec in recs:
        if is_india_market(rec):
            continue
        if "dorks" in rec and isinstance(rec["dorks"], list):
            rec["dorks"] = [d for d in rec["dorks"] if "site:.in" not in d.lower()]
            if "why_this_dork" in rec and isinstance(rec["why_this_dork"], list):
                rec["why_this_dork"] = [w for w in rec["why_this_dork"] if isinstance(w, dict) and "dork" in w and "site:.in" not in w["dork"].lower()]
        
        # If no active dorks remain, omit
        if not rec.get("dorks"):
            continue
            
        filtered_recs.append(rec)

    return {"count": len(filtered_recs), "recommendations": filtered_recs}


@router.get("/source-data/today", summary="Get today's raw source data")
def today_source_data():
    """Returns today's raw fetched source data."""
    data = get_today_source_data()
    summary = get_source_summary()
    return {"count": len(data), "source_data": data, "summary": summary}


@router.post("/recommendations/cleanup", summary="Delete all Indian market recommendations")
def cleanup_recommendations():
    """Find and delete all recommendations matching the India block criteria."""
    count = delete_india_recommendations()
    return {"status": "success", "message": f"Deleted {count} India recommendations."}

