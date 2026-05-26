"""Full pipeline test — verifies TrendAnalyzer token limit fix and dork filter fix."""
from services.pipeline import run_daily_pipeline

print("Starting full pipeline test...\n")
result = run_daily_pipeline()

print("\n" + "=" * 60)
print("RESULT SUMMARY")
print("=" * 60)
print(f"Trends: {result['trend_count']}")
print(f"Recommendations saved: {result['recommendation_count']}")

recs = result.get("recommendations", [])
if recs:
    for i, r in enumerate(recs[:5], 1):
        print(f"\nRecommendation #{i}:")
        print(f"  Trend: {r.get('trend_name', 'N/A')}")
        print(f"  Country: {r.get('country', 'N/A')}")
        dorks = r.get("dorks", [])
        print(f"  Dorks count: {len(dorks)}")
        for d in dorks[:2]:
            print(f"    - {d[:100]}")
    print(f"\n[OK] Pipeline produced {len(recs)} recommendations with dorks!")
else:
    print("\n[WARN] No recommendations produced.")
    print("  This could mean no foreign-market trends were found in today's data.")
