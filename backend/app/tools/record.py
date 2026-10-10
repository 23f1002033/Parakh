import argparse
import asyncio
import sys
import uuid
from pathlib import Path
from urllib.parse import urlparse

from sqlalchemy import func, select

from app.config import Settings, get_settings
from app.db import init_db, make_engine, make_session_factory
from app.models import ApiCall
from app.normalize import instagram_handle, website_domain
from app.serp import engines
from app.serp.client import SerpClient
from app.serp.images import ImageRef


def parse_args(argv):
    p = argparse.ArgumentParser(prog="python -m app.tools.record")
    p.add_argument("--instagram")
    p.add_argument("--website")
    p.add_argument("--image", help="local file path or http(s) URL")
    p.add_argument("--product", help="product name; used for Google Shopping, not sent to Lens")
    p.add_argument("--maps", help="Google Maps query, for example 'Store name Jaipur'")
    p.add_argument("--mode", choices=["record", "replay"], default="record")
    args = p.parse_args(argv)
    if not (args.instagram or args.website or args.image or args.product or args.maps):
        p.error("give at least one of --instagram, --website, --image, --product, --maps")
    return args


async def _try(lines, label, coro, fmt):
    try:
        lines.append(f"{label}: {fmt(await coro)}")
    except Exception as e:
        lines.append(f"{label}: unavailable ({type(e).__name__}: {e})")


def _lens_all(r):
    priced = [m for m in r.matches if m.price_inr]
    exact = sum(m.exact_match for m in r.matches)
    return f"{len(r.matches)} visual matches, {len(priced)} priced in INR, {exact} flagged exact"


def _lens_exact(r):
    domains = {urlparse(m.link).hostname for m in r.matches if m.link}
    return f"{len(r.matches)} exact matches on {len(domains)} domains"


def _profile(p):
    dates = sorted(d for d in (post.posted_on for post in p.posts) if d)
    span = f", dated {dates[0]} to {dates[-1]}" if dates else ""
    return (f"followers={p.followers} following={p.following} private={p.is_private} "
            f"verified={p.is_verified} posts visible={len(p.posts)}{span}")


def _results(r):
    return f"{len(r.results)} results"


def _shopping(r):
    return f"{len(r.items)} results, {sum(1 for i in r.items if i.price_inr)} priced in INR"


def _maps(r):
    first = r.places[0] if r.places else None
    head = f"{len(r.places)} places"
    if first:
        head += f"; first: {first.title!r} rating={first.rating} reviews={first.reviews}"
    return head + f"; raw fields: {', '.join(r.raw_fields)}"


async def run(args, settings: Settings) -> str:
    settings = settings.model_copy(update={"serpapi_mode": args.mode})
    db = make_engine(settings.database_url)
    init_db(db)
    sessions = make_session_factory(db)
    client = SerpClient(settings, sessions)
    run_id = "record-" + uuid.uuid4().hex[:12]

    handle = instagram_handle(args.instagram) if args.instagram else None
    domain = website_domain(args.website) if args.website else None
    store_key = handle or domain
    url = image = None
    if args.image:
        if args.image.startswith(("http://", "https://")):
            url = args.image
        else:
            image = ImageRef.from_bytes(Path(args.image).read_bytes())

    lines = []
    try:
        if url or image:
            await _try(lines, "lens_all", engines.lens_all(client, url=url, image=image, check_id=run_id), _lens_all)
            await _try(lines, "lens_exact", engines.lens_exact(client, url=url, image=image, check_id=run_id), _lens_exact)
        if args.product:
            await _try(lines, "google_shopping", engines.google_shopping(client, args.product, run_id), _shopping)
        if handle:
            await _try(lines, "instagram_profile", engines.instagram_profile(client, handle, run_id), _profile)
        if store_key:
            await _try(lines, "google complaints", engines.google_search(client, engines.complaints_query(handle, domain), run_id), _results)
            await _try(lines, "google_forums", engines.google_forums(client, engines.forums_query(handle, domain), run_id), _results)
        if domain:
            await _try(lines, "google footprint", engines.website_footprint(client, domain, run_id), _results)
        if args.maps:
            await _try(lines, "google_maps", engines.google_maps(client, args.maps, run_id), _maps)
    finally:
        await client.aclose()

    with sessions() as s:
        calls = s.execute(
            select(ApiCall.cache_hit, func.count()).where(ApiCall.check_id == run_id).group_by(ApiCall.cache_hit)
        ).all()
    counts = {hit: n for hit, n in calls}
    lines.append("--")
    lines.append(f"# mode={args.mode} live calls={counts.get(False, 0)} cached/replayed={counts.get(True, 0)}")
    if image:
        lines.append(f"# image sha256={image.sha256} jpeg bytes={len(image.jpeg)}")
    return "\n".join(lines)


def main(argv=None) -> None:
    args = parse_args(argv if argv is not None else sys.argv[1:])
    print(asyncio.run(run(args, get_settings())))


if __name__ == "__main__":
    main()
