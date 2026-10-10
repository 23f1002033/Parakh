import io

import httpx
import respx
from PIL import Image

from app.serp.client import SEARCH_URL
from app.serp.images import UPLOAD_URL
from app.tools.record import parse_args, run
from tests.conftest import FAKE_KEY


def fake_serp(request):
    engine = request.url.params["engine"]
    body = {"search_metadata": {"json_endpoint": f"https://serpapi.com/x.json?api_key={FAKE_KEY}"}}
    if engine == "google_lens" and request.url.params["type"] == "all":
        body["visual_matches"] = [{"title": "Red shirt", "link": "https://m.in/1", "source": "M",
                                   "price": {"value": "Rs 499", "extracted_value": 499, "currency": "Rs"}}]
    elif engine == "google_lens":
        body["exact_matches"] = [{"title": "Red shirt", "link": "https://aliexpress.com/1", "source": "AE"}]
    elif engine == "instagram_profile":
        body["profile_results"] = {"followers": 50, "posts": [{"shortcode": "A", "accessibility_caption": "on May 2, 2026"}]}
    elif engine == "google_shopping":
        body["shopping_results"] = [{"title": "boAt Rockerz 110", "price": "Rs 799", "extracted_price": 799,
                                     "source": "Flipkart", "product_link": "https://g.co/p/1"}]
    elif engine == "google_maps":
        body["local_results"] = [{"title": "Shop", "rating": 4.1, "reviews": 20, "place_id": "p1"}]
    else:
        body["organic_results"] = [{"title": "t", "link": "https://r.in/1"}]
    return httpx.Response(200, json=body)


async def test_record_then_replay_prints_same_summary(make_settings, tmp_path):
    img = tmp_path / "p.png"
    Image.new("RGB", (40, 40), (1, 2, 3)).save(img)
    argv = ["--instagram", "@Red.Store", "--website", "https://www.red.in/x", "--image", str(img),
            "--product", "red shirt", "--maps", "Red Store Jaipur"]

    with respx.mock:
        respx.post(UPLOAD_URL).mock(return_value=httpx.Response(200, json={"image_id": "i1"}))
        search = respx.get(SEARCH_URL).mock(side_effect=fake_serp)
        recorded = await run(parse_args(argv), make_settings())
    assert search.call_count == 8

    files = list(make_settings().fixture_path.glob("*.json"))
    assert len(files) == 8
    assert not any("api_key" in f.read_text() or FAKE_KEY in f.read_text() for f in files)

    with respx.mock:
        replayed = await run(parse_args(argv + ["--mode", "replay"]), make_settings(serpapi_key=None, database_url=f"sqlite:///{tmp_path / 'r.db'}"))
    summary = lambda out: out.split("\n--\n")[0]
    assert "unavailable" not in recorded
    assert summary(recorded) == summary(replayed)
    assert "1 priced in INR" in recorded and "posts visible=1" in recorded
    assert "google_shopping: 1 results, 1 priced in INR" in recorded


async def test_only_limits_the_calls(make_settings):
    argv = ["--instagram", "@red.store", "--product", "red shirt", "--only", "google_complaints,instagram_profile"]
    with respx.mock:
        search = respx.get(SEARCH_URL).mock(side_effect=fake_serp)
        out = await run(parse_args(argv), make_settings())
    assert sorted(c.request.url.params["engine"] for c in search.calls) == ["google", "instagram_profile"]
    google = next(c.request.url.params for c in search.calls if c.request.url.params["engine"] == "google")
    assert google["q"] == '"red.store" (scam OR fraud OR fake OR "not delivered" OR refund OR complaint)'
    assert "google_shopping" not in out and "google_forums" not in out


def test_only_rejects_unknown_names():
    import pytest
    with pytest.raises(SystemExit):
        parse_args(["--instagram", "x", "--only", "google_typo"])
