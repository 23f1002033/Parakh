from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import meta
from app.config import Settings, get_settings
from app.db import init_db, make_engine, make_session_factory


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    engine = make_engine(settings.database_url)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        init_db(engine)
        yield
        engine.dispose()

    app = FastAPI(title="Parakh", lifespan=lifespan)
    app.state.settings = settings
    app.state.sessions = make_session_factory(engine)
    app.include_router(meta.router, prefix="/api")
    return app


app = create_app()
