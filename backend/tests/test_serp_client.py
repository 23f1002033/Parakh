import asyncio
import io

import httpx
import pytest
import respx
from PIL import Image
from sqlalchemy import select

from app.models import ApiCall
from app.serp import engines
from app.serp.client import SEARCH_URL, CapReached, EngineError, FixtureMissing, cache_key
from app.serp.images import MAX_BYTES, UPLOAD_URL, ImageRef, to_jpeg
from tests.conftest import FAKE_KEY


def serp_response(q="x", **extra):
    return {
        "search_metadata": {
            "id": "abc",
            "status": "Success",
            "json_endpoint": f"https://serpapi.com/searches/abc.json?api_key={FAKE_KEY}",
            "google_url": f"https://www.google.com/search?q={q}",
        },
        "search_parameters": {"engine": "google", "q": q, "api_key": FAKE_KEY},
        "organic_results": [{"title": "t", "link": "https://a.in/x"}],
        **extra,
    }


def png_bytes(size=(64, 64)):
    buf = io.BytesIO()
    Image.new("RGB", size, (200, 10, 10)).save(buf, "PNG")
    return buf.getvalue()


def ledger(sessions):
    with sessions() as s:
        return s.scalars(select(ApiCall).order_by(ApiCall.id)).all()


def test_serp_1_cache_key_ignores_api_key():
    base = {"q": "x", "gl": "in"}
    assert cache_key("google", base) == cache_key("google", {**base, "api_key": "k", "no_cache": "true", "output": "json"})
    assert cache_key("google", base) != cache_key("google_forums", base)


@respx.mock
async def test_serp_2_second_identical_call_is_cached(make_client, sessions):
    route = respx.get(SEARCH_URL).mock(return_value=httpx.Response(200, json=serp_response()))
    client = make_client()
    a = await client.search("google", {"q": "x", "gl": "in"}, "c1")
    b = await client.search("google", {"q": "x", "gl": "in"}, "c1")
    assert route.call_count == 1
    assert a == b
    rows = ledger(sessions)
    assert [r.cache_hit for r in rows] == [False, True]
    assert all(r.ok for r in rows)


async def test_serp_3_replay_missing_fixture(make_client, sessions):
    client = make_client(serpapi_mode="replay", serpapi_key=None)
    with respx.mock(assert_all_called=False) as router:
        route = router.route().mock(return_value=httpx.Response(500))
        with pytest.raises(FixtureMissing):
            await client.search("google", {"q": "nothing"})
    assert route.call_count == 0
    assert ledger(sessions)[0].ok is False


@respx.mock
async def test_serp_4_record_writes_scrubbed_fixture(make_client, make_settings):
    respx.get(SEARCH_URL).mock(return_value=httpx.Response(200, json=serp_response()))
    client = make_client(serpapi_mode="record")
    await client.search("google", {"q": "x"})
    files = list(make_settings().fixture_path.glob("*.json"))
    assert len(files) == 1
    text = files[0].read_text()
    assert "api_key" not in text
    assert FAKE_KEY not in text
    assert files[0].stem == cache_key("google", {"q": "x"})

    replay = make_client(serpapi_mode="replay", serpapi_key=None)
    data = await replay.search("google", {"q": "x"})
    assert data["organic_results"][0]["link"] == "https://a.in/x"


@respx.mock
async def test_serp_5_cap_reached_but_cache_still_works(make_client, sessions):
    route = respx.get(SEARCH_URL).mock(return_value=httpx.Response(200, json=serp_response()))
    client = make_client(daily_search_cap=1)
    await client.search("google", {"q": "first"})
    with pytest.raises(CapReached):
        await client.search("google", {"q": "second"})
    assert (await client.search("google", {"q": "first"}))["organic_results"]
    assert route.call_count == 1


@respx.mock
async def test_serp_6_lens_cache_keyed_by_image_sha(make_client, sessions):
    upload = respx.post(UPLOAD_URL).mock(return_value=httpx.Response(200, json={"image_id": "img-1"}))
    search = respx.get(SEARCH_URL).mock(return_value=httpx.Response(200, json={"visual_matches": []}))
    client = make_client()
    data = png_bytes()

    await engines.lens_all(client, image=ImageRef.from_bytes(data))
    # Second check: new upload object for the same photo; image_id would differ, sha does not.
    await engines.lens_all(client, image=ImageRef.from_bytes(data))

    assert upload.call_count == 1
    assert search.call_count == 1
    assert search.calls[0].request.url.params["image_id"] == "img-1"
    assert "q" not in search.calls[0].request.url.params
    assert [r.engine for r in ledger(sessions)] == ["image_upload", "google_lens", "google_lens"]


@respx.mock
async def test_one_upload_shared_by_concurrent_lens_calls(make_client):
    upload = respx.post(UPLOAD_URL).mock(return_value=httpx.Response(200, json={"image_id": "img-1"}))
    respx.get(SEARCH_URL).mock(return_value=httpx.Response(200, json={"exact_matches": []}))
    client = make_client()
    image = ImageRef.from_bytes(png_bytes())
    await asyncio.gather(engines.lens_all(client, image=image), engines.lens_exact(client, image=image))
    assert upload.call_count == 1


@respx.mock
async def test_serpapi_error_field_raises_engine_error(make_client, sessions):
    respx.get(SEARCH_URL).mock(return_value=httpx.Response(401, json={"error": "Invalid API key."}))
    client = make_client()
    with pytest.raises(EngineError) as e:
        await client.search("google", {"q": "x"})
    assert FAKE_KEY not in str(e.value)
    assert ledger(sessions)[0].ok is False


@respx.mock
async def test_http_error_raises_engine_error(make_client):
    respx.get(SEARCH_URL).mock(side_effect=httpx.ConnectTimeout("boom"))
    with pytest.raises(EngineError):
        await make_client().search("google", {"q": "x"})


@respx.mock
async def test_no_results_is_empty_not_error(make_client):
    body = {"search_metadata": {"status": "Success"}, "error": "Google hasn't returned any results for this query."}
    respx.get(SEARCH_URL).mock(return_value=httpx.Response(200, json=body))
    res = await engines.google_forums(make_client(), '"nobody.store"')
    assert res.results == []


def test_to_jpeg_downscales_large_images():
    big = Image.effect_noise((3000, 3000), 100).convert("RGB")
    buf = io.BytesIO()
    big.save(buf, "PNG")
    jpeg, sha = to_jpeg(buf.getvalue())
    assert len(jpeg) <= MAX_BYTES
    assert Image.open(io.BytesIO(jpeg)).format == "JPEG"
    assert len(sha) == 64


def test_day_start_is_ist_midnight():
    from datetime import datetime, timezone

    from app.serp.client import day_start
    # 20:00 UTC on 9 Oct is 01:30 IST on 10 Oct; that IST day began at 18:30 UTC on 9 Oct.
    assert day_start(datetime(2026, 10, 9, 20, 0, tzinfo=timezone.utc)) == datetime(2026, 10, 9, 18, 30)
    # 10:00 UTC is 15:30 IST the same day.
    assert day_start(datetime(2026, 10, 9, 10, 0, tzinfo=timezone.utc)) == datetime(2026, 10, 8, 18, 30)


@respx.mock
async def test_timeout_raises_engine_timeout(make_client):
    from app.serp.client import EngineTimeout
    respx.get(SEARCH_URL).mock(side_effect=httpx.ReadTimeout("slow"))
    with pytest.raises(EngineTimeout):
        await make_client().search("google_forums", {"q": "x"}, timeout=30)
