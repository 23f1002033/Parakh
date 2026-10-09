from app.serp.engines import LensMatch, LensResult, ShoppingItem, ShoppingResult
from app.signals import price

NAME = "boAt Rockerz 110"


def lens(*rows):
    return LensResult(matches=[
        LensMatch(title=t, link=link, source="S", price_inr=p, condition=c)
        for t, p, link, c in [(r + (None, None))[:4] if len(r) < 4 else r for r in rows]
    ])


def same(prices, link="https://shop.example.in/x"):
    return lens(*[(f"boAt Rockerz 110 Neckband {i}", p, f"{link}/{i}") for i, p in enumerate(prices)])


def item(result):
    assert result.status == "done"
    assert len(result.items) == 1
    return result.items[0]


def test_price_1_bad_markup():
    it = item(price.evaluate(NAME, 2000, same([400, 450, 500, 550, 600]), None))
    assert it.severity == "bad"
    assert it.data["ratio"] == 4.0 and it.data["median"] == 500 and it.data["kept"] == 5
    assert "4.0x" in it.finding


def test_price_2_warn():
    assert item(price.evaluate(NAME, 1000, same([400, 500, 600]), None)).severity == "warn"


def test_price_3_good():
    it = item(price.evaluate(NAME, 550, same([400, 500, 600]), None))
    assert it.severity == "good" and it.finding == "Price is in line with 3 listings"
    assert it.data["source_label"] == "Google Lens"


def test_price_4_not_enough():
    it = item(price.evaluate(NAME, 550, same([400, 500]), None))
    assert it.severity == "info" and it.finding == "Not enough priced matches"
    assert "ratio" not in it.data and "median" not in it.data


def test_price_5_containment_and_model_number():
    data = lens(("boAt Rockerz 255 Pro", 900), ("Rockerz neckband", 800), ("BoAt Rockerz 110 Wireless Neckband", 699))
    kept = price.kept(NAME, price.lens_listings(data))
    assert [x.title for x in kept] == ["BoAt Rockerz 110 Wireless Neckband"]


def test_price_6_far_below_with_brand_listing():
    data = lens(*[(f"boAt Rockerz 110 v{i}", p, f"https://www.boat-lifestyle.com/p/{i}") for i, p in enumerate([1800, 2000, 2200])])
    it = item(price.evaluate(NAME, 150, data, None))
    assert it.severity == "warn" and it.finding.startswith("Far below other listings")


def test_price_9_far_below_without_brand_is_info_not_good():
    it = item(price.evaluate(NAME, 150, same([1800, 2000, 2200]), None))
    assert it.severity == "info" and it.finding == "Much cheaper than other listings; check what is included"


def test_price_7_no_product_name():
    r = price.evaluate(None, 699, same([400, 500, 600]), None)
    assert r.status == "skipped"
    assert r.items[0].finding.startswith("Add the product name") and r.items[0].data is None


def test_price_8_refurbished_dropped():
    data = lens(("boAt Rockerz 110", 300, "https://a.in/1", "Refurbished"), ("boAt Rockerz 110", 500, "https://a.in/2", "New"),
                ("boAt Rockerz 110", 600, "https://a.in/3", None))
    assert len(price.kept(NAME, price.lens_listings(data))) == 2


def test_usd_listings_ignored():
    data = lens(("boAt Rockerz 110", None), ("boAt Rockerz 110", None), ("boAt Rockerz 110", None))
    assert item(price.evaluate(NAME, 699, data, None)).finding == "Not enough priced matches"


def test_shopping_fallback_names_its_source():
    shop = ShoppingResult(items=[ShoppingItem(f"boAt Rockerz 110 {i}", f"https://g/{i}", "Flipkart", p)
                                 for i, p in enumerate([650, 699, 799])])
    assert not price.lens_is_enough(NAME, same([500]))
    it = item(price.evaluate(NAME, 699, same([500]), shop))
    assert it.data["source"] == "google_shopping" and "Google Shopping" in it.detail
    assert it.data["median"] == 699 and it.data["ratio"] == 1.0 and it.data["lens_kept"] == 1
    assert [s["engine"] for s in it.sources] == ["google_shopping"] * 3


def test_lens_used_when_enough_even_if_shopping_given():
    shop = ShoppingResult(items=[ShoppingItem("boAt Rockerz 110", "https://g/1", "X", 5000)] * 3)
    assert price.lens_is_enough(NAME, same([400, 500, 600]))
    assert item(price.evaluate(NAME, 550, same([400, 500, 600]), shop)).data["source"] == "google_lens"


def test_kept_listings_deduped_by_url_then_offer():
    data = lens(("boAt Rockerz 110 A", 699, "https://www.flipkart.com/p/1"),
                ("boAt Rockerz 110 B", 650, "https://www.flipkart.com/p/1/"),
                ("boAt Rockerz 110 A", 699, "https://www.flipkart.com/or/p/1?pid=2"),
                ("boAt Rockerz 110 A", 749, "https://www.flipkart.com/p/3"),
                ("boAt Rockerz 110 A", 699, "https://www.amazon.in/p/1"))
    kept = price.kept(NAME, price.lens_listings(data))
    assert [(x.link, x.price_inr) for x in kept] == [
        ("https://www.flipkart.com/p/1", 699), ("https://www.flipkart.com/p/3", 749), ("https://www.amazon.in/p/1", 699)]


def test_five_cheapest_sources():
    it = item(price.evaluate(NAME, 550, same([900, 100, 800, 200, 700, 300, 600]), None))
    assert [c["price"] for c in it.data["cheapest"]] == [100, 200, 300, 600, 700]
    assert len(it.sources) == 5
