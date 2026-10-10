import asyncio

import pytest

from app.limits import RateLimiter
from app.schemas import ApiError
from app.signals.account import indian_number


def test_window_slides():
    now = [0.0]
    lim = RateLimiter(2, "checks", clock=lambda: now[0])
    lim.hit("a")
    now[0] = 100
    lim.hit("a")
    with pytest.raises(ApiError) as e:
        lim.check("a")
    assert e.value.status == 429 and e.value.headers["Retry-After"] == "3500"
    lim.check("b")
    now[0] = 3600
    lim.check("a")


def test_indian_number():
    assert [indian_number(n) for n in (0, 999, 1000, 99999, 100000, 1036292, 123456789)] == [
        "0", "999", "1,000", "99,999", "1,00,000", "10,36,292", "12,34,56,789"]


async def test_replay_delay_waits_in_replay_only(make_client, monkeypatch):
    waits = []

    async def fake_sleep(s):
        waits.append(s)

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)
    client = make_client(serpapi_mode="replay", replay_delay_ms=1000)
    with pytest.raises(Exception):
        await client.search("google", {"q": "none"})
    assert len(waits) == 1 and 0.5 <= waits[0] <= 1.5

    waits.clear()
    with pytest.raises(Exception):
        await make_client(serpapi_mode="replay").search("google", {"q": "none"})
    assert waits == []


def test_init_db_adds_claimed_mrp_to_an_old_checks_table(tmp_path):
    from sqlalchemy import inspect, text

    from app.db import init_db, make_engine
    engine = make_engine(f"sqlite:///{tmp_path / 'old.db'}")
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE checks (id VARCHAR(32) PRIMARY KEY, quoted_price INTEGER)"))
        conn.execute(text("INSERT INTO checks (id, quoted_price) VALUES ('a', 699)"))
    init_db(engine)
    init_db(engine)
    assert "claimed_mrp" in {c["name"] for c in inspect(engine).get_columns("checks")}
    with engine.connect() as conn:
        assert conn.execute(text("SELECT quoted_price, claimed_mrp FROM checks")).one() == (699, None)
