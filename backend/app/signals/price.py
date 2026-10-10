from dataclasses import dataclass
from statistics import median

from app.normalize import normalize_text, tokens
from app.serp.engines import LensResult, ShoppingResult
from app.signals import rules
from app.signals.result import (
    Item, SignalResult, domain_of, done, is_brand_site, is_major_retailer, is_own_url, skipped, source,
)

ENGINE_LABELS = {"google_lens": "Google Lens", "google_shopping": "Google Shopping"}


@dataclass
class Listing:
    title: str | None
    link: str | None
    source: str | None
    price_inr: int | None
    condition: str | None
    engine: str


def lens_listings(lens: LensResult | None) -> list[Listing]:
    if lens is None:
        return []
    return [Listing(m.title, m.link, m.source, m.price_inr, m.condition, "google_lens") for m in lens.matches]


def shopping_listings(shop: ShoppingResult | None) -> list[Listing]:
    if shop is None:
        return []
    return [Listing(i.title, i.link, i.source, i.price_inr, None, "google_shopping") for i in shop.items]


def same_product(product_name: str, title: str | None, condition: str | None) -> bool:
    name, words = tokens(product_name), tokens(title)
    if not name or not words:
        return False
    if (condition or "").strip().lower() not in rules.ALLOWED_CONDITIONS:
        return False
    if len(name & words) / len(name) < rules.PRICE_CONTAINMENT:
        return False
    # Model numbers must match exactly: "Rockerz 255" is not "Rockerz 110".
    return all(t in words for t in name if any(c.isdigit() for c in t))


def _dedupe(listings: list[Listing]) -> list[Listing]:
    # The same offer often appears twice under different URLs (e.g. two Flipkart paths).
    out, urls, offers = [], set(), set()
    for x in listings:
        url = (x.link or "").split("#")[0].rstrip("/").lower()
        offer = (domain_of(x.link), x.price_inr, normalize_text(x.title))
        if (url and url in urls) or offer in offers:
            continue
        urls.add(url)
        offers.add(offer)
        out.append(x)
    return out


def kept(product_name: str, listings: list[Listing], store_domain: str | None = None) -> list[Listing]:
    return _dedupe([
        x for x in listings
        if x.price_inr and same_product(product_name, x.title, x.condition)
        # The store's own listing is the quote itself, not a comparison.
        and not is_own_url(x.link, None, store_domain)
    ])


def lens_is_enough(product_name: str | None, lens: LensResult | None, store_domain: str | None = None) -> bool:
    return bool(product_name) and len(kept(product_name, lens_listings(lens), store_domain)) >= rules.PRICE_MIN_SAMPLE


def _listing_data(x: Listing) -> dict:
    return {"title": x.title, "price": x.price_inr, "domain": domain_of(x.link), "source": x.source, "url": x.link}


def _quote_item(product_name: str, quoted_price: int | None, chosen: list[Listing], mid: float,
                summary: str, sources: list[dict], data: dict) -> Item:
    if not quoted_price:
        return Item("info", f"Median price of {len(chosen)} matching listings is Rs {round(mid)}", summary, sources, data)
    ratio = quoted_price / mid
    data.update(quoted=quoted_price, ratio=round(ratio, 2))
    detail = f"Quoted Rs {quoted_price}. {summary}"
    if ratio >= rules.PRICE_BAD_RATIO:
        return Item("bad", f"Quoted price is {ratio:.1f}x the median of {len(chosen)} matching listings", detail, sources, data)
    if ratio >= rules.PRICE_WARN_RATIO:
        return Item("warn", f"Quoted price is {ratio:.1f}x the median of {len(chosen)} matching listings", detail, sources, data)
    if ratio <= rules.PRICE_LOW_RATIO:
        if any(is_major_retailer(domain_of(x.link), x.source) or is_brand_site(domain_of(x.link), product_name)
               for x in chosen):
            return Item("warn", "Far below other listings; check if genuine", detail, sources, data)
        return Item("info", "Much cheaper than other listings; check what is included", detail, sources, data)
    return Item("good", f"Price is in line with {len(chosen)} listings", detail, sources, data)


def evaluate(product_name: str | None, quoted_price: int | None, lens: LensResult | None,
             shopping: ShoppingResult | None, store_domain: str | None = None,
             claimed_mrp: int | None = None) -> SignalResult:
    if not product_name:
        return skipped("Add the product name to compare prices")

    lens_all = lens_listings(lens)
    lens_kept = kept(product_name, lens_all, store_domain)
    if len(lens_kept) >= rules.PRICE_MIN_SAMPLE or shopping is None:
        engine, listings, chosen = "google_lens", lens_all, lens_kept
    else:
        engine, listings = "google_shopping", shopping_listings(shopping)
        chosen = kept(product_name, listings, store_domain)
    label = ENGINE_LABELS[engine]
    inr_count = sum(1 for x in listings if x.price_inr)
    own_count = sum(1 for x in listings if x.price_inr and is_own_url(x.link, None, store_domain))
    chosen.sort(key=lambda x: x.price_inr)
    cheapest = chosen[: rules.PRICE_SOURCES_SHOWN]
    sources = [source(f"Rs {x.price_inr} - {x.title}", x.link, x.engine) for x in cheapest]
    data = {
        "source": engine,
        "source_label": label,
        "listings_total": len(listings),
        "listings_inr": inr_count,
        "own_listings_dropped": own_count,
        "kept": len(chosen),
        "lens_kept": len(lens_kept),
        "cheapest": [_listing_data(x) for x in cheapest],
    }

    if len(chosen) < rules.PRICE_MIN_SAMPLE:
        detail = (f"{label}: {inr_count} listings had INR prices, {len(chosen)} matched \"{product_name}\". "
                  f"At least {rules.PRICE_MIN_SAMPLE} are needed before comparing prices.")
        return done(Item("info", "Not enough priced matches", detail, sources, data))

    prices = [x.price_inr for x in chosen]
    mid = median(prices)
    data.update(median=round(mid), lowest=prices[0])
    summary = (f"{label}: {len(chosen)} of {inr_count} INR listings matched \"{product_name}\"; "
               f"median Rs {round(mid)}, lowest Rs {prices[0]}.")
    items = [_quote_item(product_name, quoted_price, chosen, mid, summary, sources, data)]

    if claimed_mrp:
        mrp_ratio = claimed_mrp / mid
        data.update(claimed_mrp=claimed_mrp, mrp_ratio=round(mrp_ratio, 2))
        if mrp_ratio >= rules.PRICE_MRP_RATIO:
            items.append(Item(
                "warn",
                f"The original price shown (Rs {claimed_mrp}) is {mrp_ratio:.1f}x the median of {len(chosen)} listings. "
                "The discount may be overstated.",
                summary, [], {"claimed_mrp": claimed_mrp, "median": round(mid), "mrp_ratio": round(mrp_ratio, 2)},
            ))
    return done(*items)
