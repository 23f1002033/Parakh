from app.serp.client import EngineTimeout

PROFILE = {"profile_results": {
    "username": "red.store", "full_name": "Red Store", "followers": 1200, "following": 80,
    "is_private": False, "is_verified": False, "external_url": "https://red.in",
    "posts": [{"shortcode": f"P{i}", "accessibility_caption": f"Photo by Red Store on March {i + 1}, 2026."}
              for i in range(12)],
}}


def serp_body(engine: str, params: dict) -> dict:
    if engine == "google_lens" and params.get("type") == "all":
        return {"visual_matches": [
            {"title": f"Red Shirt Cotton {i}", "link": f"https://www.amazon.in/dp/{i}", "source": "Amazon.in",
             "price": {"value": f"Rs {p}", "extracted_value": p, "currency": "Rs"}}
            for i, p in enumerate([450, 500, 550])
        ]}
    if engine == "google_lens":
        return {"exact_matches": [{"title": "Red shirt", "link": "https://red.in/p/1", "source": "Red"}]}
    if engine == "instagram_profile":
        return PROFILE
    if engine == "google_shopping":
        return {"shopping_results": []}
    return {"organic_results": [
        {"title": "red.store review", "link": f"https://forum.in/{engine}/1", "snippet": "received my order, genuine"},
        {"title": "Red Store haul", "link": f"https://forum.in/{engine}/2", "snippet": "received, original"},
    ]}


class StubClient:
    """SerpClient stand-in: canned responses, optional failing engines."""

    def __init__(self, fail: dict | None = None):
        self.fail = fail or {}
        self.calls = []

    async def search(self, engine, params, check_id=None, image=None, timeout=None):
        self.calls.append(engine)
        if engine in self.fail:
            raise self.fail[engine]
        return serp_body(engine, params)

    async def aclose(self):
        pass


def timeout_error():
    return EngineTimeout("google_forums: ReadTimeout")
