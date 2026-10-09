from fastapi.testclient import TestClient

from app.main import create_app
from tests.stubs import StubClient


def test_built_spa_is_served(make_settings, tmp_path):
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text("<!doctype html><div id=app></div>")
    (dist / "assets" / "app.js").write_text("console.log(1)")
    (dist / "favicon.svg").write_text("<svg/>")

    with TestClient(create_app(make_settings(serpapi_mode="replay"), serp=StubClient(), frontend_dist=dist)) as c:
        for path in ("/", "/c/abc123", "/s/instagram/red.store", "/about"):
            r = c.get(path)
            assert r.status_code == 200 and "id=app" in r.text, path
        assert c.get("/assets/app.js").text == "console.log(1)"
        assert c.get("/favicon.svg").text == "<svg/>"
        assert c.get("/api/health").json() == {"ok": True}
        missing = c.get("/api/nothing")
        assert missing.status_code == 404 and missing.json()["error"]["code"] == "not_found"
        assert c.get("/../../etc/passwd").status_code in (200, 404)
        assert "root:" not in c.get("/..%2F..%2Fetc%2Fpasswd").text


def test_no_dist_means_api_only(make_settings, tmp_path):
    with TestClient(create_app(make_settings(serpapi_mode="replay"), serp=StubClient(), frontend_dist=tmp_path / "none")) as c:
        assert c.get("/about").status_code == 404
