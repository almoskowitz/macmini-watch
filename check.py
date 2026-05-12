#!/usr/bin/env python3
"""
Polls Apple's Certified Refurbished store for M4 Mac mini and Mac Studio listings.
Filters by MEMORY_SIZES (comma-separated, e.g. "64GB,96GB,128GB") and optionally PRICE_CAP.
On a new hit, posts to Slack via webhook. Dedupes via state.json.
"""

import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

MEMORY_SIZES = [s.strip() for s in os.environ.get("MEMORY_SIZES", "").split(",") if s.strip()]
PRICE_CAP = int(os.environ.get("PRICE_CAP", "0")) or None
STATE_PATH = Path("state.json")
SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL", "").strip()
# Optional: Slack user ID(s) to @-mention on hits. Comma-separated for multiple.
SLACK_MENTION_USER_IDS = os.environ.get("SLACK_MENTION_USER_IDS", "").strip()

PRODUCTS = [
    ("Mac mini",   "https://www.apple.com/shop/refurbished/mac/mac-mini"),
    ("Mac Studio", "https://www.apple.com/shop/refurbished/mac/mac-studio"),
]

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) "
    "Version/17.0 Safari/605.1.15"
)
HEADERS = {
    "User-Agent": UA,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode("utf-8", errors="ignore")
            print(f"[fetch] {url} -> {resp.status} ({len(body)} bytes)", file=sys.stderr)
            return body
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as e:
        print(f"[fetch] {url} -> {e}", file=sys.stderr)
        return ""


def check_apple_refurb(product: str, url: str) -> list[dict]:
    html = fetch(url)
    if not html:
        return []

    m = re.search(r"window\.REFURB_GRID_BOOTSTRAP\s*=\s*", html)
    if not m:
        print(f"[apple] '{product}': REFURB_GRID_BOOTSTRAP not found in page", file=sys.stderr)
        return []
    try:
        data, _ = json.JSONDecoder().raw_decode(html, m.end())
    except json.JSONDecodeError as e:
        print(f"[apple] '{product}': JSON parse error: {e}", file=sys.stderr)
        return []

    tiles = data.get("tiles", [])
    # tsMemorySize values are lowercase without spaces, e.g. "128gb"
    memory_filter = {s.lower().replace(" ", "") for s in MEMORY_SIZES}
    matching = sum(1 for t in tiles if product in t.get("title", "") and re.search(r"\bM4\b", t.get("title", "")))
    print(f"[apple] '{product}': {len(tiles)} tiles on page, {matching} matching M4 {product}", file=sys.stderr)

    hits = []
    seen = set()
    for tile in tiles:
        title = tile.get("title", "")
        if not title.startswith("Refurbished"):
            continue
        if product not in title:
            continue
        if not re.search(r"\bM4\b", title):
            continue

        try:
            price = int(float(tile["price"]["currentPrice"]["raw_amount"]))
        except (KeyError, TypeError, ValueError):
            continue

        key = (title, price)
        if key in seen:
            continue
        seen.add(key)

        if memory_filter:
            ts_mem = tile.get("filters", {}).get("dimensions", {}).get("tsMemorySize", "").lower()
            if ts_mem not in memory_filter:
                continue
        if PRICE_CAP and price > PRICE_CAP:
            continue

        product_url = tile.get("productDetailsUrl") or url
        if product_url.startswith("/"):
            product_url = "https://www.apple.com" + product_url

        hits.append(
            {
                "retailer": f"Apple Refurb {product}",
                "variant": title[:140],
                "price": price,
                "url": product_url,
            }
        )
    return hits


def signature(hit: dict) -> str:
    return f"{hit['retailer']}|{hit['variant']}|{hit['price']}"


def post_slack(hit: dict) -> None:
    if not SLACK_WEBHOOK_URL:
        print(f"[slack] (dry-run) would post: {hit}", file=sys.stderr)
        return
    mentions = ""
    if SLACK_MENTION_USER_IDS:
        ids = [u.strip() for u in SLACK_MENTION_USER_IDS.split(",") if u.strip()]
        mentions = " ".join(f"<@{u}>" for u in ids)
        if mentions:
            mentions += " "
    filter_desc = "/".join(MEMORY_SIZES) if MEMORY_SIZES else (f"${PRICE_CAP}" if PRICE_CAP else "")
    header = f":rotating_light: {hit['retailer']} hit"
    if filter_desc:
        header += f" — {filter_desc}"
    text = (
        f"{mentions}{header}\n"
        f"{hit['variant']} at ${hit['price']}\n"
        f"{hit['url']}"
    )
    payload = json.dumps({"text": text}).encode("utf-8")
    req = urllib.request.Request(
        SLACK_WEBHOOK_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            resp.read()
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as e:
        print(f"[slack] post failed: {e}", file=sys.stderr)


def load_state() -> dict:
    if not STATE_PATH.exists():
        return {}
    try:
        return json.loads(STATE_PATH.read_text())
    except json.JSONDecodeError:
        return {}


def save_state(state: dict) -> None:
    STATE_PATH.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n")


def main() -> int:
    if os.environ.get("TEST_PING") == "1":
        print("[test] sending Slack test ping")
        post_slack(
            {
                "retailer": "TEST",
                "variant": "end-to-end Slack wiring test",
                "price": 0,
                "url": "https://www.apple.com/shop/refurbished/mac",
            }
        )
        return 0

    all_hits: list[dict] = []
    for product_name, product_url in PRODUCTS:
        try:
            all_hits.extend(check_apple_refurb(product_name, product_url))
        except Exception as e:
            print(f"[check_apple_refurb] {product_name} error: {e}", file=sys.stderr)

    print(f"hits this run: {len(all_hits)}")
    for h in all_hits:
        print(f"  - {signature(h)} -> {h['url']}")

    previous = load_state()
    current = {signature(h): h for h in all_hits}
    new_keys = set(current) - set(previous)

    for key in new_keys:
        print(f"[alert] new hit: {key}")
        post_slack(current[key])

    save_state(current)
    return 0


if __name__ == "__main__":
    sys.exit(main())
