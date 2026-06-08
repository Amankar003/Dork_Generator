"""
Lead Intelligence API — Response Models.

Standardized response schemas for all API v1 endpoints.
Every response has success=true/false for consistent consumption.
"""

from pydantic import BaseModel, Field
from typing import Optional, Any


class GenerateMetadata(BaseModel):
    """Metadata included with every generation response."""
    processing_time: float = Field(description="Processing time in seconds")
    industry: str = ""
    country: str = ""
    platform: str = "All"
    target_role: Optional[str] = None
    business_type: Optional[str] = None
    region: Optional[str] = None
    model_used: str = ""
    cached: bool = False


class GenerateResponse(BaseModel):
    """Response model for POST /api/v1/generate."""
    success: bool = True
    industry: str = ""
    country: str = ""
    keywords: list[str] = Field(default_factory=list)
    dorks: list[str] = Field(default_factory=list)
    target_urls: list[str] = Field(default_factory=list)
    opportunity_score: int = 0
    why_this_opportunity: str = ""
    generated_count: int = 0
    metadata: GenerateMetadata = Field(default_factory=lambda: GenerateMetadata(processing_time=0.0))


class BulkGenerateResponse(BaseModel):
    """Response model for POST /api/v1/bulk-generate."""
    success: bool = True
    total_requested: int = 0
    total_generated: int = 0
    results: list[GenerateResponse] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)


class TrendingOpportunity(BaseModel):
    """Single trending opportunity."""
    trend_name: str = ""
    country: str = ""
    region: str = ""
    sector: str = ""
    domain: str = ""
    recommended_service: str = ""
    confidence_score: int = 0
    why_this_region: str = ""
    why_this_sector: str = ""
    keywords: list[str] = Field(default_factory=list)
    dorks: list[str] = Field(default_factory=list)
    opportunity_score: int = 0


class TrendingResponse(BaseModel):
    """Response model for GET /api/v1/trending-opportunities."""
    success: bool = True
    count: int = 0
    opportunities: list[TrendingOpportunity] = Field(default_factory=list)


class ErrorResponse(BaseModel):
    """Standardized error response — same shape for all error types."""
    success: bool = False
    error: str = ""
    message: str = ""
    generated_count: int = 0
    dorks: list[str] = Field(default_factory=list)


class MetadataListResponse(BaseModel):
    """Response model for metadata list endpoints (countries, sectors, platforms)."""
    success: bool = True
    data: list[str] = Field(default_factory=list)
    count: int = 0
