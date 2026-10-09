from app.serp.engines import SearchResult, SearchResults
from app.signals import complaints

TERMS = complaints.store_terms("red.store", None, None)


def results(*rows):
    return SearchResults(results=[SearchResult(title=t, link=f"https://f.in/{i}", snippet=s) for i, (t, s) in enumerate(rows)])


def test_store_terms_variants():
    t = complaints.store_terms("red_store.in", "red-store.co.in", "Red Store")
    assert t.exact == ["red_store.in", "red-store.co.in"] and t.loose == ["red store in", "red store"]
    one_word = complaints.store_terms("boat.nirvana", None, "boAt")
    assert one_word.loose == ["boat nirvana"]
    assert complaints.store_terms("redstore", None, "Red").loose == []


def test_exact_handle_and_domain_match():
    t = complaints.store_terms("red.store", "red-store.in", None)
    hit = lambda s: complaints.is_relevant(s.lower(), complaints.normalize_text(s), t)
    assert hit("Ordered from @red.store last week")
    assert hit("bought on www.red-store.in/products/1")
    assert not hit("ordered from red.storefront")
    assert not hit("ordered from xred.store")


def test_comp_5_boat_nirvana_product_threads_do_not_count():
    """Recorded google_forums fixture for "boat.nirvana": threads about boAt Nirvana earbuds."""
    import json
    from pathlib import Path

    from app.serp.engines import _results
    path = Path(__file__).parent / "fixtures/serp/a8419354533a393991d430459cc29a6787a2d38155a54bf24dadbbb132268f85.json"
    forums = _results(json.loads(path.read_text()))
    assert len(forums.results) == 10
    r = complaints.evaluate(None, forums, complaints.store_terms("boat.nirvana", None, "boAt"))
    counted = [x["title"] for x in r.items[0].data["results"]]
    # The rule as specified still counts one thread: a consumer-complaint form whose
    # "Seller Name" / "Website Name" fields hit the context words. Reported to the owner.
    assert counted == ["Wrong product recived"]
    assert r.items[0].severity == "info"


def test_comp_1_two_not_delivered_is_bad():
    r = complaints.evaluate(results(("red.store order", "my order was not delivered"),
                                    ("Red Store review", "parcel not delivered after 3 weeks")), None, TERMS)
    it = r.items[0]
    assert it.severity == "bad" and it.data["negatives"] == 2 and len(it.sources) == 2


def test_comp_2_unrelated_scam_not_counted():
    r = complaints.evaluate(results(("Big scam alert", "a scam by another shop")), None, TERMS)
    assert r.items[0].finding == "No public discussion found" and r.items[0].data["relevant"] == 0


def test_comp_3_nothing_is_info_not_good():
    r = complaints.evaluate(results(), results(), TERMS)
    assert r.status == "done" and r.items[0].severity == "info"


def test_comp_4_positive_is_good():
    r = complaints.evaluate(None, results(("red.store", "received my order"), ("red store", "genuine product"),
                                          ("red store haul", "received, original box")), TERMS)
    assert r.items[0].severity == "good" and r.items[0].data["positives"] == 3


def test_one_negative_is_warn_and_dedupe_by_url():
    g = SearchResults(results=[SearchResult("red.store fake", "https://f.in/1/", "fake item")])
    f = SearchResults(results=[SearchResult("red.store fake", "https://f.in/1", "fake item")])
    r = complaints.evaluate(g, f, TERMS)
    assert r.items[0].severity == "warn" and r.items[0].data["searched"] == 1
