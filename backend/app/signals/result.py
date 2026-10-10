from dataclasses import dataclass, field
from urllib.parse import urlparse

from app.normalize import tokens, website_domain
from app.signals.rules import MAJOR_RETAILERS


@dataclass
class Item:
    severity: str
    finding: str
    detail: str | None = None
    sources: list[dict] = field(default_factory=list)
    data: dict | None = None


@dataclass
class SignalResult:
    status: str
    reason: str | None = None
    items: list[Item] = field(default_factory=list)


def done(*items: Item) -> SignalResult:
    return SignalResult("done", None, list(items))


def skipped(reason: str) -> SignalResult:
    return SignalResult("skipped", reason, [Item("info", reason)])


def unavailable(reason: str) -> SignalResult:
    return SignalResult("unavailable", reason, [Item("info", f"Source unavailable: {reason}")])


def source(title: str | None, url: str | None, engine: str) -> dict:
    return {"title": title or url or "", "url": url or "", "engine": engine}


def domain_of(url: str | None) -> str:
    if not url:
        return ""
    host = urlparse(url).hostname
    return website_domain(host) if host else ""


def is_own_url(url: str | None, handle: str | None, store_domain: str | None) -> bool:
    """True for the store's own website (any subdomain) or its own Instagram profile."""
    domain = domain_of(url)
    if not domain:
        return False
    if store_domain and (domain == store_domain or domain.endswith("." + store_domain)):
        return True
    if handle and domain == "instagram.com":
        path = url.split("instagram.com", 1)[1].strip("/").lower()
        return path.split("/")[0].split("?")[0] == handle
    return False


def domain_labels(domain: str) -> list[str]:
    return [p for p in domain.split(".") if p]


def is_major_retailer(domain: str, source_name: str | None = None) -> bool:
    if any(label in MAJOR_RETAILERS for label in domain_labels(domain)):
        return True
    return bool(tokens(source_name) & set(MAJOR_RETAILERS))


def is_brand_site(domain: str, product_name: str | None) -> bool:
    # The brand is not known separately; a site counts as the brand's when a word of
    # the product name (letters only, 3+ chars) appears in its name, e.g. boat-lifestyle.com.
    if not domain or not product_name:
        return False
    name_words = {t for t in tokens(product_name) if t.isalpha() and len(t) >= 3}
    site_words = tokens(" ".join(domain_labels(domain)[:-1]))
    return bool(name_words & site_words)
