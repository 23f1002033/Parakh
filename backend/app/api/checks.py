import io
import re

from fastapi import APIRouter, BackgroundTasks, File, Form, Request, UploadFile
from PIL import Image, UnidentifiedImageError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.checks.runner import CheckInputs, run_check
from app.models import Check, Evidence, Store, utcnow
from app.normalize import instagram_handle, website_domain
from app.schemas import ApiError, CheckCreated, CheckOut, StoreRef
from app.serp.images import ImageRef
from app.signals.rules import SIGNALS

router = APIRouter()

MAX_IMAGE_BYTES = 5 * 1024 * 1024
IMAGE_FORMATS = {"JPEG", "PNG", "WEBP"}
HANDLE_RE = re.compile(r"^[a-z0-9._]{1,30}$")
DOMAIN_RE = re.compile(r"^[a-z0-9-]+(\.[a-z0-9-]+)+$")


def bad_input(message: str) -> ApiError:
    return ApiError(422, "invalid_input", message)


def store_ref(st: Store) -> StoreRef:
    return StoreRef(kind=st.kind, key=st.key, display=st.display, path=f"/s/{st.kind}/{st.key}")


def upsert_store(s: Session, kind: str, key: str, display: str) -> Store:
    st = s.scalar(select(Store).where(Store.kind == kind, Store.key == key))
    if st is None:
        st = Store(kind=kind, key=key, display=display)
        s.add(st)
    st.last_checked_at = utcnow()
    s.flush()
    return st


def parse_inputs(instagram, website, product_name, image_url) -> tuple[str | None, str | None, str | None, str | None]:
    handle = instagram_handle(instagram) if instagram and instagram.strip() else None
    domain = website_domain(website) if website and website.strip() else None
    if not handle and not domain:
        raise bad_input("Give an Instagram handle or a website")
    if handle is not None and not HANDLE_RE.match(handle):
        raise bad_input("Instagram handle is not valid")
    if domain is not None and not DOMAIN_RE.match(domain):
        raise bad_input("Website is not valid")
    name = product_name.strip() if product_name and product_name.strip() else None
    if name and len(name) > 120:
        raise bad_input("Product name is longer than 120 characters")
    url = image_url.strip() if image_url and image_url.strip() else None
    if url and not re.match(r"^https?://[^\s/]+", url, re.I):
        raise bad_input("Image URL must start with http:// or https://")
    return handle, domain, name, url


async def read_image(image: UploadFile) -> ImageRef:
    data = await image.read(MAX_IMAGE_BYTES + 1)
    if len(data) > MAX_IMAGE_BYTES:
        raise ApiError(413, "image_too_large", "Image is larger than 5 MB")
    try:
        with Image.open(io.BytesIO(data)) as img:
            fmt = img.format
            img.verify()
    except (UnidentifiedImageError, OSError, SyntaxError):
        raise bad_input("File is not a readable image") from None
    if fmt not in IMAGE_FORMATS:
        raise bad_input("Image must be JPG, PNG or WebP")
    return ImageRef.from_bytes(data)


@router.post("/checks", status_code=202, response_model=CheckCreated)
async def create_check(
    request: Request,
    background: BackgroundTasks,
    instagram: str | None = Form(None),
    website: str | None = Form(None),
    product_name: str | None = Form(None),
    quoted_price: int | None = Form(None, ge=1, le=10_000_000),
    image_url: str | None = Form(None),
    image: UploadFile | None = File(None),
):
    handle, domain, name, url = parse_inputs(instagram, website, product_name, image_url)
    has_file = image is not None and bool(image.filename)
    if has_file and url:
        raise bad_input("Give an image file or an image URL, not both")
    ref = await read_image(image) if has_file else None

    with request.app.state.sessions() as s:
        ig = upsert_store(s, "instagram", handle, f"@{handle}") if handle else None
        web = upsert_store(s, "website", domain, domain) if domain else None
        check = Check(
            instagram_store_id=ig.id if ig else None, website_store_id=web.id if web else None,
            product_name=name, quoted_price=quoted_price, image_sha256=ref.sha256 if ref else None,
            image_url=url, status="running", signal_status={n: "pending" for n in SIGNALS},
        )
        s.add(check)
        s.commit()
        check_id = check.id

    inputs = CheckInputs(handle=handle, domain=domain, product_name=name, quoted_price=quoted_price,
                         image=ref, image_url=url)
    background.add_task(run_check, check_id, inputs, request.app.state.serp, request.app.state.sessions)
    return CheckCreated(id=check_id)


@router.get("/checks/{check_id}", response_model=CheckOut)
def get_check(check_id: str, request: Request):
    with request.app.state.sessions() as s:
        check = s.get(Check, check_id)
        if check is None:
            raise ApiError(404, "not_found", "Check not found")
        ids = [i for i in (check.instagram_store_id, check.website_store_id) if i]
        stores = s.scalars(select(Store).where(Store.id.in_(ids)).order_by(Store.kind)).all()
        rows = s.scalars(select(Evidence).where(Evidence.check_id == check_id).order_by(Evidence.position, Evidence.id)).all()
    evidence = {name: [] for name in SIGNALS}
    for e in rows:
        evidence.setdefault(e.signal, []).append(
            {"severity": e.severity, "finding": e.finding, "detail": e.detail, "sources": e.sources or [], "data": e.data}
        )
    return CheckOut(
        id=check.id, status=check.status, created_at=check.created_at, finished_at=check.finished_at,
        product_name=check.product_name, quoted_price=check.quoted_price, has_image=bool(check.image_sha256),
        image_url=check.image_url, stores=[store_ref(st) for st in stores], signal_status=check.signal_status or {},
        verdict=check.verdict, risk_points=check.risk_points, evidence=evidence,
        live_searches=check.live_searches or 0, cached_searches=check.cached_searches or 0,
        duration_ms=check.duration_ms,
    )
