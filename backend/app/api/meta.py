from fastapi import APIRouter, Request
from sqlalchemy import func, select

from app.models import ApiCall
from app.serp.client import UPLOAD_ENGINE, day_start, live_searches_today
from app.signals.rules import rules_as_data

router = APIRouter()


@router.get("/health")
def health():
    return {"ok": True}


@router.get("/meta/credits")
def credits(request: Request):
    settings = request.app.state.settings
    with request.app.state.sessions() as s:
        live = live_searches_today(s)
        today = (ApiCall.created_at >= day_start(), ApiCall.engine != UPLOAD_ENGINE, ApiCall.ok.is_(True))
        total = s.scalar(select(func.count(ApiCall.id)).where(*today)) or 0
        hits = s.scalar(select(func.count(ApiCall.id)).where(*today, ApiCall.cache_hit.is_(True))) or 0
    return {
        "live_searches_today": live,
        "daily_cap": settings.daily_search_cap,
        "cache_hit_rate_today": round(hits / total, 3) if total else None,
        "mode": settings.serpapi_mode,
    }


@router.get("/meta/rules")
def rules():
    return rules_as_data()
