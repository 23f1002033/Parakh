import pytest

from app.config import Settings
from app.db import init_db, make_engine, make_session_factory
from app.serp.client import SerpClient

FAKE_KEY = "test-key-0123456789abcdef"


@pytest.fixture
def make_settings(tmp_path):
    def _make(**overrides):
        values = dict(
            _env_file=None,
            serpapi_key=FAKE_KEY,
            serpapi_mode="live",
            database_url=f"sqlite:///{tmp_path / 'test.db'}",
            fixture_dir=str(tmp_path / "fixtures"),
            daily_search_cap=40,
        )
        values.update(overrides)
        return Settings(**values)
    return _make


@pytest.fixture
def sessions(make_settings):
    engine = make_engine(make_settings().database_url)
    init_db(engine)
    yield make_session_factory(engine)
    engine.dispose()


@pytest.fixture
def make_client(make_settings, sessions):
    clients = []

    def _make(**overrides):
        c = SerpClient(make_settings(**overrides), sessions)
        clients.append(c)
        return c
    yield _make
