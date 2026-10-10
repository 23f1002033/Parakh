import re
from dataclasses import dataclass, field
from datetime import date

from app.normalize import parse_caption_date, parse_currency
from app.serp.client import EngineTimeout, SerpClient
from app.serp.images import ImageRef

COMPLAINT_TERMS = 'scam OR fraud OR fake OR "not delivered" OR refund'
# Forums timed out at 20 s during the M1 recording.
FORUMS_TIMEOUT = 30
# A handle like "the.red.store" is often written as "the red store"; two-word handles
# keep the plain query (spaced two-word names are usually product names, and demo 1
# fixtures depend on the old query).
SPACED_HANDLE_MIN_WORDS = 3


def store_query_term(handle: str | None, domain: str | None) -> str:
    if handle:
        words = [w for w in re.split(r"[._]+", handle) if w]
        if len(words) >= SPACED_HANDLE_MIN_WORDS:
            return f'("{handle}" OR "{" ".join(words)}")'
        return f'"{handle}"'
    return f'"{domain}"'


def complaints_query(handle: str | None, domain: str | None) -> str:
    return f"{store_query_term(handle, domain)} {COMPLAINT_TERMS}"


def forums_query(handle: str | None, domain: str | None) -> str:
    return store_query_term(handle, domain)


def _list(v) -> list:
    return v if isinstance(v, list) else []


def _dict(v) -> dict:
    return v if isinstance(v, dict) else {}


def _str(v) -> str | None:
    return v if isinstance(v, str) and v else None


def _int(v) -> int | None:
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return int(v)
    if isinstance(v, str) and v.replace(",", "").isdigit():
        return int(v.replace(",", ""))
    return None


def _bool(v) -> bool:
    return v is True


def _search_url(data: dict) -> str | None:
    meta = _dict(data.get("search_metadata"))
    for k in ("google_lens_url", "google_shopping_url", "google_url", "google_maps_url", "instagram_url"):
        if _str(meta.get(k)):
            return meta[k]
    return None


@dataclass
class LensMatch:
    title: str | None
    link: str | None
    source: str | None
    price_value: float | None = None
    price_currency: str | None = None
    price_inr: int | None = None
    in_stock: bool | None = None
    condition: str | None = None
    exact_match: bool = False


@dataclass
class LensResult:
    matches: list[LensMatch] = field(default_factory=list)
    search_url: str | None = None


@dataclass
class InstagramPost:
    shortcode: str | None
    url: str | None
    caption: str | None
    posted_on: date | None


@dataclass
class InstagramProfile:
    handle: str
    url: str
    full_name: str | None = None
    followers: int | None = None
    following: int | None = None
    is_private: bool = False
    is_verified: bool = False
    is_professional: bool = False
    biography: str | None = None
    external_url: str | None = None
    bio_links: list[str] = field(default_factory=list)
    posts: list[InstagramPost] = field(default_factory=list)


@dataclass
class SearchResult:
    title: str | None
    link: str | None
    snippet: str | None = None
    date: str | None = None
    source: str | None = None
    displayed_meta: str | None = None


@dataclass
class SearchResults:
    results: list[SearchResult] = field(default_factory=list)
    search_url: str | None = None


@dataclass
class ShoppingItem:
    title: str | None
    link: str | None
    source: str | None = None
    price_inr: int | None = None
    price_text: str | None = None


@dataclass
class ShoppingResult:
    items: list[ShoppingItem] = field(default_factory=list)
    search_url: str | None = None


@dataclass
class Place:
    title: str | None
    link: str | None
    address: str | None = None
    rating: float | None = None
    reviews: int | None = None
    type: str | None = None


@dataclass
class MapsResult:
    places: list[Place] = field(default_factory=list)
    search_url: str | None = None
    # Raw keys of the first place; fields are still being confirmed against real responses.
    raw_fields: list[str] = field(default_factory=list)


def _lens_params(kind: str, url: str | None, image: ImageRef | None) -> dict:
    if (url is None) == (image is None):
        raise ValueError("pass exactly one of url or image")
    return {"type": kind, "url": url, "country": "in"}


async def lens_all(client: SerpClient, *, url: str | None = None, image: ImageRef | None = None,
                   check_id: str | None = None) -> LensResult:
    # No q: with a product name Lens returned 0 visual matches; name filtering happens in our code.
    params = {**_lens_params("all", url, image), "hl": "en"}
    data = await client.search("google_lens", params, check_id, image=image)
    matches = []
    for m in _list(data.get("visual_matches")):
        m = _dict(m)
        price = _dict(m.get("price"))
        value = price.get("extracted_value")
        matches.append(LensMatch(
            title=_str(m.get("title")),
            link=_str(m.get("link")),
            source=_str(m.get("source")),
            price_value=float(value) if isinstance(value, (int, float)) else None,
            price_currency=_str(price.get("currency")),
            price_inr=parse_currency(price),
            in_stock=m.get("in_stock") if isinstance(m.get("in_stock"), bool) else None,
            condition=_str(m.get("condition")),
            exact_match=bool(m.get("exact_matches")),
        ))
    return LensResult(matches=matches, search_url=_search_url(data))


