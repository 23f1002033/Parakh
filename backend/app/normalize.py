import re
import unicodedata
from datetime import date, datetime
from urllib.parse import urlparse

RUPEE = "\u20b9"
INR_MARKERS = ("rs", "inr", RUPEE)

MONTHS = "January|February|March|April|May|June|July|August|September|October|November|December"
CAPTION_DATE = re.compile(rf"\bon ({MONTHS}) (\d{{1,2}}), (\d{{4}})")


def instagram_handle(value: str) -> str:
    s = value.strip()
    if "instagram.com" in s.lower():
        if "://" not in s:
            s = "https://" + s
        path = urlparse(s).path.strip("/")
        s = path.split("/")[0] if path else ""
    return s.lstrip("@").strip().strip("/").lower()


def website_domain(value: str) -> str:
    s = value.strip()
    if "://" not in s:
        s = "http://" + s
    host = (urlparse(s).hostname or "").lower().rstrip(".")
    return host[4:] if host.startswith("www.") else host


def _is_inr(text: str) -> bool:
    t = text.strip().lower()
    return any(t.startswith(m) for m in INR_MARKERS)


def parse_currency(price: dict | None) -> int | None:
    """INR rupees from a SerpApi price object, or None if not in INR."""
    if not isinstance(price, dict):
        return None
    currency = str(price.get("currency") or "")
    value = str(price.get("value") or "")
    if not (_is_inr(currency) if currency else _is_inr(value)):
        return None
    extracted = price.get("extracted_value")
    if isinstance(extracted, (int, float)) and extracted > 0:
        return round(extracted)
    m = re.search(r"\d[\d,]*(?:\.\d+)?", value)
    if not m:
        return None
    return round(float(m.group(0).replace(",", ""))) or None


def parse_caption_date(caption: str | None) -> date | None:
    if not caption:
        return None
    m = CAPTION_DATE.search(caption)
    if not m:
        return None
    try:
        return datetime.strptime(f"{m.group(1)} {m.group(2)} {m.group(3)}", "%B %d %Y").date()
    except ValueError:
        return None


def normalize_text(text: str | None) -> str:
    if not text:
        return ""
    s = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()
    return " ".join(re.sub(r"[^a-z0-9]+", " ", s).split())


def tokens(text: str | None) -> set[str]:
    return set(normalize_text(text).split())


def jaccard(a: str | None, b: str | None) -> float:
    ta, tb = tokens(a), tokens(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)
