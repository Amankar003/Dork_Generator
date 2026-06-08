"""
Opportunity Service — Trending opportunity detection.

Wraps existing trend analysis and recommendation data to expose
trending opportunities via the Lead Intelligence API.
"""

from database import get_today_recommendations, get_today_trends
from services.market_filter import is_india_market


def get_trending_opportunities() -> list[dict]:
    """Get current trending opportunities from existing recommendation and trend data.

    Pulls from today's recommendations first, falls back to trends.
    Returns a list of opportunity dicts ready for API consumption.
    """
    opportunities = []

    # 1. Pull from recommendations (already contain dorks + keywords)
    recs = get_today_recommendations()
    for rec in recs:
        if is_india_market(rec):
            continue

        # Filter out site:.in dorks
        dorks = rec.get("dorks", [])
        if isinstance(dorks, list):
            dorks = [d for d in dorks if "site:.in" not in d.lower()]

        if not dorks:
            continue

        opportunities.append({
            "trend_name": rec.get("trend_name", ""),
            "country": rec.get("country", ""),
            "region": rec.get("region", ""),
            "sector": rec.get("sector", ""),
            "domain": rec.get("domain", ""),
            "recommended_service": rec.get("recommended_service", ""),
            "confidence_score": rec.get("opportunity_score", 0),
            "why_this_region": "",
            "why_this_sector": "",
            "keywords": rec.get("keywords", []),
            "dorks": dorks[:10],
            "opportunity_score": rec.get("opportunity_score", 0),
        })

    # 2. If no recommendations, pull from trends
    if not opportunities:
        trends = get_today_trends()
        for trend in trends:
            if is_india_market(trend):
                continue

            opportunities.append({
                "trend_name": trend.get("trend_name", ""),
                "country": trend.get("country", ""),
                "region": trend.get("region", ""),
                "sector": trend.get("sector", ""),
                "domain": trend.get("domain", ""),
                "recommended_service": trend.get("recommended_service", ""),
                "confidence_score": trend.get("confidence_score", 0),
                "why_this_region": trend.get("why_this_region", ""),
                "why_this_sector": trend.get("why_this_sector", ""),
                "keywords": [],
                "dorks": [],
                "opportunity_score": trend.get("confidence_score", 0),
            })

    # Sort by score descending
    opportunities.sort(key=lambda x: x.get("opportunity_score", 0), reverse=True)
    return opportunities[:50]
