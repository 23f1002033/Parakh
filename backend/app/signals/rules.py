SIGNALS = ("price", "photo", "complaints", "account", "community")

# Price (design 6.1)
PRICE_MIN_SAMPLE = 3
PRICE_CONTAINMENT = 0.6
PRICE_BAD_RATIO = 3.0
PRICE_WARN_RATIO = 1.8
PRICE_LOW_RATIO = 0.4
# A store's "original price" this far above the median makes the discount look bigger than it is.
PRICE_MRP_RATIO = 2.0
PRICE_SOURCES_SHOWN = 5
ALLOWED_CONDITIONS = ("", "new")

# Photo (design 6.2)
PHOTO_MANY_SITES = 3
MARKETPLACES = ("aliexpress", "alibaba", "temu", "dhgate", "meesho", "indiamart", "shein")
MAJOR_RETAILERS = (
    "amazon", "flipkart", "myntra", "ajio", "tatacliq", "croma", "reliancedigital",
    "nykaa", "jiomart", "vijaysales", "snapdeal",
)

# Complaints (design 6.3)
NEGATIVE_TERMS = ("scam", "fraud", "fake", "not delivered", "never received", "no refund",
                  "blocked me", "cheated", "duplicate")
POSITIVE_TERMS = ("received", "genuine", "legit", "delivered on time", "original")
STORE_CONTEXT_WORDS = ("order", "ordered", "seller", "delivery", "delivered", "refund", "instagram", "insta",
                       "page", "shop", "store", "website", "cod")
LOOSE_NAME_MIN_WORDS = 2
COMPLAINTS_BAD = 2
COMPLAINTS_WARN = 1
COMPLAINTS_GOOD = 2

# Account (design 6.4)
NEW_ACCOUNT_DAYS = 60
NEW_ACCOUNT_POSTS = 12
LARGE_FOLLOWING = 10_000
FEW_POSTS = 6

# Community (design 6.5)
NEGATIVE_OUTCOMES = ("not_delivered", "differs")
POSITIVE_OUTCOMES = ("delivered",)
OUTCOMES = ("delivered", "not_delivered", "differs", "other")

# Verdict (design 6.6)
POINTS_BAD = 3
POINTS_WARN = 1
POINTS_GOOD = -1
GOOD_CAP = 3
REPORT_NEGATIVE_WEIGHT = 2
REPORT_POSITIVE_WEIGHT = 1
COMMUNITY_CAP = 6
MIN_USABLE_SIGNALS = 2
HIGH_RISK_POINTS = 5
CAREFUL_POINTS = 2
VERDICT_HIGH = "High risk"
VERDICT_CAREFUL = "Be careful"
VERDICT_CLEAR = "No red flags found"
VERDICT_NO_DATA = "Not enough data"


def rules_as_data() -> dict:
    return {
        "price": {
            "min_sample": PRICE_MIN_SAMPLE,
            "containment": PRICE_CONTAINMENT,
            "model_numbers_must_match": True,
            "allowed_conditions": ["new", "(empty)"],
            "bad_ratio": PRICE_BAD_RATIO,
            "warn_ratio": PRICE_WARN_RATIO,
            "low_ratio": PRICE_LOW_RATIO,
            "mrp_ratio": PRICE_MRP_RATIO,
            "sources": ["Google Lens", "Google Shopping (when Lens has fewer than 3 matching listings)"],
            "major_retailers": list(MAJOR_RETAILERS),
        },
        "photo": {"marketplaces": list(MARKETPLACES), "many_sites": PHOTO_MANY_SITES, "ever_good": False},
        "complaints": {
            "negative_terms": list(NEGATIVE_TERMS),
            "positive_terms": list(POSITIVE_TERMS),
            "relevance": "exact handle (with or without @) or website domain; the spaced handle or Instagram "
                         "name only when it has 2+ words and the result has a store-context word",
            "store_context_words": list(STORE_CONTEXT_WORDS),
            "bad_at_negatives": COMPLAINTS_BAD,
            "warn_at_negatives": COMPLAINTS_WARN,
            "good_at_positives": COMPLAINTS_GOOD,
        },
        "account": {
            "new_account_days": NEW_ACCOUNT_DAYS,
            "new_account_posts": NEW_ACCOUNT_POSTS,
            "large_following": LARGE_FOLLOWING,
            "few_posts": FEW_POSTS,
        },
        "community": {
            "negative_outcomes": list(NEGATIVE_OUTCOMES),
            "positive_outcomes": list(POSITIVE_OUTCOMES),
            "cap": COMMUNITY_CAP,
        },
        "verdict": {
            "points": {"bad": POINTS_BAD, "warn": POINTS_WARN, "good": POINTS_GOOD, "good_cap": GOOD_CAP},
            "reports": {
                "formula": "min(2 x negative - positive, 6), floored at 0",
                "negative_weight": REPORT_NEGATIVE_WEIGHT,
                "positive_weight": REPORT_POSITIVE_WEIGHT,
                "cap": COMMUNITY_CAP,
            },
            "min_usable_signals": MIN_USABLE_SIGNALS,
            "levels": [
                {"verdict": VERDICT_NO_DATA, "when": f"fewer than {MIN_USABLE_SIGNALS} signals returned data"},
                {"verdict": VERDICT_HIGH, "min_points": HIGH_RISK_POINTS},
                {"verdict": VERDICT_CAREFUL, "min_points": CAREFUL_POINTS},
                {"verdict": VERDICT_CLEAR, "min_points": None},
            ],
        },
    }
