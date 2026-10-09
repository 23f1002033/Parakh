from app.signals import community, rules, verdict
from app.signals.result import Item, SignalResult, done


def sig(*severities):
    return done(*[Item(s, s) for s in severities])


def skip():
    return SignalResult("skipped", "x", [Item("info", "x")])


def test_verd_1_one_signal():
    assert verdict.evaluate({"price": sig("bad"), "photo": skip(), "account": skip()}, 0, 0)[0] == "Not enough data"


def test_verd_2_high_risk():
    assert verdict.evaluate({"price": sig("bad"), "account": sig("warn", "warn", "info")}, 0, 0) == ("High risk", 5)


def test_verd_3_careful():
    assert verdict.evaluate({"price": sig("warn"), "account": sig("warn")}, 0, 0) == ("Be careful", 2)


def test_verd_4_clear():
    assert verdict.evaluate({"price": sig("good"), "complaints": sig("good"), "account": sig("good", "warn")}, 0, 0)[0] == "No red flags found"


def test_verd_5_reports_capped():
    results = {"price": sig("good"), "complaints": sig("good"), "account": sig("good"), "photo": sig("good")}
    label, points = verdict.evaluate(results, 10, 0)
    assert points == -rules.GOOD_CAP + rules.COMMUNITY_CAP == 3
    assert label in ("Be careful", "High risk")


def test_reports_floored_at_zero():
    assert verdict.evaluate({"price": sig("info"), "account": sig("info")}, 0, 5) == ("No red flags found", 0)


def test_unavailable_items_do_not_score():
    bad = SignalResult("unavailable", "x", [Item("bad", "x")])
    assert verdict.evaluate({"price": bad, "a": sig("info"), "b": sig("info")}, 0, 0)[1] == 0


def test_community_counts():
    r = community.evaluate({"not_delivered": 2, "delivered": 1}, [("Store page", "/s/instagram/x")])
    assert r.status == "done" and r.items[0].data["negative"] == 2 and r.items[0].severity == "info"
    assert community.evaluate({}, []).status == "skipped"
