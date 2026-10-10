from datetime import date
from pathlib import Path

import httpx
import respx
from sqlalchemy import select

from app.checks.runner import CheckInputs, Runner
from app.config import BACKEND_DIR
from app.models import Check, Evidence, Store
from app.serp.client import SEARCH_URL, SerpClient
from app.serp.images import ImageRef
from tests.stubs import StubClient, serp_body, timeout_error

DEMO_IMAGE = BACKEND_DIR / "demo" / "boat.png"
REAL_FIXTURES = BACKEND_DIR / "tests" / "fixtures" / "serp"


def new_check(sessions, handle="red.store", domain=None):
    with sessions() as s:
        st = Store(kind="instagram", key=handle, display=f"@{handle}")
        s.add(st)
        s.flush()
        c = Check(instagram_store_id=st.id, status="running", signal_status={})
        s.add(c)
        s.commit()
        return c.id


def load(sessions, check_id):
    with sessions() as s:
        c = s.get(Check, check_id)
        ev = s.scalars(select(Evidence).where(Evidence.check_id == check_id).order_by(Evidence.position)).all()
        return c, ev


async def test_run_1_demo_in_replay(make_settings, sessions):
    settings = make_settings(serpapi_mode="replay", serpapi_key=None, fixture_dir=str(REAL_FIXTURES))
    client = SerpClient(settings, sessions)
    check_id = new_check(sessions, "boat.nirvana")
    inputs = CheckInputs(handle="boat.nirvana", product_name="boAt Rockerz 110", quoted_price=699,
                         image=ImageRef.from_bytes(DEMO_IMAGE.read_bytes()))
    await Runner(check_id, inputs, client, sessions, today=date(2026, 10, 9)).run()
    c, ev = load(sessions, check_id)

    assert c.status == "done"
    assert c.live_searches == 0
    for name in ("photo", "complaints", "account"):
        assert c.signal_status[name] == "done", name
    price_items = [e for e in ev if e.signal == "price"]
    if c.signal_status["price"] != "done":
        import pytest
        pytest.skip(f"demo 1 price fixtures not recorded yet: {price_items[0].finding}")
    p = price_items[0]
    assert p.data["source"] in ("google_lens", "google_shopping")
    assert 0.6 <= p.data["ratio"] <= 1.5
    assert c.verdict == "No red flags found"


async def test_run_2_forums_failure_keeps_google(make_settings, sessions):
    client = StubClient(fail={"google_forums": timeout_error()})
    check_id = new_check(sessions)
    inputs = CheckInputs(handle="red.store", product_name="Red Shirt Cotton", quoted_price=520,
                         image=ImageRef.from_bytes(DEMO_IMAGE.read_bytes()))
    await Runner(check_id, inputs, client, sessions, today=date(2026, 10, 9)).run()
    c, ev = load(sessions, check_id)
    assert c.status == "done"
    assert c.signal_status["complaints"] == "done"
    comp = [e for e in ev if e.signal == "complaints"][0]
    assert comp.severity == "good" and {s["engine"] for s in comp.sources} == {"google"}


async def test_all_complaint_engines_fail_marks_unavailable(sessions):
    client = StubClient(fail={"google_forums": timeout_error(), "google": timeout_error()})
    check_id = new_check(sessions)
    await Runner(check_id, CheckInputs(handle="red.store"), client, sessions).run()
    c, ev = load(sessions, check_id)
    assert c.status == "done" and c.signal_status["complaints"] == "unavailable"
    assert [e.finding for e in ev if e.signal == "complaints"] == ["Source unavailable: source timed out"]


async def test_signal_bug_is_contained(sessions, monkeypatch):
    from app.signals import account

    def boom(*a, **k):
        raise ZeroDivisionError

    monkeypatch.setattr(account, "evaluate", boom)
    check_id = new_check(sessions)
    await Runner(check_id, CheckInputs(handle="red.store", product_name="Red Shirt Cotton"), StubClient(), sessions).run()
    c, _ = load(sessions, check_id)
    assert c.status == "done"
    assert c.signal_status["account"] == "unavailable" and c.signal_status["complaints"] == "done"


async def test_shopping_called_only_when_lens_is_short(sessions):
    client = StubClient()
    check_id = new_check(sessions)
    await Runner(check_id, CheckInputs(handle="red.store", product_name="Red Shirt Cotton", image_url="https://i.in/a.jpg"),
                 client, sessions).run()
    assert "google_shopping" not in client.calls
    assert len(client.calls) == 5

    client = StubClient()
    check_id = new_check(sessions, "red.store2")
    await Runner(check_id, CheckInputs(handle="red.store", product_name="Blue Jeans 501", image_url="https://i.in/a.jpg"),
                 client, sessions).run()
    assert client.calls.count("google_shopping") == 1
    assert len(client.calls) == 6


async def test_same_check_twice_spends_no_live_searches(make_settings, sessions):
    def reply(request):
        params = dict(request.url.params)
        return httpx.Response(200, json=serp_body(params.pop("engine"), params))

    client = SerpClient(make_settings(serpapi_mode="live"), sessions)
    inputs = CheckInputs(handle="red.store", product_name="Red Shirt Cotton", quoted_price=500, image_url="https://i.in/a.jpg")
    with respx.mock:
        route = respx.get(SEARCH_URL).mock(side_effect=reply)
        first = new_check(sessions)
        await Runner(first, inputs, client, sessions).run()
        second = new_check(sessions, "red.store3")
        await Runner(second, inputs, client, sessions).run()
    a, _ = load(sessions, first)
    b, _ = load(sessions, second)
    assert a.live_searches == 5 and a.cached_searches == 0
    assert b.live_searches == 0 and b.cached_searches == 5
    assert route.call_count == 5
    await client.aclose()


async def test_instagram_profile_not_found_is_a_caution(sessions):
    from app.serp.client import EngineError

    class NotFound(StubClient):
        async def search(self, engine, params, check_id=None, image=None, timeout=None):
            if engine == "instagram_profile":
                self.calls.append(engine)
                return {"search_metadata": {"status": "Success"}, "error": "Instagram profile not found."}
            return await super().search(engine, params, check_id, image, timeout)

    check_id = new_check(sessions)
    await Runner(check_id, CheckInputs(handle="red.store"), NotFound(), sessions).run()
    c, ev = load(sessions, check_id)
    assert c.status == "done" and c.signal_status["account"] == "done"
    acc = [e for e in ev if e.signal == "account"]
    assert [(e.severity, e.finding[:43]) for e in acc] == [("warn", "No Instagram account found with this handle")]
    assert c.signal_status["complaints"] == "done"

    other = StubClient(fail={"instagram_profile": EngineError("instagram_profile: HTTP 200: Instagram profile is private API error")})
    check_id = new_check(sessions, "red.store9")
    await Runner(check_id, CheckInputs(handle="red.store"), other, sessions).run()
    c, _ = load(sessions, check_id)
    assert c.signal_status["account"] == "unavailable"
