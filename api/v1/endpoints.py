"""
Lead Intelligence API — v1 Endpoints.

Production-grade endpoints for LeadPilot and future products.
All endpoints require X-API-KEY authentication.

Endpoints:
  POST /api/v1/generate              — Single intelligence generation
  POST /api/v1/bulk-generate          — Bulk generation (1-100 requests)
  GET  /api/v1/trending-opportunities — Current trending opportunities
  GET  /api/v1/countries              — Supported countries list
  GET  /api/v1/sectors                — Supported sectors list
  GET  /api/v1/platforms              — Supported platforms list
  GET  /api/v1/health                 — API health check
"""

import time
import asyncio
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, Depends, HTTPException

from models.request_models import (
    GenerateRequest,
    BulkGenerateRequest,
    SUPPORTED_COUNTRIES,
    SUPPORTED_SECTORS,
    SUPPORTED_PLATFORMS,
)
from models.response_models import (
    GenerateResponse,
    GenerateMetadata,
    BulkGenerateResponse,
    TrendingResponse,
    TrendingOpportunity,
    ErrorResponse,
    MetadataListResponse,
)
from services.intelligence_service import generate_intelligence, generate_cache_key
from services.opportunity_service import get_trending_opportunities
from services.cache_service import get_cached_response, set_cached_response, get_cache_stats
from middleware.auth import verify_api_key


router = APIRouter(prefix="/api/v1", tags=["Lead Intelligence API v1"])

# Thread pool for async execution of blocking LLM calls
_executor = ThreadPoolExecutor(max_workers=4)


