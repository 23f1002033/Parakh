import re
from dataclasses import dataclass, field

from app.normalize import normalize_text
from app.serp.engines import SearchResults
from app.signals import rules
from app.signals.result import Item, SignalResult, done, is_own_url, source


@dataclass
class StoreTerms:
    exact: list[str] = field(default_factory=list)
    loose: list[str] = field(default_factory=list)


def store_terms(handle: str | None, domain: str | None, full_name: str | None) -> StoreTerms:
    exact = [t for t in (handle, domain) if t]
    # Loose names like "boat nirvana" are also product names, so they need 2+ words
    # and a store-context word in the same result to count.
    loose = [normalize_text(t) for t in (handle and handle.replace(".", " ").replace("_", " "), full_name) if t]
    loose = [t for t in dict.fromkeys(loose) if len(t.split()) >= rules.LOOSE_NAME_MIN_WORDS]
    return StoreTerms(exact=exact, loose=loose)


def _has(text: str, phrase: str) -> bool:
    return re.search(rf"\b{re.escape(phrase)}\b", text) is not None


def _has_exact(raw: str, term: str) -> bool:
    return re.search(rf"(?<![\w-])@?{re.escape(term)}(?![\w-]|\.\w)", raw) is not None


def is_relevant(raw: str, text: str, terms: StoreTerms) -> bool:
    if any(_has_exact(raw, t) for t in terms.exact):
        return True
    return any(_has(text, t) for t in terms.loose) and any(_has(text, w) for w in rules.STORE_CONTEXT_WORDS)


def _url_key(url: str | None) -> str:
    return (url or "").split("#")[0].rstrip("/").lower()


def evaluate(google: SearchResults | None, forums: SearchResults | None, terms: StoreTerms,
             handle: str | None = None, store_domain: str | None = None) -> SignalResult:
    merged, seen, own = [], set(), []
    for engine, res in (("google", google), ("google_forums", forums)):
        for r in (res.results if res else []):
            key = _url_key(r.link)
            if not key or key in seen:
                continue
            seen.add(key)
            # The store's own pages say what the store wants; they are not public discussion.
            if is_own_url(r.link, handle, store_domain):
                own.append({"engine": engine, "title": r.title, "url": r.link})
                continue
            merged.append((engine, r))

    relevant = []
    for engine, r in merged:
        raw = f"{r.title or ''} {r.snippet or ''}".lower()
        text = normalize_text(raw)
        if not is_relevant(raw, text, terms):
            continue
        neg = [t for t in rules.NEGATIVE_TERMS if _has(text, t)]
        pos = [t for t in rules.POSITIVE_TERMS if _has(text, t)] if not neg else []
        relevant.append({"engine": engine, "title": r.title, "url": r.link, "snippet": r.snippet,
                         "date": r.date, "source": r.source, "negative": neg, "positive": pos})

    relevant.sort(key=lambda x: (not x["negative"], not x["positive"]))
    negatives = sum(1 for x in relevant if x["negative"])
    positives = sum(1 for x in relevant if x["positive"])
    data = {"searched": len(merged), "own_dropped": own, "relevant": len(relevant), "negatives": negatives,
            "positives": positives, "terms": {"exact": terms.exact, "loose": terms.loose}, "results": relevant}
    sources = [source(x["title"], x["url"], x["engine"]) for x in relevant]

    if not relevant:
        return done(Item("info", "No public discussion found",
                         f"{len(merged)} search results checked; none mention this store by name.", [], data))
    if negatives >= rules.COMPLAINTS_BAD:
        return done(Item("bad", f"{negatives} public posts mention problems with this store", None, sources, data))
    if negatives >= rules.COMPLAINTS_WARN:
        return done(Item("warn", "1 public post mentions a problem with this store", None, sources, data))
    if positives >= rules.COMPLAINTS_GOOD:
        return done(Item("good", f"{positives} public posts mention good experiences", None, sources, data))
    n = len(relevant)
    verb = "mention" if n > 1 else "mentions"
    return done(Item("info", f"{n} public post{'s' if n > 1 else ''} {verb} this store, none with complaints",
                     None, sources, data))
