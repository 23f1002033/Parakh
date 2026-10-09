from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from app.api import checks, demos, meta, reports, stores
from app.config import Settings, get_settings
from app.db import init_db, make_engine, make_session_factory
from app.schemas import ApiError
from app.serp.client import SerpClient


def error(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse({"error": {"code": code, "message": message}}, status_code=status)


def _validation_message(exc: RequestValidationError) -> str:
    first = exc.errors()[0] if exc.errors() else {}
    field = ".".join(str(p) for p in first.get("loc", ())[1:]) or "input"
    return f"{field}: {first.get('msg', 'invalid value')}"


def create_app(settings: Settings | None = None, serp: SerpClient | None = None) -> FastAPI:
    settings = settings or get_settings()
    engine = make_engine(settings.database_url)
    sessions = make_session_factory(engine)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        init_db(engine)
        app.state.serp = serp or SerpClient(settings, sessions)
        yield
        await app.state.serp.aclose()
        engine.dispose()

    app = FastAPI(title="Parakh", lifespan=lifespan)
    app.state.settings = settings
    app.state.sessions = sessions

    @app.exception_handler(ApiError)
    async def api_error(request: Request, exc: ApiError):
        return error(exc.status, exc.code, exc.message)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError):
        return error(422, "invalid_input", _validation_message(exc))

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException):
        return error(exc.status_code, "not_found" if exc.status_code == 404 else "http_error", str(exc.detail))

    for module in (meta, checks, stores, reports, demos):
        app.include_router(module.router, prefix="/api")
    return app


app = create_app()
