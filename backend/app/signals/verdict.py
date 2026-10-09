from app.signals import rules
from app.signals.result import SignalResult


def evaluate(results: dict[str, SignalResult], negative_reports: int, positive_reports: int) -> tuple[str, int]:
    items = [i for r in results.values() if r.status == "done" for i in r.items]
    bad = sum(1 for i in items if i.severity == "bad")
    warn = sum(1 for i in items if i.severity == "warn")
    good = min(sum(1 for i in items if i.severity == "good"), rules.GOOD_CAP)
    reports = rules.REPORT_NEGATIVE_WEIGHT * negative_reports - rules.REPORT_POSITIVE_WEIGHT * positive_reports
    points = (rules.POINTS_BAD * bad + rules.POINTS_WARN * warn + rules.POINTS_GOOD * good
              + max(min(reports, rules.COMMUNITY_CAP), 0))

    if sum(1 for r in results.values() if r.status == "done") < rules.MIN_USABLE_SIGNALS:
        return rules.VERDICT_NO_DATA, points
    if points >= rules.HIGH_RISK_POINTS:
        return rules.VERDICT_HIGH, points
    if points >= rules.CAREFUL_POINTS:
        return rules.VERDICT_CAREFUL, points
    return rules.VERDICT_CLEAR, points
