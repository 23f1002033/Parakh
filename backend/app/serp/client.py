import hashlib
import json
import re
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import httpx
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, sessionmaker

from app.config import Settings
from app.models import ApiCall, SerpCache, utcnow
from app.serp import images
from app.serp.images import ImageRef

SEARCH_URL = "https://serpapi.com/search.json"
KEY_EXCLUDED = {"api_key", "no_cache", "output"}
UPLOAD_ENGINE = "image_upload"
CAP_ERROR = "daily limit reached"
# SerpApi reports an empty result page through the "error" field; that is data, not a failure.
NO_RESULTS = "hasn't returned any results"
KEY_IN_URL = re.compile(r"[?&]api_key=[^&\"'\s]*")


class FixtureMissing(Exception):
    pass


class CapReached(Exception):
    pass


class EngineError(Exception):
    pass


class EngineTimeout(EngineError):
    pass


def canonical_json(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def cache_key(engine: str, params: dict) -> str:
    clean = {k: v for k, v in params.items() if k not in KEY_EXCLUDED}
    return hashlib.sha256(f"{engine}|{canonical_json(clean)}".encode()).hexdigest()


def scrub(obj, key: str | None = None):
    if isinstance(obj, dict):
        return {k: scrub(v, key) for k, v in obj.items() if k != "api_key"}
    if isinstance(obj, list):
        return [scrub(v, key) for v in obj]
    if isinstance(obj, str):
        s = KEY_IN_URL.sub("", obj)
        return s.replace(key, "") if key else s
    return obj


IST = ZoneInfo("Asia/Kolkata")


def day_start(now: datetime | None = None) -> datetime:
    # The daily cap resets at IST midnight; returned as naive UTC to match stored timestamps.
    local = (now or datetime.now(timezone.utc)).astimezone(IST)
    midnight = local.replace(hour=0, minute=0, second=0, microsecond=0)
    return midnight.astimezone(timezone.utc).replace(tzinfo=None)


def live_searches_today(session: Session) -> int:
    q = select(func.count(ApiCall.id)).where(
        ApiCall.created_at >= day_start(),
        ApiCall.cache_hit.is_(False),
        ApiCall.engine != UPLOAD_ENGINE,
        or_(ApiCall.error.is_(None), ApiCall.error != CAP_ERROR),
    )
    return session.scalar(q) or 0


class SerpClient:
    def __init__(self, settings: Settings, session_factory: sessionmaker, http: httpx.AsyncClient | None = None):
        self.settings = settings
        self.sessions = session_factory
        self.http = http or httpx.AsyncClient(timeout=20)

    async def aclose(self) -> None:
        await self.http.aclose()

    async def search(self, engine: str, params: dict, check_id: str | None = None, image: ImageRef | None = None,
                     timeout: float | None = None) -> dict:
        params = {k: v for k, v in params.items() if v is not None}
        key_params = dict(params)
        if image is not None:
            # image_id changes on every upload, so the cache is keyed by the JPEG bytes instead.
            key_params["image_id"] = f"image_sha256:{image.sha256}"
        key = cache_key(engine, key_params)
        mode = self.settings.serpapi_mode

        if mode == "replay":
            path = self.settings.fixture_path / f"{key}.json"
            if not path.exists():
                self._ledger(check_id, engine, key, hit=True, ok=False, error="fixture missing")
                raise FixtureMissing(f"{engine} {key}")
            self._ledger(check_id, engine, key, hit=True, ok=True)
            return json.loads(path.read_text())

        cached = self._cached(key)
        if cached is not None:
            self._ledger(check_id, engine, key, hit=True, ok=True)
            if mode == "record":
                self._write_fixture(key, cached, overwrite=False)
            return cached

        with self.sessions() as s:
            if live_searches_today(s) >= self.settings.daily_search_cap:
                self._ledger(check_id, engine, key, hit=False, ok=False, error=CAP_ERROR)
                raise CapReached(CAP_ERROR)

        try:
            if image is not None:
                params["image_id"] = await self._ensure_image_id(image, check_id)
            data = await self._fetch(engine, params, timeout)
        except EngineError as e:
            self._ledger(check_id, engine, key, hit=False, ok=False, error=str(e))
            raise

        with self.sessions() as s:
            s.merge(SerpCache(key=key, engine=engine, params=key_params, response=data, fetched_at=utcnow()))
            s.commit()
        self._ledger(check_id, engine, key, hit=False, ok=True)
        if mode == "record":
            self._write_fixture(key, data, overwrite=True)
        return data

    def _require_key(self) -> str:
        key = self.settings.api_key()
        if not key:
            raise EngineError("SERPAPI_KEY is not set")
        return key

    def _scrub_msg(self, msg: str) -> str:
        return scrub(msg, self.settings.api_key())

    async def _fetch(self, engine: str, params: dict, timeout: float | None = None) -> dict:
        api_key = self._require_key()
        extra = {"timeout": timeout} if timeout else {}
        try:
            resp = await self.http.get(SEARCH_URL, params={**params, "engine": engine, "api_key": api_key}, **extra)
        except httpx.TimeoutException as e:
            raise EngineTimeout(f"{engine}: {type(e).__name__}") from None
        except httpx.HTTPError as e:
            raise EngineError(f"{engine}: {type(e).__name__}") from None
        try:
            data = resp.json()
        except ValueError:
            raise EngineError(f"{engine}: HTTP {resp.status_code}, body is not JSON") from None
        error = data.get("error") if isinstance(data, dict) else "unexpected response"
        if error and NO_RESULTS not in str(error):
            raise EngineError(self._scrub_msg(f"{engine}: HTTP {resp.status_code}: {error}"))
        if resp.status_code >= 400:
            raise EngineError(f"{engine}: HTTP {resp.status_code}")
        return scrub(data, api_key)

    async def _ensure_image_id(self, image: ImageRef, check_id: str | None) -> str:
        async with image.lock:
            if image.image_id:
                return image.image_id
            api_key = self._require_key()
            try:
                body = await images.upload(self.http, api_key, image.jpeg)
            except httpx.HTTPError as e:
                body = {"error": type(e).__name__}
            image_id = body.get("image_id")
            if not image_id:
                error = self._scrub_msg(f"image upload: {body.get('error') or 'no image_id in response'}")
                self._ledger(check_id, UPLOAD_ENGINE, None, hit=False, ok=False, error=error)
                raise EngineError(error)
            self._ledger(check_id, UPLOAD_ENGINE, None, hit=False, ok=True)
            image.image_id = image_id
            return image_id

    def _cached(self, key: str) -> dict | None:
        with self.sessions() as s:
            row = s.get(SerpCache, key)
            if row is None:
                return None
            if utcnow() - row.fetched_at > timedelta(hours=self.settings.cache_ttl_hours):
                return None
            return row.response

    def _write_fixture(self, key: str, data: dict, overwrite: bool) -> None:
        path = self.settings.fixture_path / f"{key}.json"
        if path.exists() and not overwrite:
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(scrub(data, self.settings.api_key()), indent=1, ensure_ascii=True) + "\n")

    def _ledger(self, check_id, engine, key, hit: bool, ok: bool, error: str | None = None) -> None:
        with self.sessions() as s:
            s.add(ApiCall(check_id=check_id, engine=engine, cache_key=key, cache_hit=hit, ok=ok, error=error))
            s.commit()