async def lens_exact(client: SerpClient, *, url: str | None = None, image: ImageRef | None = None,
                     check_id: str | None = None) -> LensResult:
    data = await client.search("google_lens", _lens_params("exact_matches", url, image), check_id, image=image)
    matches = [
        LensMatch(title=_str(m.get("title")), link=_str(m.get("link")), source=_str(m.get("source")), exact_match=True)
        for m in map(_dict, _list(data.get("exact_matches")))
    ]
    return LensResult(matches=matches, search_url=_search_url(data))


async def instagram_profile(client: SerpClient, handle: str, check_id: str | None = None) -> InstagramProfile:
    data = await client.search("instagram_profile", {"profile_id": handle}, check_id)
    p = _dict(data.get("profile_results"))
    bio_links = []
    for b in _list(p.get("bio_links")):
        link = _str(b) or _str(_dict(b).get("url"))
        if link:
            bio_links.append(link)
    posts = []
    for post in map(_dict, _list(p.get("posts"))):
        code = _str(post.get("shortcode"))
        caption = _str(post.get("accessibility_caption"))
        posts.append(InstagramPost(
            shortcode=code,
            url=f"https://www.instagram.com/p/{code}/" if code else None,
            caption=caption,
            posted_on=parse_caption_date(caption),
        ))
    return InstagramProfile(
        handle=handle,
        url=f"https://www.instagram.com/{handle}/",
        full_name=_str(p.get("full_name")),
        followers=_int(p.get("followers")),
        following=_int(p.get("following")),
        is_private=_bool(p.get("is_private")),
        is_verified=_bool(p.get("is_verified")),
        is_professional=_bool(p.get("is_professional_account")),
        biography=_str(p.get("biography")),
        external_url=_str(p.get("external_url")),
        bio_links=bio_links,
        posts=posts,
    )


def _results(data: dict) -> SearchResults:
    results = [
        SearchResult(
            title=_str(r.get("title")),
            link=_str(r.get("link")),
            snippet=_str(r.get("snippet")),
            date=_str(r.get("date")),
            source=_str(r.get("source")),
            displayed_meta=_str(r.get("displayed_meta")),
        )
        for r in map(_dict, _list(data.get("organic_results")))
    ]
    return SearchResults(results=results, search_url=_search_url(data))


async def google_search(client: SerpClient, q: str, check_id: str | None = None, hl: str | None = "en") -> SearchResults:
    data = await client.search("google", {"q": q, "gl": "in", "hl": hl}, check_id)
    return _results(data)


async def website_footprint(client: SerpClient, domain: str, check_id: str | None = None) -> SearchResults:
    # Design section 3: q=domain, gl=in, no hl.
    return await google_search(client, domain, check_id, hl=None)


async def google_forums(client: SerpClient, q: str, check_id: str | None = None) -> SearchResults:
    params = {"q": q, "gl": "in", "hl": "en"}
    try:
        data = await client.search("google_forums", params, check_id, timeout=FORUMS_TIMEOUT)
    except EngineTimeout:
        data = await client.search("google_forums", params, check_id, timeout=FORUMS_TIMEOUT)
    return _results(data)


async def google_shopping(client: SerpClient, q: str, check_id: str | None = None) -> ShoppingResult:
    data = await client.search("google_shopping", {"q": q, "gl": "in", "hl": "en"}, check_id)
    items = []
    for r in map(_dict, _list(data.get("shopping_results"))):
        value = r.get("extracted_price")
        items.append(ShoppingItem(
            title=_str(r.get("title")),
            link=_str(r.get("link")) or _str(r.get("product_link")),
            source=_str(r.get("source")),
            price_inr=parse_currency({"value": r.get("price"), "extracted_value": value}),
            price_text=_str(r.get("price")),
        ))
    return ShoppingResult(items=items, search_url=_search_url(data))


async def google_maps(client: SerpClient, q: str, check_id: str | None = None) -> MapsResult:
    data = await client.search("google_maps", {"q": q, "type": "search"}, check_id)
    raw = _list(data.get("local_results"))
    if not raw and data.get("place_results"):
        raw = [data["place_results"]]
    places = []
    for r in map(_dict, raw):
        place_id = _str(r.get("place_id"))
        places.append(Place(
            title=_str(r.get("title")),
            link=f"https://www.google.com/maps/place/?q=place_id:{place_id}" if place_id else None,
            address=_str(r.get("address")),
            rating=float(r["rating"]) if isinstance(r.get("rating"), (int, float)) else None,
            reviews=_int(r.get("reviews")),
            type=_str(r.get("type")),
        ))
    raw_fields = sorted(_dict(raw[0]).keys()) if raw else []
    return MapsResult(places=places, search_url=_search_url(data), raw_fields=raw_fields)
