from app.serp.engines import LensMatch, LensResult
from app.signals import photo


def exact(*links):
    return LensResult(matches=[LensMatch(title="t", link=link, source="s", exact_match=True) for link in links])


def test_photo_1_marketplace():
    r = photo.evaluate(exact("https://www.aliexpress.com/item/1", "https://blog.in/a"), "x.store", None, "Red shirt")
    assert r.items[0].severity == "warn" and r.items[0].finding == "Same photo appears on aliexpress"


def test_photo_2_no_matches_is_never_good():
    r = photo.evaluate(exact(), "x.store", "x.in", "Red shirt")
    assert r.status == "done"
    assert r.items[0].severity == "info" and r.items[0].finding.startswith("No exact copies found")


def test_photo_2b_only_own_store_is_not_good():
    r = photo.evaluate(exact("https://www.x.in/p/1", "https://instagram.com/x.store/p/2"), "x.store", "x.in", None)
    assert r.items[0].severity == "info" and r.items[0].finding.startswith("No exact copies found")


def test_photo_3_many_sites():
    r = photo.evaluate(exact("https://a.in/1", "https://b.com/2", "https://c.org/3", "https://d.net/4"), None, None, None)
    assert r.items[0].severity == "info" and r.items[0].finding == "Photo is used on 4 other sites"
    assert r.items[0].data["matches"] == 4


def test_photo_brand_own_image():
    r = photo.evaluate(exact("https://www.boat-lifestyle.com/p", "https://www.amazon.in/dp/1"), None, None, "boAt Rockerz 110")
    assert r.items[0].finding == "Photo is the brand's own product image"
