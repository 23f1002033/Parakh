from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

Outcome = Literal["delivered", "not_delivered", "differs", "other"]


class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str, headers: dict | None = None):
        self.status, self.code, self.message, self.headers = status, code, message, headers


class CheckCreated(BaseModel):
    id: str


class SourceOut(BaseModel):
    title: str
    url: str
    engine: str


class EvidenceOut(BaseModel):
    severity: str
    finding: str
    detail: str | None
    sources: list[SourceOut]
    data: dict | None


class StoreRef(BaseModel):
    kind: str
    key: str
    display: str
    path: str


class CheckOut(BaseModel):
    id: str
    status: str
    created_at: datetime
    finished_at: datetime | None
    product_name: str | None
    quoted_price: int | None
    claimed_mrp: int | None
    has_image: bool
    image_url: str | None
    stores: list[StoreRef]
    signal_status: dict[str, str]
    verdict: str | None
    risk_points: int | None
    evidence: dict[str, list[EvidenceOut]]
    live_searches: int
    cached_searches: int
    duration_ms: int | None


class ReportIn(BaseModel):
    outcome: Outcome
    note: str | None = Field(default=None, max_length=280)


class ReportOut(BaseModel):
    id: int
    outcome: str
    note: str | None
    created_at: datetime


class CheckSummary(BaseModel):
    id: str
    created_at: datetime
    verdict: str | None
    status: str


class StorePage(BaseModel):
    store: StoreRef
    created_at: datetime
    last_checked_at: datetime | None
    checks: list[CheckSummary]
    report_counts: dict[str, int]
    reports: list[ReportOut]


class Demo(BaseModel):
    name: str
    instagram: str | None
    website: str | None
    product_name: str | None
    quoted_price: int | None
    claimed_mrp: int | None = None
    image: str | None
    image_path: str | None
