"""
Lead Intelligence API — Comprehensive Test Suite.

Tests all endpoints for both existing and new functionality.
Run with: python test_api.py
"""

import urllib.request
import json
import time

BASE = "http://127.0.0.1:8000"
API_KEY = "lpk_4519f3220b1c30b688d861ce651c6b24b9dd079c34d3e385"

results = {"pass": 0, "fail": 0}


def test(name, fn):
    """Run a test and print result."""
    try:
        fn()
        results["pass"] += 1
        print(f"  ✅ {name}")
    except Exception as e:
        results["fail"] += 1
        print(f"  ❌ {name}: {e}")


def get(path):
    """GET request helper."""
    req = urllib.request.urlopen(f"{BASE}{path}")
    return json.loads(req.read().decode()), req.status


def get_with_key(path):
    """GET with API key."""
    req = urllib.request.Request(f"{BASE}{path}", headers={"X-API-KEY": API_KEY})
    resp = urllib.request.urlopen(req)
    return json.loads(resp.read().decode()), resp.status


def post_with_key(path, body):
    """POST with API key."""
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        f"{BASE}{path}",
        data=data,
        headers={"X-API-KEY": API_KEY, "Content-Type": "application/json"},
        method="POST",
    )
    resp = urllib.request.urlopen(req)
    return json.loads(resp.read().decode()), resp.status


def post_no_key(path, body):
    """POST without API key — expects 401/422."""
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        f"{BASE}{path}",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        resp = urllib.request.urlopen(req)
        return json.loads(resp.read().decode()), resp.status
    except urllib.error.HTTPError as e:
        return json.loads(e.read().decode()), e.code


# ═══════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("PHASE 1: EXISTING ENDPOINTS (Backward Compatibility)")
print("=" * 60)

def test_swagger():
    req = urllib.request.urlopen(f"{BASE}/docs")
    assert req.status == 200

def test_dashboard():
    req = urllib.request.urlopen(f"{BASE}/")
    assert req.status == 200

def test_today_recs():
    d, s = get("/today-recommendations")
    assert s == 200
    assert "count" in d
    assert "recommendations" in d

def test_debug_config():
    d, s = get("/debug-llm-config")
    assert s == 200
    assert "provider" in d
    assert d["api_key_present"] is True

test("Swagger UI (/docs)", test_swagger)
test("Dashboard (/)", test_dashboard)
test("Today Recommendations", test_today_recs)
test("Debug LLM Config", test_debug_config)


# ═══════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("PHASE 2: AUTHENTICATION")
print("=" * 60)

def test_no_key():
    d, s = post_no_key("/api/v1/generate", {"industry": "Healthcare", "country": "UAE"})
    assert s in (401, 422), f"Expected 401/422, got {s}"

def test_bad_key():
    data = json.dumps({"industry": "Healthcare", "country": "UAE"}).encode()
    req = urllib.request.Request(
        f"{BASE}/api/v1/generate", data=data,
        headers={"X-API-KEY": "bad_key_123", "Content-Type": "application/json"}, method="POST"
    )
    try:
        urllib.request.urlopen(req)
        assert False, "Should have failed"
    except urllib.error.HTTPError as e:
        assert e.code == 403

def test_good_key():
    # Health doesn't need auth, but metadata endpoints do
    d, s = get_with_key("/api/v1/countries")
    assert s == 200
    assert d["success"] is True

test("No API Key → 401/422", test_no_key)
test("Bad API Key → 403", test_bad_key)
test("Valid API Key → 200", test_good_key)


# ═══════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("PHASE 3: HEALTH & METADATA")
print("=" * 60)

def test_health():
    d, s = get("/api/v1/health")
    assert s == 200
    assert d["success"] is True
    assert d["status"] == "healthy"

def test_countries():
    d, s = get_with_key("/api/v1/countries")
    assert s == 200
    assert d["count"] > 0
    assert "UAE" in d["data"]

def test_sectors():
    d, s = get_with_key("/api/v1/sectors")
    assert s == 200
    assert d["count"] > 0
    assert "healthcare" in d["data"]

def test_platforms():
    d, s = get_with_key("/api/v1/platforms")
    assert s == 200
    assert d["count"] > 0
    assert "LinkedIn" in d["data"]

test("Health Check", test_health)
test("Countries List", test_countries)
test("Sectors List", test_sectors)
test("Platforms List", test_platforms)


# ═══════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("PHASE 4: GENERATE ENDPOINT")
print("=" * 60)

