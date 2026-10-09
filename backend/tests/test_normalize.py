from datetime import date

from app.normalize import instagram_handle, jaccard, normalize_text, parse_caption_date, parse_currency, website_domain


def test_norm_1_instagram_handle():
    for raw in ["@Some.Store", "instagram.com/some.store/?hl=en", "SOME.STORE",
                "https://www.instagram.com/Some.Store/"]:
        assert instagram_handle(raw) == "some.store"


def test_norm_2_website_domain():
    assert website_domain("https://www.Shop.in/products/x?ref=1") == "shop.in"
    assert website_domain("shop.in/") == "shop.in"


def test_norm_3_inr_price():
    assert parse_currency({"value": "Rs 1,299.00", "extracted_value": 1299}) == 1299
    assert parse_currency({"value": "\u20b91,299", "extracted_value": 1299, "currency": "\u20b9"}) == 1299
    assert parse_currency({"value": "INR 499", "currency": "INR"}) == 499


def test_norm_4_usd_dropped():
    assert parse_currency({"value": "$12.99", "extracted_value": 12.99, "currency": "$"}) is None
    assert parse_currency({"value": "USD 12.99", "extracted_value": 12.99}) is None
    assert parse_currency(None) is None


def test_norm_5_caption_date():
    caption = "Photo by X on September 05, 2026. May be an image of text."
    assert parse_caption_date(caption) == date(2026, 9, 5)
    assert parse_caption_date("Photo by X. May be an image.") is None


def test_text_and_jaccard():
    assert normalize_text("  Nike Air-Max 90!! ") == "nike air max 90"
    assert jaccard("Nike Air Max 90", "nike air max 90 white") == 0.8
    assert jaccard("", "x") == 0.0
