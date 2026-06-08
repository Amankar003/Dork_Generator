"""
Intelligence Service — Main orchestrator for Lead Intelligence API.

This is the primary entry point that LeadPilot calls.
Orchestrates: Keyword Engine → Dork Engine → Scoring → Response.

Reuses ALL existing business logic from:
  - services/keyword_service.py (keyword enrichment)
  - services/dork_service.py   (dork generation)
  - llm/dork_generator.py      (core generation engine)
  - config.py                  (LLM client)
"""

import time
import hashlib
import json

from services.keyword_service import resolve_sector, get_sector_keywords, enrich_keywords_with_llm
from services.dork_service import generate_dorks, generate_target_urls
from config import DORK_MODEL


def generate_intelligence(
    industry: str,
    country: str,
    target_role: str | None = None,
    business_type: str | None = None,
    platform: str | None = None,
    region: str | None = None,
) -> dict:
    """Generate complete lead intelligence for a single request.

    This is the main orchestration function that:
    1. Resolves industry → sector
    2. Generates/enriches keywords via LLM
    3. Generates dorks via deterministic engine
    4. Generates target URLs
    5. Returns structured response

    Args:
        industry: Industry/sector (e.g., "Healthcare")
        country: Target country (e.g., "UAE")
        target_role: Optional decision-maker role (e.g., "CEO")
        business_type: Optional specific business type (e.g., "Hospital")
        platform: Optional platform focus (e.g., "LinkedIn")
        region: Optional specific city/region

    Returns:
        Dict matching GenerateResponse schema
    """
    start_time = time.time()

    # 1. Resolve sector
    sector = resolve_sector(industry)

    # 2. Get keywords (LLM-enriched with fallback)
    keywords, opportunity_score, why_opportunity = enrich_keywords_with_llm(
        industry=industry,
        country=country,
        target_role=target_role,
        business_type=business_type,
    )

    # Ensure keywords is a list
    if not isinstance(keywords, list):
        keywords = get_sector_keywords(sector)

    # 3. Generate dorks
    dorks, why_this_dork = generate_dorks(
        keywords=keywords,
        country=country,
        region=region,
        platform=platform,
        target_role=target_role,
        business_type=business_type,
    )

    # 4. Generate target URLs
    target_urls = generate_target_urls(keywords, country, region)

    # 5. Build response
    processing_time = round(time.time() - start_time, 2)

    return {
        "success": True,
        "industry": industry,
        "country": country,
        "keywords": keywords[:10],
        "dorks": dorks,
        "target_urls": target_urls,
        "opportunity_score": opportunity_score,
        "why_this_opportunity": why_opportunity or f"High-potential B2B lead opportunity in {industry} sector in {country}.",
        "generated_count": len(dorks),
        "metadata": {
            "processing_time": processing_time,
            "industry": industry,
            "country": country,
            "platform": platform or "All",
            "target_role": target_role,
            "business_type": business_type,
            "region": region,
            "model_used": DORK_MODEL,
            "cached": False,
        },
    }


def generate_cache_key(
    industry: str,
    country: str,
    target_role: str | None = None,
    business_type: str | None = None,
    platform: str | None = None,
    region: str | None = None,
) -> str:
    """Generate a deterministic cache key for a generation request."""
    raw = "|".join([
        (industry or "").strip().lower(),
        (country or "").strip().lower(),
        (target_role or "").strip().lower(),
        (business_type or "").strip().lower(),
        (platform or "all").strip().lower(),
        (region or "").strip().lower(),
    ])
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