def test_generate():
    d, s = post_with_key("/api/v1/generate", {
        "industry": "Healthcare",
        "country": "UAE",
        "target_role": "CEO",
        "business_type": "Hospital",
        "platform": "LinkedIn",
    })
    assert s == 200, f"HTTP {s}: {d}"
    assert d["success"] is True
    assert d["industry"] == "Healthcare"
    assert d["country"] == "UAE"
    assert len(d["dorks"]) > 0, "Expected dorks"
    assert len(d["keywords"]) > 0, "Expected keywords"
    assert d["opportunity_score"] > 0
    assert d["generated_count"] == len(d["dorks"])
    assert "metadata" in d
    assert d["metadata"]["processing_time"] > 0
    print(f"    → {d['generated_count']} dorks, score={d['opportunity_score']}, time={d['metadata']['processing_time']}s")

def test_generate_minimal():
    d, s = post_with_key("/api/v1/generate", {
        "industry": "Tourism",
        "country": "UK",
    })
    assert s == 200
    assert d["success"] is True
    assert len(d["dorks"]) > 0
    print(f"    → {d['generated_count']} dorks (minimal request)")

test("Generate (full params)", test_generate)
test("Generate (minimal params)", test_generate_minimal)


# ═══════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("PHASE 5: CACHE")
print("=" * 60)

def test_cache():
    # Call same request again — should hit cache
    d, s = post_with_key("/api/v1/generate", {
        "industry": "Healthcare",
        "country": "UAE",
        "target_role": "CEO",
        "business_type": "Hospital",
        "platform": "LinkedIn",
    })
    assert s == 200
    assert d["success"] is True
    assert d["metadata"]["cached"] is True
    print(f"    → Cache HIT confirmed, time={d['metadata']['processing_time']}s")

test("Cache Hit (repeated request)", test_cache)


# ═══════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("PHASE 6: BULK GENERATE")
print("=" * 60)

def test_bulk():
    d, s = post_with_key("/api/v1/bulk-generate", {
        "requests": [
            {"industry": "Healthcare", "country": "UAE"},
            {"industry": "Legal", "country": "UK"},
            {"industry": "Tourism", "country": "Australia"},
        ]
    })
    assert s == 200
    assert d["success"] is True
    assert d["total_requested"] == 3
    assert len(d["results"]) == 3
    assert d["total_generated"] > 0
    for r in d["results"]:
        assert r["success"] is True
        assert len(r["dorks"]) > 0
    print(f"    → {d['total_generated']} total dorks across {d['total_requested']} requests")

test("Bulk Generate (3 requests)", test_bulk)


# ═══════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("PHASE 7: TRENDING OPPORTUNITIES")
print("=" * 60)

def test_trending():
    d, s = get_with_key("/api/v1/trending-opportunities")
    assert s == 200
    assert d["success"] is True
    assert "count" in d
    assert "opportunities" in d
    print(f"    → {d['count']} trending opportunities")

test("Trending Opportunities", test_trending)


# ═══════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("PHASE 8: LEADPILOT INTEGRATION SIMULATION")
print("=" * 60)

def test_leadpilot_integration():
    """Simulate exactly what LeadPilot would do."""
    import urllib.request
    API_URL = f"{BASE}/api/v1/generate"

    payload = {
        "industry": "Real Estate",
        "country": "Saudi Arabia",
        "target_role": "Founder",
        "business_type": "Property Developer",
        "platform": "Google",
    }

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        API_URL, data=data,
        headers={"X-API-KEY": API_KEY, "Content-Type": "application/json"},
        method="POST"
    )
    resp = urllib.request.urlopen(req)
    response = json.loads(resp.read().decode())

    # LeadPilot direct field access:
    assert response["success"] is True
    keywords = response["keywords"]
    dorks = response["dorks"]
    score = response["opportunity_score"]
    urls = response["target_urls"]

    assert isinstance(keywords, list)
    assert isinstance(dorks, list)
    assert isinstance(score, int)
    assert isinstance(urls, list)
    assert len(dorks) > 0
    print(f"    → LeadPilot can directly use: {len(keywords)} keywords, {len(dorks)} dorks, score={score}")

test("LeadPilot Integration Simulation", test_leadpilot_integration)


# ═══════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print(f"RESULTS: {results['pass']} passed, {results['fail']} failed")
print("=" * 60)

if results["fail"] == 0:
    print("\n🎉 ALL TESTS PASSED!")
else:
    print(f"\n⚠️  {results['fail']} test(s) failed")
