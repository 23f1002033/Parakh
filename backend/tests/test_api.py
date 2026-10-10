import io

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.main import create_app
from app.signals.rules import SIGNALS
from tests.stubs import StubClient


@pytest.fixture
def api(make_settings):
    with TestClient(create_app(make_settings(serpapi_mode="replay", ip_salt="s"), serp=StubClient())) as c:
        yield c


def png(size=(32, 32)):
    buf = io.BytesIO()
    Image.new("RGB", size, (9, 9, 9)).save(buf, "PNG")
    return buf.getvalue()


def post_check(api, files=None, **fields):
    data = {"instagram": "@Red.Store", "product_name": "Red Shirt Cotton", "quoted_price": "520", **fields}
    return api.post("/api/checks", data={k: v for k, v in data.items() if v is not None}, files=files)


def test_api_1_needs_handle_or_website(api):
    r = post_check(api, instagram=None)
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "invalid_input"


def test_api_2_image_too_large(api):
    r = post_check(api, files={"image": ("big.jpg", b"0" * (6 * 1024 * 1024), "image/jpeg")})
    assert r.status_code == 413 and r.json()["error"]["code"] == "image_too_large"


def test_api_3_not_an_image(api):
    r = post_check(api, files={"image": ("x.png", b"hello, not an image", "image/png")})
    assert r.status_code == 422


def test_api_4_post_then_get_done(api):
    r = post_check(api, files={"image": ("p.png", png(), "image/png")})
    assert r.status_code == 202
    body = api.get(f"/api/checks/{r.json()['id']}").json()
    assert body["status"] == "done"
    assert list(body["evidence"]) == list(SIGNALS)
    assert all(body["signal_status"][s] in ("done", "skipped", "unavailable") for s in SIGNALS)
    assert body["evidence"]["price"][0]["severity"] == "good"
    assert body["stores"][0]["path"] == "/s/instagram/red.store"
    assert body["verdict"] and body["has_image"] is True


def test_api_5_report_then_store_page(api):
    post_check(api)
    r = api.post("/api/stores/instagram/red.store/reports", json={"outcome": "not_delivered", "note": "<b>No</b> parcel"})
    assert r.status_code == 201 and r.json()["note"] == "No parcel"
    page = api.get("/api/stores/instagram/@Red.Store").json()
    assert page["report_counts"]["not_delivered"] == 1
    assert page["reports"][0]["outcome"] == "not_delivered" and "ip_hash" not in page["reports"][0]
    assert len(page["checks"]) == 1

    second = api.get(f"/api/checks/{post_check(api).json()['id']}").json()
    assert second["signal_status"]["community"] == "done"
    assert second["evidence"]["community"][0]["data"]["negative"] == 1


def test_api_6_long_note(api):
    post_check(api)
    r = api.post("/api/stores/instagram/red.store/reports", json={"outcome": "other", "note": "x" * 300})
    assert r.status_code == 422 and "error" in r.json()


def test_api_7_unknown_store(api):
    r = api.get("/api/stores/instagram/nobody.here")
    assert r.status_code == 404 and r.json()["error"]["code"] == "not_found"
    assert api.get("/api/stores/tiktok/x").status_code == 404


def test_bad_inputs(api):
    assert post_check(api, quoted_price="0").status_code == 422
    assert post_check(api, product_name="x" * 121).status_code == 422
    assert post_check(api, image_url="ftp://x.in/a.jpg").status_code == 422
    assert post_check(api, instagram=None, website="not a domain").status_code == 422
    assert api.get("/api/checks/nope").status_code == 404


def test_demos_and_rules(api):
    demos = api.get("/api/demos").json()
    assert [d["name"] for d in demos] == ["boat", "shopyvision", "shanaya"]
    assert demos[1]["claimed_mrp"] == 1999 and demos[2]["image_path"] is None
    assert demos[0]["quoted_price"] == 699 and demos[0]["product_name"] == "boAt Rockerz 110"
    img = api.get(demos[0]["image_path"])
    assert img.status_code == 200 and img.headers["content-type"] == "image/png"
    assert api.get("/api/demos/demo2/image").status_code == 404
    rules = api.get("/api/meta/rules").json()
    assert rules["price"]["bad_ratio"] == 3.0 and rules["verdict"]["reports"]["cap"] == 6


def test_api_8_check_rate_limit(make_settings):
    with TestClient(create_app(make_settings(serpapi_mode="replay"), serp=StubClient())) as c:
        for _ in range(10):
            assert post_check(c).status_code == 202
        r = post_check(c)
    assert r.status_code == 429
    assert r.json()["error"]["code"] == "rate_limited" and "10 checks per hour" in r.json()["error"]["message"]
    assert 3500 <= int(r.headers["Retry-After"]) <= 3600


def test_rejected_input_does_not_use_the_check_limit(make_settings):
    with TestClient(create_app(make_settings(serpapi_mode="replay", checks_per_hour=1), serp=StubClient())) as c:
        assert post_check(c, instagram=None).status_code == 422
        assert post_check(c).status_code == 202
        assert post_check(c).status_code == 429


def test_report_rate_limit(make_settings):
    with TestClient(create_app(make_settings(serpapi_mode="replay", reports_per_hour=2), serp=StubClient())) as c:
        post_check(c)
        path = "/api/stores/instagram/red.store/reports"
        assert [c.post(path, json={"outcome": "other"}).status_code for _ in range(3)] == [201, 201, 429]
        assert "Retry-After" in c.post(path, json={"outcome": "other"}).headers


def test_claimed_mrp_is_stored_and_validated(api):
    assert post_check(api, claimed_mrp="0").status_code == 422
    r = post_check(api, claimed_mrp="1999", image_url="https://i.in/a.jpg")
    body = api.get(f"/api/checks/{r.json()['id']}").json()
    assert body["claimed_mrp"] == 1999
    mrp = [i for i in body["evidence"]["price"] if "original price" in i["finding"]]
    assert mrp and mrp[0]["severity"] == "warn"
