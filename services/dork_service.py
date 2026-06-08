"""
Dork Service — Dork generation for Lead Intelligence API.

Thin adapter that reuses ALL existing logic from llm/dork_generator.py.
Maps LeadPilot-style inputs into the internal structures dork_generator expects.
"""

from llm.dork_generator import (
    resolve_country_metadata,
    generate_dorks_deterministically,
    _clean_and_dedupe_dorks,
    deduplicate_dorks,
    SECTOR_TO_KEYWORDS,
)


def generate_dorks(
    keywords: list[str],
    country: str,
    region: str | None = None,
    platform: str | None = None,
    target_role: str | None = None,
    business_type: str | None = None,
) -> tuple[list[str], list[dict]]:
    """Generate dorks using existing deterministic engine + optional platform filtering.

    Args:
        keywords: List of keywords to build dorks around.
        country: Target country.
        region: Optional target city/region.
        platform: Optional platform filter (LinkedIn, Facebook, Google, Shopify, All).
        target_role: Optional decision-maker role to inject into LinkedIn dorks.
        business_type: Optional business type keyword.

    Returns:
        Tuple of (dorks_list, why_this_dork_list)
    """
    # Resolve country metadata using existing mapper
    country_meta = resolve_country_metadata(country, region or "")
    location = region if region else country

    # Enrich keywords with business_type if provided
    enriched_keywords = list(keywords)
    if business_type and business_type.lower() not in [k.lower() for k in enriched_keywords]:
        enriched_keywords.insert(0, business_type)

    # Generate dorks using existing deterministic engine
    raw_dorks = generate_dorks_deterministically(enriched_keywords, country_meta, location)

    # Add role-specific LinkedIn dorks if target_role is provided
    if target_role:
        phone_code = country_meta.get("phone", "")
        for kw in enriched_keywords[:5]:
            raw_dorks.append(
                f'site:linkedin.com/in ("{target_role}") "{kw}" "{location}" -india -91 -jobs -careers'
            )
            raw_dorks.append(
                f'site:linkedin.com/company "{kw}" "{location}" "{target_role}" -india -91 -jobs -careers'
            )

    # Clean and deduplicate using existing logic
    clean_dorks = _clean_and_dedupe_dorks(raw_dorks)
    clean_dorks = deduplicate_dorks(clean_dorks)

    # Platform filtering (post-generation)
    if platform and platform.lower() != "all":
        clean_dorks = _filter_by_platform(clean_dorks, platform)

        # If platform filtering removed too many, add platform-specific dorks
        if len(clean_dorks) < 5:
            extra = _generate_platform_specific_dorks(
                enriched_keywords, country_meta, location, platform, target_role
            )
            extra_clean = _clean_and_dedupe_dorks(extra)
            existing_lower = {d.lower() for d in clean_dorks}
            for d in extra_clean:
                if d.lower() not in existing_lower:
                    clean_dorks.append(d)
                    existing_lower.add(d.lower())

    # Generate explanations
    why_this_dork = _generate_explanations(clean_dorks, enriched_keywords, location)

    return clean_dorks[:30], why_this_dork[:30]


def _filter_by_platform(dorks: list[str], platform: str) -> list[str]:
    """Filter dorks to only include those targeting a specific platform."""
    platform_lower = platform.lower()

    platform_signals = {
        "linkedin": ["linkedin.com"],
        "facebook": ["facebook.com"],
        "shopify": ["shopify", "powered by shopify"],
        "google": [],  # Google = general web dorks (not social/shopify)
    }

    signals = platform_signals.get(platform_lower, [])

    if platform_lower == "google":
        # Google = everything EXCEPT social/shopify-specific
        social_signals = ["linkedin.com", "facebook.com"]
        return [d for d in dorks if not any(s in d.lower() for s in social_signals)]

    if signals:
        return [d for d in dorks if any(s in d.lower() for s in signals)]

    return dorks


def _generate_platform_specific_dorks(
    keywords: list[str],
    country_meta: dict,
    location: str,
    platform: str,
    target_role: str | None = None,
) -> list[str]:
    """Generate additional dorks specifically for a platform."""
    dorks = []
    phone_code = country_meta.get("phone", "")
    role = target_role or "Founder"

    for kw in keywords[:8]:
        if platform.lower() == "linkedin":
            dorks.append(f'site:linkedin.com/company "{kw}" "{location}" -india -91 -jobs -careers')
            dorks.append(f'site:linkedin.com/in ("{role}" OR "CEO" OR "Founder") "{kw}" "{location}" -india -91 -jobs -careers')
            dorks.append(f'site:linkedin.com/in "{kw}" "{location}" "email" -india -91 -jobs -careers')
        elif platform.lower() == "facebook":
            dorks.append(f'site:facebook.com "About" "{kw}" "{location}" "{phone_code}" -india -91 -jobs -careers')
            dorks.append(f'site:facebook.com "{kw}" "{location}" "info" "contact" -india -91 -jobs -careers')
        elif platform.lower() == "shopify":
            dorks.append(f'"Powered by Shopify" "{kw}" "{location}" "info" "{phone_code}" -india -91 -jobs -careers')
            dorks.append(f'"Shopify" "{kw}" "{location}" inurl:contact "@gmail.com" -india -91 -jobs -careers')

    return dorks


def _generate_explanations(dorks: list[str], keywords: list[str], location: str) -> list[dict]:
    """Generate why_this_dork explanations for each dork. Reuses the same logic pattern as dork_generator.py."""
    why_this_dork = []
    kw0 = keywords[0] if keywords else "business"

    for d in dorks:
        reason = f"Advanced B2B lead extraction dork designed to target {kw0} leads in {location} via high-intent filters."
        if "facebook.com" in d:
            reason = f"Extracts direct B2B contacts, phone numbers, and page info for {kw0} in {location} via Facebook."
        elif "linkedin.com" in d:
            reason = f"Targets LinkedIn companies or founders/owners of {kw0} in {location}."
        elif "Shopify" in d or "Powered by Shopify" in d:
            reason = f"Finds Shopify-based ecommerce stores matching {kw0} in {location}."
        elif "@gmail.com" in d:
            reason = f"Directly extracts private and business emails (@gmail) for {kw0} leads in {location}."
        elif "info@" in d:
            reason = f"Finds generic business contact addresses (info@) for {kw0} in {location}."
        elif "contact" in d.lower() or "inurl:contact" in d:
            reason = f"Targets direct contact pages of {kw0} websites in {location} to extract forms/details."
        elif "WhatsApp" in d:
            reason = f"Finds direct WhatsApp contact numbers of {kw0} businesses in {location}."
        why_this_dork.append({"dork": d, "reason": reason})

    return why_this_dork


def generate_target_urls(keywords: list[str], country: str, region: str | None = None) -> list[str]:
    """Generate target URLs (directories, listing sites) for a given industry + country."""
    country_meta = resolve_country_metadata(country, region or "")
    location = region if region else country
    domains = country_meta.get("domains", ["site:.com"])

    urls = []
    kw = keywords[0] if keywords else "business"

    url_templates = [
        f"https://www.google.com/search?q={kw}+{location}+contact",
        f"https://www.linkedin.com/search/results/companies/?keywords={kw}+{location}",
        f"https://www.facebook.com/search/pages/?q={kw}+{location}",
        f"https://www.yelp.com/search?find_desc={kw}&find_loc={location}",
        f"https://www.yellowpages.com/search?search_terms={kw}&geo_location_terms={location}",
    ]

    urls.extend(url_templates)
    return urls[:10]
