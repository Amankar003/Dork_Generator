"""
Lead Intelligence API — Request Models.

Pydantic schemas for all API v1 endpoints.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional


# ── Supported values (used for validation and metadata endpoints) ──

SUPPORTED_PLATFORMS = [
    "Google", "LinkedIn", "Facebook", "Shopify", "All"
]

SUPPORTED_SECTORS = [
    "ai digital transformation", "tourism", "real estate", "healthcare",
    "ecommerce", "manufacturing", "wedding events", "education",
    "b2b services", "immigration", "legal", "finance", "logistics",
    "hospitality", "construction", "automotive", "media",
]

SUPPORTED_COUNTRIES = [
    "USA", "UAE", "UK", "Canada", "Australia", "Singapore",
    "Saudi Arabia", "Qatar", "Germany", "France", "Netherlands",
    "New Zealand", "Kuwait", "India",
]


class GenerateRequest(BaseModel):
    """Request model for POST /api/v1/generate."""

    industry: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Industry/sector to target (e.g., Healthcare, Tourism, Real Estate)",
        examples=["Healthcare"],
    )
    country: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Target country (e.g., UAE, UK, USA)",
        examples=["UAE"],
    )
    target_role: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Target decision-maker role (e.g., CEO, CTO, Founder)",
        examples=["CEO"],
    )
    business_type: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Specific business type to target (e.g., Hospital, Hotel, Law Firm)",
        examples=["Hospital"],
    )
    platform: Optional[str] = Field(
        default="All",
        max_length=50,
        description="Platform to focus dorks on (Google, LinkedIn, Facebook, Shopify, All)",
        examples=["LinkedIn"],
    )
    region: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Specific city or region within the country",
        examples=["Dubai"],
    )

    @field_validator("industry")
    @classmethod
    def normalize_industry(cls, v: str) -> str:
        return v.strip()

    @field_validator("country")
    @classmethod
    def normalize_country(cls, v: str) -> str:
        return v.strip()

    @field_validator("platform")
    @classmethod
    def validate_platform(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return "All"
        v = v.strip()
        # Case-insensitive match
        for p in SUPPORTED_PLATFORMS:
            if v.lower() == p.lower():
                return p
        return v  # Allow unknown platforms, just pass through


class BulkGenerateRequest(BaseModel):
    """Request model for POST /api/v1/bulk-generate."""

    requests: list[GenerateRequest] = Field(
        ...,
        min_length=1,
        max_length=100,
        description="List of generation requests (1-100)",
    )
