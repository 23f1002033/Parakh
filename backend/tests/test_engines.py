import json
from datetime import date

from app.serp import engines
from app.serp.client import cache_key


def put_fixture(settings, engine, params, data):
    path = settings.fixture_path / f"{cache_key(engine, params)}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data))


async def test_engines_tolerate_missing_fields(make_client, make_settings):
    s = make_settings(serpapi_mode="replay")
    client = make_client(serpapi_mode="replay")
    put_fixture(s, "instagram_profile", {"profile_id": "x.store"}, {})
    put_fixture(s, "google_lens", {"type": "all", "url": "https://i/x.jpg", "country": "in", "hl": "en"},
                {"visual_matches": [{}, {"price": "bad"}, None]})
    put_fixture(s, "google_maps", {"q": "x", "type": "search"}, {"local_results": [{"title": "Shop"}]})

    p = await engines.instagram_profile(client, "x.store")
    assert p.posts == [] and p.followers is None and p.is_private is False
    lens = await engines.lens_all(client, url="https://i/x.jpg")
    assert len(lens.matches) == 3 and all(m.price_inr is None for m in lens.matches)
    maps = await engines.google_maps(client, "x")
    assert maps.places[0].title == "Shop" and maps.places[0].rating is None


async def test_engines_parse_fields(make_client, make_settings):
    s = make_settings(serpapi_mode="replay")
    client = make_client(serpapi_mode="replay")
    put_fixture(s, "instagram_profile", {"profile_id": "x.store"}, {"profile_results": {
        "followers": 12000, "following": 10, "is_private": False, "is_verified": True,
        "is_professional_account": True, "external_url": "https://x.in",
        "bio_links": [{"url": "https://x.in/a"}],
        "posts": [{"shortcode": "AB", "accessibility_caption": "Photo by x on August 1, 2026."}],
    }})
    put_fixture(s, "google_lens", {"type": "all", "url": "https://i/x.jpg", "country": "in", "hl": "en"},
                {"visual_matches": [{"title": "Red Shirt", "link": "https://m.in/1", "source": "M",
                                     "price": {"value": "\u20b9499", "extracted_value": 499, "currency": "\u20b9"},
                                     "exact_matches": True}]})

    p = await engines.instagram_profile(client, "x.store")
    assert p.is_verified and p.followers == 12000 and p.bio_links == ["https://x.in/a"]
    assert p.posts[0].posted_on == date(2026, 8, 1) and p.posts[0].url == "https://www.instagram.com/p/AB/"
    lens = await engines.lens_all(client, url="https://i/x.jpg")
    assert lens.matches[0].price_inr == 499 and lens.matches[0].exact_match


async def test_google_shopping_parses_inr(make_client, make_settings):
    s = make_settings(serpapi_mode="replay")
    put_fixture(s, "google_shopping", {"q": "boAt Rockerz 110", "gl": "in", "hl": "en"}, {"shopping_results": [
        {"title": "boAt Rockerz 110", "price": "\u20b9699.00", "extracted_price": 699, "source": "Flipkart",
         "product_link": "https://www.google.com/shopping/product/1"},
        {"title": "No price"},
    ]})
    res = await engines.google_shopping(make_client(serpapi_mode="replay"), "boAt Rockerz 110")
    assert res.items[0].price_inr == 699 and res.items[0].link.endswith("/product/1")
    assert res.items[1].price_inr is None


async def test_forums_retries_once_on_timeout():
    import pytest

    from app.serp.client import EngineTimeout

    class Flaky:
        calls = 0

        async def search(self, engine, params, check_id=None, image=None, timeout=None):
            Flaky.calls += 1
            assert timeout == engines.FORUMS_TIMEOUT
            if Flaky.calls == 1:
                raise EngineTimeout("t")
            return {"organic_results": [{"title": "x", "link": "https://f.in/1"}]}

    assert len((await engines.google_forums(Flaky(), "q")).results) == 1
    assert Flaky.calls == 2

    class Dead(Flaky):
        async def search(self, *a, **k):
            raise EngineTimeout("t")

    with pytest.raises(EngineTimeout):
        await engines.google_forums(Dead(), "q")


def test_complaint_queries_keep_plain_form_for_short_handles():
    # Complaint terms are grouped: ungrouped, Google read "<name> OR scam OR ..." and ignored the name.
    assert engines.complaints_query("boat.nirvana", None) == (
        '"boat.nirvana" (scam OR fraud OR fake OR "not delivered" OR refund OR complaint)')
    assert engines.forums_query("boat.nirvana", None) == '"boat.nirvana"'
    assert engines.forums_query("redstore", "red.co.in") == '"redstore"'
    # Domains are never split, even with 3+ dot-separated parts.
    assert engines.forums_query(None, "my.shop.co.in") == '"my.shop.co.in"'


def test_complaint_queries_add_spaced_handle_for_three_words():
    assert engines.complaints_query("the_red.store", None) == (
        '("the_red.store" OR "the red store") (scam OR fraud OR fake OR "not delivered" OR refund OR complaint)')
    assert engines.forums_query("shop.with.priya_", "x.in") == '("shop.with.priya_" OR "shop with priya")'
