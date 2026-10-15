
import os, requests

FRED_API_KEY = os.getenv("FRED_API_KEY")

def fetch_fred(series_id="DTWEXBGS"):
    """DXY 대용: DTWEXBGS (Broad Dollar Index) / DGS10 (10Y) / VIXCLS (VIX)"""
    if not FRED_API_KEY:
        return {"error": "NO_KEY", "value": None}
    url = f"https://api.stlouisfed.org/fred/series/observations?series_id={series_id}&api_key={FRED_API_KEY}&file_type=json&sort_order=desc&limit=5"
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        data = r.json().get("observations", [])
        return {"series": series_id, "latest": data[0] if data else None}
    except Exception as e:
        return {"error": str(e), "series": series_id}

def fetch_all():
    return {
        "DXY_proxy": fetch_fred("DTWEXBGS"),
        "US10Y": fetch_fred("DGS10"),
        "VIX": fetch_fred("VIXCLS")
    }

if __name__ == "__main__":
    print(fetch_all())
