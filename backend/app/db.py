from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

from app.models import Base


def make_engine(url: str) -> Engine:
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    return create_engine(url, connect_args=connect_args)


def make_session_factory(engine: Engine) -> sessionmaker:
    return sessionmaker(bind=engine, expire_on_commit=False)


# Columns added after the first release; create_all does not add columns to existing tables.
ADDED_COLUMNS = {"checks": {"claimed_mrp": "INTEGER"}}


def init_db(engine: Engine) -> None:
    Base.metadata.create_all(engine)
    existing = inspect(engine)
    with engine.begin() as conn:
        for table, columns in ADDED_COLUMNS.items():
            have = {c["name"] for c in existing.get_columns(table)}
            for name, sql_type in columns.items():
                if name not in have:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {sql_type}"))
