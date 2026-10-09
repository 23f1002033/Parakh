import hashlib
import re

from fastapi import APIRouter, Request

from app.api.stores import find_store, report_out
from app.models import Report
from app.schemas import ReportIn, ReportOut

router = APIRouter()

TAG_RE = re.compile(r"<[^>]*>")
CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def plain_text(note: str | None) -> str | None:
    if not note:
        return None
    text = CONTROL_RE.sub("", TAG_RE.sub("", note)).strip()
    return text or None


def ip_hash(salt: str, ip: str) -> str:
    return hashlib.sha256(f"{salt}|{ip}".encode()).hexdigest()


@router.post("/stores/{kind}/{key}/reports", status_code=201, response_model=ReportOut)
def create_report(kind: str, key: str, body: ReportIn, request: Request):
    salt = request.app.state.settings.ip_salt
    ip = request.client.host if request.client else ""
    with request.app.state.sessions() as s:
        st = find_store(s, kind, key)
        report = Report(store_id=st.id, outcome=body.outcome, note=plain_text(body.note), ip_hash=ip_hash(salt, ip))
        s.add(report)
        s.commit()
        return report_out(report)
