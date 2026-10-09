from app.signals import rules
from app.signals.result import Item, SignalResult, source


def counts_points(counts: dict[str, int]) -> tuple[int, int]:
    negative = sum(counts.get(o, 0) for o in rules.NEGATIVE_OUTCOMES)
    positive = sum(counts.get(o, 0) for o in rules.POSITIVE_OUTCOMES)
    return negative, positive


def evaluate(counts: dict[str, int], store_pages: list[tuple[str, str]]) -> SignalResult:
    """counts: reports by outcome over the check's stores; store_pages: (label, path) pairs."""
    links = [source(label, path, "community") for label, path in store_pages]
    total = sum(counts.values())
    negative, positive = counts_points(counts)
    data = {"counts": {o: counts.get(o, 0) for o in rules.OUTCOMES}, "negative": negative, "positive": positive}
    if not total:
        # No reports is not data; the verdict must not count it as a usable signal.
        return SignalResult("skipped", "No buyer reports yet",
                            [Item("info", "No buyer reports yet", "Bought from this store? Add what happened.", links, data)])
    detail = (f"{counts.get('delivered', 0)} delivered, {counts.get('not_delivered', 0)} not delivered, "
              f"{counts.get('differs', 0)} differs from photo, {counts.get('other', 0)} other.")
    return SignalResult("done", None, [Item("info", f"{total} buyer report{'s' if total > 1 else ''}", detail, links, data)])
