"""
Keyword Service — Keyword extraction and enrichment.

Reuses existing LLM call infrastructure and sector-to-keyword mappings
from llm/dork_generator.py. Does NOT duplicate any logic.
"""

from llm.dork_generator import SECTOR_TO_KEYWORDS
from config import call_llm, extract_json_from_response, DORK_MODEL


def resolve_sector(industry: str) -> str:
    """Map a user-facing industry name to an internal sector key.

    Handles exact matches, substring matches, and common aliases.
    Returns lowercase sector key compatible with SECTOR_TO_KEYWORDS.
    """
    if not industry:
        return "b2b services"

    industry_lower = industry.strip().lower()

    # Direct match
    if industry_lower in SECTOR_TO_KEYWORDS:
        return industry_lower

    # Alias map for common variations
    aliases = {
        "health": "healthcare",
        "medical": "healthcare",
        "hospital": "healthcare",
        "dental": "healthcare",
        "clinic": "healthcare",
        "hotel": "tourism",
        "travel": "tourism",
        "hospitality": "tourism",
        "resort": "tourism",
        "property": "real estate",
        "realty": "real estate",
        "construction": "real estate",
        "shop": "ecommerce",
        "retail": "ecommerce",
        "online store": "ecommerce",
        "shopify": "ecommerce",
        "tech": "ai digital transformation",
        "software": "ai digital transformation",
        "it": "ai digital transformation",
        "digital": "ai digital transformation",
        "ai": "ai digital transformation",
        "automation": "ai digital transformation",
        "factory": "manufacturing",
        "industrial": "manufacturing",
        "export": "manufacturing",
        "wedding": "wedding events",
        "event": "wedding events",
        "catering": "wedding events",
        "school": "education",
        "training": "education",
        "university": "education",
        "coaching": "education",
        "consulting": "b2b services",
        "agency": "b2b services",
        "marketing": "b2b services",
        "accounting": "b2b services",
        "legal": "b2b services",
        "law": "b2b services",
        "finance": "b2b services",
        "logistics": "b2b services",
        "visa": "immigration",
        "immigration": "immigration",
        "migration": "immigration",
        "study abroad": "immigration",
    }

    # Exact alias
    if industry_lower in aliases:
        return aliases[industry_lower]

    # Substring match
    for alias, sector in aliases.items():
        if alias in industry_lower or industry_lower in alias:
            return sector

    # Substring match in sector keys
    for sector_key in SECTOR_TO_KEYWORDS:
        if industry_lower in sector_key or sector_key in industry_lower:
            return sector_key

    return "b2b services"


def get_sector_keywords(sector: str) -> list[str]:
    """Get predefined keywords for a sector. Reuses SECTOR_TO_KEYWORDS from dork_generator."""
    return SECTOR_TO_KEYWORDS.get(sector, SECTOR_TO_KEYWORDS.get("b2b services", []))


def enrich_keywords_with_llm(
    industry: str,
    country: str,
    target_role: str | None = None,
    business_type: str | None = None,
) -> list[str]:
    """Use LLM to generate enriched keywords for a specific industry + country + role.

    Falls back to sector keywords if LLM fails.
    """
    sector = resolve_sector(industry)
    base_keywords = get_sector_keywords(sector)

    role_hint = f"\nTarget decision-maker: {target_role}" if target_role else ""
    biz_hint = f"\nBusiness type: {business_type}" if business_type else ""

    prompt = f"""Generate 8-12 highly specific B2B lead-generation keywords for finding businesses in the {industry} sector in {country}.{role_hint}{biz_hint}

These keywords will be used in Google search dorks to find business contact details, emails, phone numbers.

Existing seed keywords for this sector: {', '.join(base_keywords[:5])}

Return ONLY valid JSON (no markdown, no explanation):
{{
  "keywords": ["keyword1", "keyword2", ...],
  "opportunity_score": 85,
  "why_this_opportunity": "One sentence explaining why this is a good lead opportunity"
}}"""

    system_prompt = """You are a B2B lead generation keyword expert. Generate highly specific, actionable keywords for Google dork-based lead extraction. Focus on business types, not generic terms."""

    try:
        raw = call_llm(prompt=prompt, system_prompt=system_prompt, model=DORK_MODEL, temperature=0.3)
        result = extract_json_from_response(raw)

        if isinstance(result, dict) and "keywords" in result:
            llm_keywords = result.get("keywords", [])
            if llm_keywords and isinstance(llm_keywords, list):
                return llm_keywords, result.get("opportunity_score", 80), result.get("why_this_opportunity", "")

    except Exception as e:
        print(f"[KeywordService] LLM enrichment failed: {e}")

    # Fallback: use sector keywords
    return base_keywords[:8], 70, f"B2B opportunity in {industry} sector in {country}"
