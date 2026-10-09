from datetime import date

from app.serp.engines import InstagramProfile
from app.signals import rules
from app.signals.result import Item, SignalResult, domain_of, done, source


def indian_number(n: int) -> str:
    # Lakh/crore grouping, as Indian buyers read it: 1036292 -> 10,36,292.
    s = str(abs(n))
    head, tail = s[:-3], s[-3:]
    groups = []
    while len(head) > 2:
        groups.insert(0, head[-2:])
        head = head[:-2]
    if head:
        groups.insert(0, head)
    return ("-" if n < 0 else "") + ",".join(groups + [tail])


def evaluate(p: InstagramProfile, website: str | None, today: date) -> SignalResult:
    link = [source(f"@{p.handle} on Instagram", p.url, "instagram_profile")]
    dates = sorted(d for d in (post.posted_on for post in p.posts) if d)
    oldest = dates[0] if dates else None
    bio_domains = sorted({d for d in (domain_of(u) for u in [p.external_url, *p.bio_links]) if d})
    items = []

    if p.is_private:
        items.append(Item("warn", "Account is private", "Posts and history cannot be seen.", link))
    if oldest and (today - oldest).days < rules.NEW_ACCOUNT_DAYS and len(p.posts) < rules.NEW_ACCOUNT_POSTS:
        items.append(Item("warn", "Very new activity",
                          f"Oldest visible post is from {oldest.isoformat()} ({(today - oldest).days} days ago) "
                          f"and only {len(p.posts)} posts are visible.", link))
    if website and bio_domains and website not in bio_domains:
        items.append(Item("warn", "Bio link points to a different website",
                          f"You gave {website}; the profile links to {', '.join(bio_domains)}.", link))
    if p.followers is not None and p.followers >= rules.LARGE_FOLLOWING and len(p.posts) < rules.FEW_POSTS:
        items.append(Item("info", "Large following, few posts",
                          f"{indian_number(p.followers)} followers but {len(p.posts)} visible posts.", link))
    if p.is_verified:
        items.append(Item("good", "Account is verified by Instagram", None, link))

    numbers = {
        "followers": p.followers, "following": p.following, "visible_posts": len(p.posts),
        "oldest_visible_post": oldest.isoformat() if oldest else None,
        "newest_visible_post": dates[-1].isoformat() if dates else None,
        "is_private": p.is_private, "is_verified": p.is_verified, "is_professional": p.is_professional,
        "full_name": p.full_name, "bio_domains": bio_domains,
    }
    span = f", posts dated {oldest.isoformat()} to {dates[-1].isoformat()}" if dates else ""
    followers = indian_number(p.followers) if p.followers is not None else "unknown"
    following = indian_number(p.following) if p.following is not None else "unknown"
    summary = (f"{followers} followers, {following} following, "
               f"{len(p.posts)} recent posts visible{span}")
    items.append(Item("info", summary, "Only recent posts are visible; older history cannot be seen.",
                      link, numbers))
    return done(*items)
