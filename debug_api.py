"""Test the LIVE API endpoint after fix."""
import urllib.request
import json

url = "http://127.0.0.1:8000/today-recommendations"
try:
    req = urllib.request.urlopen(url)
    data = json.loads(req.read().decode())
    print(f"HTTP Status: {req.status}")
    print(f"count: {data.get('count', '?')}")
    print(f"recommendations: {len(data.get('recommendations', []))}")
    
    recs = data.get("recommendations", [])
    if recs:
        for i, r in enumerate(recs[:5]):
            print(f"\n  Rec #{i+1}: {r.get('trend_name','?')}")
            print(f"    country: {r.get('country','?')}")
            print(f"    dorks: {len(r.get('dorks',[]))}")
        print(f"\n[OK] Dashboard should show {len(recs)} recommendations!")
    else:
        print("\n[STILL BROKEN] API returns 0 recommendations")
        print("The server may be running old code. Try restarting: python app.py")
except Exception as e:
    print(f"Error connecting: {e}")
    print("Is the server running? Start with: python app.py")
