import asyncio
import logging
import time
from dataclasses import dataclass
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import sessionmaker

from app.models import ApiCall, Check, Evidence, Report, Store, utcnow
from app.serp import engines
from app.serp.client import CAP_ERROR, UPLOAD_ENGINE, CapReached, EngineError, EngineTimeout, FixtureMissing, SerpClient
from app.serp.images import ImageRef
from app.signals import account, community, complaints, photo, price, rules, verdict
from app.signals.result import SignalResult, skipped, unavailable

log = logging.getLogger(__name__)


@dataclass
class CheckInputs:
    handle: str | None = None
    domain: str | None = None
    product_name: str | None = None
    quoted_price: int | None = None
    claimed_mrp: int | None = None
    image: ImageRef | None = None
    image_url: str | None = None


def reason_for(exc: BaseException) -> str:
    if isinstance(exc, CapReached):
        return "daily limit reached"
    if isinstance(exc, FixtureMissing):
        return "no recorded data"
    if isinstance(exc, (EngineTimeout, asyncio.TimeoutError)):
        return "source timed out"
    return "source error"


async def _attempt(coro):
    try:
        return await coro, None
    except Exception as e:
        return None, e


def search_counts(sessions: sessionmaker, check_id: str) -> tuple[int, int]:
    """(live, cached). Failed live calls still count as live; a missing fixture is not a cached search."""
    base = (ApiCall.check_id == check_id, ApiCall.engine != UPLOAD_ENGINE)
    with sessions() as s:
        live = s.scalar(select(func.count()).where(
            *base, ApiCall.cache_hit.is_(False), (ApiCall.error.is_(None)) | (ApiCall.error != CAP_ERROR)))
        cached = s.scalar(select(func.count()).where(*base, ApiCall.cache_hit.is_(True), ApiCall.ok.is_(True)))
    return live or 0, cached or 0


class Runner:
    def __init__(self, check_id: str, inputs: CheckInputs, client: SerpClient, sessions: sessionmaker,
                 today: date | None = None):
        self.id = check_id
        self.inp = inputs
        self.client = client
        self.sessions = sessions
        self.today = today or date.today()
        self.profile_task: asyncio.Task | None = None

    async def price(self) -> SignalResult:
        name = self.inp.product_name
        if not name:
            return price.evaluate(None, None, None, None)
        lens, lens_err = None, None
        if self.inp.image or self.inp.image_url:
            lens, lens_err = await _attempt(engines.lens_all(
                self.client, url=self.inp.image_url, image=self.inp.image, check_id=self.id))
        domain, mrp = self.inp.domain, self.inp.claimed_mrp
        if price.lens_is_enough(name, lens, domain):
            return price.evaluate(name, self.inp.quoted_price, lens, None, domain, mrp)
        shop, shop_err = await _attempt(engines.google_shopping(self.client, name, self.id))
        # A needed fallback that failed would make "not enough matches" a false claim.
        if shop is None:
            return unavailable(reason_for(shop_err or lens_err))
        return price.evaluate(name, self.inp.quoted_price, lens, shop, domain, mrp)

    async def photo(self) -> SignalResult:
        if not (self.inp.image or self.inp.image_url):
            return skipped("No product photo given")
        exact = await engines.lens_exact(self.client, url=self.inp.image_url, image=self.inp.image, check_id=self.id)
        return photo.evaluate(exact, self.inp.handle, self.inp.domain, self.inp.product_name)

    async def complaints(self) -> SignalResult:
        handle, domain = self.inp.handle, self.inp.domain
        (google, g_err), (forums, f_err) = await asyncio.gather(
            _attempt(engines.google_search(self.client, engines.complaints_query(handle, domain), self.id)),
            _attempt(engines.google_forums(self.client, engines.forums_query(handle, domain), self.id)),
        )
        if google is None and forums is None:
            return unavailable(reason_for(g_err or f_err))
        full_name = None
        if self.profile_task:
            profile, _ = await _attempt(self.profile_task)
            full_name = profile.full_name if profile else None
        terms = complaints.store_terms(self.inp.handle, self.inp.domain, full_name)
        return complaints.evaluate(google, forums, terms, handle, domain)

    async def account(self) -> SignalResult:
        if not self.profile_task:
            return skipped("No Instagram handle given")
        try:
            profile = await self.profile_task
        except engines.ProfileNotFound:
            return account.not_found(self.inp.handle)
        return account.evaluate(profile, self.inp.domain, self.today)

    def community(self) -> tuple[SignalResult, int, int]:
        with self.sessions() as s:
            check = s.get(Check, self.id)
            ids = [i for i in (check.instagram_store_id, check.website_store_id) if i]
            stores = s.scalars(select(Store).where(Store.id.in_(ids))).all()
            rows = s.execute(select(Report.outcome, func.count()).where(Report.store_id.in_(ids))
                             .group_by(Report.outcome)).all()
        counts = {o: n for o, n in rows}
        pages = [(f"Store page for {st.display}", f"/s/{st.kind}/{st.key}") for st in stores]
        neg, pos = community.counts_points(counts)
        return community.evaluate(counts, pages), neg, pos

    async def _signal(self, name: str, fn) -> SignalResult:
        try:
            result = await fn()
        except (CapReached, FixtureMissing, EngineError) as e:
            result = unavailable(reason_for(e))
        except Exception:
            log.exception("signal %s failed in check %s", name, self.id)
            result = unavailable("internal error")
        self.save(name, result)
        return result

    def save(self, name: str, result: SignalResult) -> None:
        base = rules.SIGNALS.index(name) * 100
        with self.sessions() as s:
            for i, item in enumerate(result.items):
                s.add(Evidence(check_id=self.id, signal=name, severity=item.severity, finding=item.finding,
                               detail=item.detail, sources=item.sources, data=item.data, position=base + i))
            check = s.get(Check, self.id)
            check.signal_status = {**check.signal_status, name: result.status}
            s.commit()

    async def run(self) -> None:
        start = time.monotonic()
        with self.sessions() as s:
            check = s.get(Check, self.id)
            check.signal_status = {name: "pending" for name in rules.SIGNALS}
            s.commit()
        try:
            if self.inp.handle:
                self.profile_task = asyncio.create_task(engines.instagram_profile(self.client, self.inp.handle, self.id))
                # Retrieved by the account signal; this keeps an unread failure from being logged as lost.
                self.profile_task.add_done_callback(lambda t: t.cancelled() or t.exception())
            names = ("price", "photo", "complaints", "account")
            outs = await asyncio.gather(*(self._signal(n, getattr(self, n)) for n in names), return_exceptions=True)
            results = {n: (r if isinstance(r, SignalResult) else unavailable("internal error")) for n, r in zip(names, outs)}
            try:
                results["community"], neg, pos = self.community()
            except Exception:
                log.exception("community signal failed in check %s", self.id)
                results["community"], neg, pos = unavailable("internal error"), 0, 0
            self.save("community", results["community"])
            label, points = verdict.evaluate(results, neg, pos)
            status = "done"
        except Exception:
            log.exception("check %s failed", self.id)
            label, points, status = None, None, "failed"
        live, cached = search_counts(self.sessions, self.id)
        with self.sessions() as s:
            check = s.get(Check, self.id)
            check.verdict, check.risk_points, check.status = label, points, status
            check.live_searches, check.cached_searches = live, cached
            check.finished_at = utcnow()
            check.duration_ms = int((time.monotonic() - start) * 1000)
            s.commit()


async def run_check(check_id: str, inputs: CheckInputs, client: SerpClient, sessions: sessionmaker) -> None:
    await Runner(check_id, inputs, client, sessions).run()