# ═══════════════════════════════════════════════════════════
# POST /api/v1/generate
# ═══════════════════════════════════════════════════════════
@router.post(
    "/generate",
    response_model=GenerateResponse,
    summary="Generate Lead Intelligence",
    description="Generate keywords, dorks, target URLs, and opportunity scoring for a specific industry + country combination.",
    responses={
        401: {"model": ErrorResponse, "description": "Missing API key"},
        403: {"model": ErrorResponse, "description": "Invalid API key"},
        422: {"model": ErrorResponse, "description": "Validation error"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def generate_endpoint(
    request: GenerateRequest,
    client: dict = Depends(verify_api_key),
):
    """Generate lead intelligence for a single request.

    Authenticated via X-API-KEY header.
    Supports caching — identical requests within 24h return cached results.
    """
    try:
        # Check cache first
        cache_key = generate_cache_key(
            industry=request.industry,
            country=request.country,
            target_role=request.target_role,
            business_type=request.business_type,
            platform=request.platform,
            region=request.region,
        )

        cached = get_cached_response(cache_key)
        if cached:
            # Mark as cached in metadata
            if "metadata" in cached:
                cached["metadata"]["cached"] = True
            print(f"[API] Cache HIT for {request.industry}/{request.country} (client: {client['client_name']})")
            return GenerateResponse(**cached)

        # Generate fresh intelligence (run blocking LLM call in thread pool)
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            _executor,
            lambda: generate_intelligence(
                industry=request.industry,
                country=request.country,
                target_role=request.target_role,
                business_type=request.business_type,
                platform=request.platform,
                region=request.region,
            ),
        )

        # Cache the result
        set_cached_response(cache_key, result)

        print(f"[API] Generated {result.get('generated_count', 0)} dorks for {request.industry}/{request.country} (client: {client['client_name']})")
        return GenerateResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        print(f"[API] Generate error: {e}")
        raise HTTPException(
            status_code=500,
            detail={"success": False, "error": "InternalError", "message": str(e)},
        )


# ═══════════════════════════════════════════════════════════
# POST /api/v1/bulk-generate
# ═══════════════════════════════════════════════════════════
@router.post(
    "/bulk-generate",
    response_model=BulkGenerateResponse,
    summary="Bulk Generate Lead Intelligence",
    description="Generate intelligence for multiple industry+country combinations in a single call (1-100 requests).",
    responses={
        401: {"model": ErrorResponse, "description": "Missing API key"},
        403: {"model": ErrorResponse, "description": "Invalid API key"},
        422: {"model": ErrorResponse, "description": "Validation error"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def bulk_generate_endpoint(
    request: BulkGenerateRequest,
    client: dict = Depends(verify_api_key),
):
    """Generate lead intelligence for multiple requests.

    Processes requests concurrently using thread pool.
    Supports 1-100 requests per call.
    """
    start_time = time.time()
    results = []
    loop = asyncio.get_event_loop()

    async def process_single(req: GenerateRequest) -> GenerateResponse:
        """Process a single request with cache check."""
        cache_key = generate_cache_key(
            industry=req.industry,
            country=req.country,
            target_role=req.target_role,
            business_type=req.business_type,
            platform=req.platform,
            region=req.region,
        )

        cached = get_cached_response(cache_key)
        if cached:
            if "metadata" in cached:
                cached["metadata"]["cached"] = True
            return GenerateResponse(**cached)

        result = await loop.run_in_executor(
            _executor,
            lambda: generate_intelligence(
                industry=req.industry,
                country=req.country,
                target_role=req.target_role,
                business_type=req.business_type,
                platform=req.platform,
                region=req.region,
            ),
        )
        set_cached_response(cache_key, result)
        return GenerateResponse(**result)

    try:
        # Process all requests concurrently
        tasks = [process_single(req) for req in request.requests]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Convert exceptions to error responses
        final_results = []
        for i, r in enumerate(results):
            if isinstance(r, Exception):
                final_results.append(GenerateResponse(
                    success=False,
                    industry=request.requests[i].industry,
                    country=request.requests[i].country,
                ))
            else:
                final_results.append(r)

        total_time = round(time.time() - start_time, 2)
        total_generated = sum(r.generated_count for r in final_results if r.success)

        print(f"[API] Bulk generated {total_generated} dorks across {len(final_results)} requests (client: {client['client_name']})")

        return BulkGenerateResponse(
            success=True,
            total_requested=len(request.requests),
            total_generated=total_generated,
            results=final_results,
            metadata={"processing_time": total_time, "client": client["client_name"]},
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"[API] Bulk generate error: {e}")
        raise HTTPException(
            status_code=500,
            detail={"success": False, "error": "InternalError", "message": str(e)},
        )


# ═══════════════════════════════════════════════════════════
# GET /api/v1/trending-opportunities
# ═══════════════════════════════════════════════════════════
@router.get(
    "/trending-opportunities",
    response_model=TrendingResponse,
    summary="Get Trending Opportunities",
    description="Returns current trending B2B opportunities detected by the pipeline.",
    responses={
        401: {"model": ErrorResponse, "description": "Missing API key"},
        403: {"model": ErrorResponse, "description": "Invalid API key"},
    },
)
async def trending_opportunities_endpoint(
    client: dict = Depends(verify_api_key),
):
    """Get trending opportunities from the existing pipeline data."""
    try:
        opps = get_trending_opportunities()
        return TrendingResponse(
            success=True,
            count=len(opps),
            opportunities=[TrendingOpportunity(**o) for o in opps],
        )
    except Exception as e:
        print(f"[API] Trending opportunities error: {e}")
        raise HTTPException(
            status_code=500,
            detail={"success": False, "error": "InternalError", "message": str(e)},
        )


# ═══════════════════════════════════════════════════════════
# METADATA ENDPOINTS (for LeadPilot dropdowns)
# ═══════════════════════════════════════════════════════════
@router.get(
    "/countries",
    response_model=MetadataListResponse,
    summary="List Supported Countries",
    description="Returns the list of supported target countries for LeadPilot dropdowns.",
)
async def list_countries(client: dict = Depends(verify_api_key)):
    return MetadataListResponse(
        success=True,
        data=SUPPORTED_COUNTRIES,
        count=len(SUPPORTED_COUNTRIES),
    )


@router.get(
    "/sectors",
    response_model=MetadataListResponse,
    summary="List Supported Sectors",
    description="Returns the list of supported industry sectors for LeadPilot dropdowns.",
)
async def list_sectors(client: dict = Depends(verify_api_key)):
    return MetadataListResponse(
        success=True,
        data=SUPPORTED_SECTORS,
        count=len(SUPPORTED_SECTORS),
    )


@router.get(
    "/platforms",
    response_model=MetadataListResponse,
    summary="List Supported Platforms",
    description="Returns the list of supported platforms for dork generation.",
)
async def list_platforms(client: dict = Depends(verify_api_key)):
    return MetadataListResponse(
        success=True,
        data=SUPPORTED_PLATFORMS,
        count=len(SUPPORTED_PLATFORMS),
    )


# ═══════════════════════════════════════════════════════════
# HEALTH CHECK (no auth required)
# ═══════════════════════════════════════════════════════════
@router.get(
    "/health",
    summary="API Health Check",
    description="Returns API health status and cache statistics. No authentication required.",
)
async def health_check():
    cache_stats = get_cache_stats()
    return {
        "success": True,
        "status": "healthy",
        "version": "1.0.0",
        "cache": cache_stats,
    }
