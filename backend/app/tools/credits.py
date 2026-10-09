import argparse
import asyncio
from pathlib import Path

import httpx

from app.config import get_settings
from app.serp import images

ACCOUNT_URL = "https://serpapi.com/account.json"
# Only these fields are printed; the account response also contains the key.
FIELDS = ("plan_searches_left", "extra_credits", "total_searches_left", "this_month_usage", "this_hour_searches")


async def account(http: httpx.AsyncClient, api_key: str) -> dict:
    resp = await http.get(ACCOUNT_URL, params={"api_key": api_key})
    body = resp.json()
    return {k: body.get(k) for k in FIELDS}


async def main(image_path: str | None, wait: float) -> None:
    api_key = get_settings().api_key()
    if not api_key:
        raise SystemExit("SERPAPI_KEY is not set")
    async with httpx.AsyncClient(timeout=30) as http:
        print("before:", await account(http, api_key))
        if not image_path:
            return
        jpeg, sha = images.to_jpeg(Path(image_path).read_bytes())
        body = await images.upload(http, api_key, jpeg)
        print(f"upload: jpeg bytes={len(jpeg)} image_id present={bool(body.get('image_id'))} error={body.get('error')}")
        print("upload response keys:", sorted(k for k in body if k != "api_key"))
        await asyncio.sleep(wait)
        print("after: ", await account(http, api_key))


if __name__ == "__main__":
    p = argparse.ArgumentParser(prog="python -m app.tools.credits")
    p.add_argument("--upload", help="image file to upload once through the Image API")
    p.add_argument("--wait", type=float, default=15, help="seconds to wait before reading the account again")
    a = p.parse_args()
    asyncio.run(main(a.upload, a.wait))
