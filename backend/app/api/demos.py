import json

from fastapi import APIRouter
from fastapi.responses import FileResponse

from app.config import BACKEND_DIR
from app.schemas import ApiError, Demo

router = APIRouter()

DEMO_DIR = BACKEND_DIR / "demo"


def load_demos() -> list[dict]:
    entries = json.loads((DEMO_DIR / "demos.json").read_text())
    return [e for e in entries if not e.get("todo")]


@router.get("/demos", response_model=list[Demo])
def list_demos():
    return [
        Demo(**{k: e.get(k) for k in ("name", "instagram", "website", "product_name", "quoted_price", "claimed_mrp", "image")},
             image_path=f"/api/demos/{e['name']}/image" if e.get("image") else None)
        for e in load_demos()
    ]


@router.get("/demos/{name}/image")
def demo_image(name: str):
    entry = next((e for e in load_demos() if e["name"] == name), None)
    # Only names from demos.json resolve to files, so no user path reaches the filesystem.
    path = DEMO_DIR / entry["image"] if entry and entry.get("image") else None
    if path is None or path.parent != DEMO_DIR or not path.is_file():
        raise ApiError(404, "not_found", "Demo image not found")
    return FileResponse(path)
