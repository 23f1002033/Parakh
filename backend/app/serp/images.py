import asyncio
import hashlib
import io
from dataclasses import dataclass, field

import httpx
from PIL import Image, ImageOps

UPLOAD_URL = "https://serpapi.com/image"
MAX_BYTES = 480 * 1024


def to_jpeg(data: bytes) -> tuple[bytes, str]:
    """JPEG bytes no larger than MAX_BYTES, and their sha256 hex."""
    img = ImageOps.exif_transpose(Image.open(io.BytesIO(data)))
    if img.mode in ("RGBA", "LA", "P"):
        img = img.convert("RGBA")
        bg = Image.new("RGB", img.size, (255, 255, 255))
        bg.paste(img, mask=img.getchannel("A"))
        img = bg
    else:
        img = img.convert("RGB")
    while True:
        buf = io.BytesIO()
        img.save(buf, "JPEG", quality=85, optimize=True)
        out = buf.getvalue()
        if len(out) <= MAX_BYTES or min(img.size) <= 64:
            break
        img = img.resize((max(1, int(img.width * 0.8)), max(1, int(img.height * 0.8))), Image.LANCZOS)
    return out, hashlib.sha256(out).hexdigest()


@dataclass
class ImageRef:
    jpeg: bytes
    sha256: str
    image_id: str | None = None
    lock: asyncio.Lock = field(default_factory=asyncio.Lock, repr=False)

    @classmethod
    def from_bytes(cls, data: bytes) -> "ImageRef":
        jpeg, sha = to_jpeg(data)
        return cls(jpeg=jpeg, sha256=sha)


async def upload(http: httpx.AsyncClient, api_key: str, jpeg: bytes) -> dict:
    resp = await http.post(
        UPLOAD_URL,
        data={"api_key": api_key},
        files={"image": ("image.jpg", jpeg, "image/jpeg")},
    )
    try:
        body = resp.json()
    except ValueError:
        body = {}
    if resp.status_code >= 400 and "error" not in body:
        body["error"] = f"HTTP {resp.status_code}"
    return body
