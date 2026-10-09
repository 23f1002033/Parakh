from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException

from app.api import checks, demos, meta, reports, stores
from app.config import BACKEND_DIR, Settings, get_settings
from app.db import init_db, make_engine, make_session_factory
from app.schemas import ApiError
from app.serp.client import SerpClient


FRONTEND_DIST = BACKEND_DIR.parent / "frontend" / "dist"


def error(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse({"error": {"code": code, "message": message}}, status_code=status)


def _validation_message(exc: RequestValidationError) -> str:
    first = exc.errors()[0] if exc.errors() else {}
    field = ".".join(str(p) for p in first.get("loc", ())[1:]) or "input"
    return f"{field}: {first.get('msg', 'invalid value')}"


def mount_spa(app: FastAPI, dist: Path) -> None:
    root = dist.resolve()
    app.mount("/assets", StaticFiles(directory=root / "assets", check_dir=False), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        if path == "api" or path.startswith("api/"):
            raise ApiError(404, "not_found", "Not found")
        file = (root / path).resolve()
        if path and file.is_file() and file.is_relative_to(root):
            return FileResponse(file)
        # Client-side routes (/c/<id>, /s/..., /about) all load the SPA shell.
        return FileResponse(root / "index.html")


def create_app(settings: Settings | None = None, serp: SerpClient | None = None,
               frontend_dist: Path | None = FRONTEND_DIST) -> FastAPI:
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
    if frontend_dist and (frontend_dist / "index.html").is_file():
        mount_spa(app, frontend_dist)
    return app


app = create_app()
