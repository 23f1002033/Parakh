from app.serp.engines import LensResult
from app.signals import rules
from app.signals.result import Item, SignalResult, domain_labels, domain_of, done, is_brand_site, is_major_retailer, source

NO_COPIES = ("No exact copies found. Screenshots and edited photos often have none, "
             "so this is not proof the photo is original.")


def _is_own(url: str, domain: str, handle: str | None, store_domain: str | None) -> bool:
    if store_domain and (domain == store_domain or domain.endswith("." + store_domain)):
        return True
    if handle and domain == "instagram.com":
        path = url.split("instagram.com", 1)[1].strip("/").lower()
        return path.split("/")[0] == handle
    return False


def _marketplace(domain: str) -> str | None:
    return next((label for label in domain_labels(domain) if label in rules.MARKETPLACES), None)


def evaluate(exact: LensResult, handle: str | None, store_domain: str | None, product_name: str | None) -> SignalResult:
    by_domain: dict[str, list] = {}
    for m in exact.matches:
        domain = domain_of(m.link)
        if not domain or _is_own(m.link, domain, handle, store_domain):
            continue
        by_domain.setdefault(domain, []).append(m)

    groups = [
        {"domain": d, "count": len(ms), "marketplace": _marketplace(d),
         "brand_or_retailer": is_brand_site(d, product_name) or is_major_retailer(d, ms[0].source)}
        for d, ms in sorted(by_domain.items(), key=lambda kv: -len(kv[1]))
    ]
    sources = [source(ms[0].title, ms[0].link, "google_lens") for ms in
               sorted(by_domain.values(), key=lambda ms: -len(ms))][:10]
    data = {"domains": groups, "matches": sum(g["count"] for g in groups)}

    markets = sorted({g["marketplace"] for g in groups if g["marketplace"]})
    if markets:
        names = ", ".join(markets)
        return done(Item("warn", f"Same photo appears on {names}",
                         "Marketplace listings using the same photo often mean the item is resold.", sources, data))
    if len(groups) >= rules.PHOTO_MANY_SITES:
        return done(Item("info", f"Photo is used on {len(groups)} other sites", None, sources, data))
    if groups and all(g["brand_or_retailer"] for g in groups):
        return done(Item("info", "Photo is the brand's own product image", None, sources, data))
    if groups:
        n = len(groups)
        return done(Item("info", f"Photo is used on {n} other site{'s' if n > 1 else ''}", None, sources, data))
    return done(Item("info", NO_COPIES, None, [], data))
