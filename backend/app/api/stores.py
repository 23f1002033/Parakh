from fastapi import APIRouter, Request
from sqlalchemy import func, or_, select

from app.api.checks import store_ref
from app.models import Check, Report, Store
from app.normalize import instagram_handle, website_domain
from app.schemas import ApiError, CheckSummary, ReportOut, StorePage
from app.signals.rules import OUTCOMES

router = APIRouter()

PAGE_SIZE = 20


def find_store(s, kind: str, key: str) -> Store:
    if kind == "instagram":
        key = instagram_handle(key)
    elif kind == "website":
        key = website_domain(key)
    else:
        raise ApiError(404, "not_found", "Store not found")
    st = s.scalar(select(Store).where(Store.kind == kind, Store.key == key))
    if st is None:
        raise ApiError(404, "not_found", "Store not found")
    return st


def report_out(r: Report) -> ReportOut:
    return ReportOut(id=r.id, outcome=r.outcome, note=r.note, created_at=r.created_at)


@router.get("/stores/{kind}/{key}", response_model=StorePage)
def get_store(kind: str, key: str, request: Request):
    with request.app.state.sessions() as s:
        st = find_store(s, kind, key)
        checks = s.scalars(
            select(Check).where(or_(Check.instagram_store_id == st.id, Check.website_store_id == st.id))
            .order_by(Check.created_at.desc()).limit(PAGE_SIZE)
        ).all()
        counts = dict(s.execute(select(Report.outcome, func.count()).where(Report.store_id == st.id)
                                .group_by(Report.outcome)).all())
        reports = s.scalars(select(Report).where(Report.store_id == st.id)
                            .order_by(Report.created_at.desc(), Report.id.desc()).limit(PAGE_SIZE)).all()
    return StorePage(
        store=store_ref(st), created_at=st.created_at, last_checked_at=st.last_checked_at,
        checks=[CheckSummary(id=c.id, created_at=c.created_at, verdict=c.verdict, status=c.status) for c in checks],
        report_counts={o: counts.get(o, 0) for o in OUTCOMES},
        reports=[report_out(r) for r in reports],
    )
