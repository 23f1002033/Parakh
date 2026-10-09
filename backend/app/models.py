import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


def utcnow() -> datetime:
    # Stored naive in UTC; SQLite drops tzinfo anyway.
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Store(Base):
    __tablename__ = "stores"
    __table_args__ = (UniqueConstraint("kind", "key"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(16))
    key: Mapped[str] = mapped_column(String(255))
    display: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime)


class Check(Base):
    __tablename__ = "checks"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: uuid.uuid4().hex)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)
    instagram_store_id: Mapped[int | None] = mapped_column(ForeignKey("stores.id"))
    website_store_id: Mapped[int | None] = mapped_column(ForeignKey("stores.id"))
    product_name: Mapped[str | None] = mapped_column(String(120))
    quoted_price: Mapped[int | None] = mapped_column(Integer)
    image_sha256: Mapped[str | None] = mapped_column(String(64))
    image_url: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16), default="running")
    signal_status: Mapped[dict] = mapped_column(JSON, default=dict)
    verdict: Mapped[str | None] = mapped_column(String(32))
    risk_points: Mapped[int | None] = mapped_column(Integer)
    live_searches: Mapped[int] = mapped_column(Integer, default=0)
    cached_searches: Mapped[int] = mapped_column(Integer, default=0)
    duration_ms: Mapped[int | None] = mapped_column(Integer)


class Evidence(Base):
    __tablename__ = "evidence"

    id: Mapped[int] = mapped_column(primary_key=True)
    check_id: Mapped[str] = mapped_column(ForeignKey("checks.id"), index=True)
    signal: Mapped[str] = mapped_column(String(32))
    severity: Mapped[str] = mapped_column(String(8))
    finding: Mapped[str] = mapped_column(Text)
    detail: Mapped[str | None] = mapped_column(Text)
    sources: Mapped[list] = mapped_column(JSON, default=list)
    data: Mapped[dict | None] = mapped_column(JSON)
    position: Mapped[int] = mapped_column(Integer, default=0)


class SerpCache(Base):
    __tablename__ = "serp_cache"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    engine: Mapped[str] = mapped_column(String(32))
    params: Mapped[dict] = mapped_column(JSON)
    response: Mapped[dict] = mapped_column(JSON)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class ApiCall(Base):
    __tablename__ = "api_calls"

    id: Mapped[int] = mapped_column(primary_key=True)
    # No FK: tools record calls outside any check.
    check_id: Mapped[str | None] = mapped_column(String(64), index=True)
    engine: Mapped[str] = mapped_column(String(32))
    cache_key: Mapped[str | None] = mapped_column(String(64))
    cache_hit: Mapped[bool] = mapped_column(Boolean)
    ok: Mapped[bool] = mapped_column(Boolean)
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(primary_key=True)
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id"), index=True)
    outcome: Mapped[str] = mapped_column(String(16))
    note: Mapped[str | None] = mapped_column(String(280))
    ip_hash: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
