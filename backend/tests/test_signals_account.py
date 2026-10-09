from datetime import date, timedelta

from app.serp.engines import InstagramPost, InstagramProfile
from app.signals import account

TODAY = date(2026, 10, 9)


def profile(**kw):
    return InstagramProfile(handle="x.store", url="https://www.instagram.com/x.store/", **kw)


def posts(n, oldest_days):
    return [InstagramPost(f"p{i}", None, None, TODAY - timedelta(days=oldest_days - i)) for i in range(n)]


def findings(r, severity):
    return [i.finding for i in r.items if i.severity == severity]


def test_acc_1_private():
    assert findings(account.evaluate(profile(is_private=True), None, TODAY), "warn") == ["Account is private"]


def test_acc_2_very_new():
    r = account.evaluate(profile(posts=posts(5, 20)), None, TODAY)
    assert findings(r, "warn") == ["Very new activity"]


def test_acc_2b_old_enough():
    assert findings(account.evaluate(profile(posts=posts(5, 90)), None, TODAY), "warn") == []


def test_acc_3_bio_link_differs():
    r = account.evaluate(profile(external_url="https://www.other.in/x", bio_links=["https://other.in/y"]), "shop.in", TODAY)
    assert findings(r, "warn") == ["Bio link points to a different website"]
    same = account.evaluate(profile(bio_links=["https://www.shop.in/"]), "shop.in", TODAY)
    assert findings(same, "warn") == []


def test_acc_4_verified():
    assert findings(account.evaluate(profile(is_verified=True), None, TODAY), "good") == ["Account is verified by Instagram"]


def test_acc_5_missing_posts_info_only():
    r = account.evaluate(profile(), None, TODAY)
    assert [i.severity for i in r.items] == ["info"]
    assert r.items[0].sources[0]["url"] == "https://www.instagram.com/x.store/"
    assert r.items[0].detail.startswith("Only recent posts are visible")


def test_large_following_few_posts():
    r = account.evaluate(profile(followers=50_000, posts=posts(3, 400)), None, TODAY)
    assert "Large following, few posts" in findings(r, "info")
    assert any(i.finding.startswith("50,000 followers") for i in r.items)
