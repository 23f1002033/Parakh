from fastapi.testclient import TestClient

from app.main import create_app


def test_health_and_credits(make_settings):
    with TestClient(create_app(make_settings(serpapi_mode="replay"))) as c:
        assert c.get("/api/health").json() == {"ok": True}
        body = c.get("/api/meta/credits").json()
    assert body == {"live_searches_today": 0, "daily_cap": 40, "cache_hit_rate_today": None, "mode": "replay"}
