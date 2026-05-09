# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A GitHub Actions cron job that polls Apple's Certified Refurbished store for M4 Mac mini and Mac Studio listings, filters by memory size and/or price cap, and posts new hits to Slack. Zero dependencies — pure Python stdlib.

## Running locally

```sh
# Dry-run (no Slack post, logs what would be sent to stderr)
SLACK_WEBHOOK_URL="" python3 check.py

# Live run with a real webhook
SLACK_WEBHOOK_URL="https://hooks.slack.com/services/..." python3 check.py

# Test ping only (skips the actual scrape)
TEST_PING=1 SLACK_WEBHOOK_URL="https://hooks.slack.com/services/..." python3 check.py
```

## Architecture

**`check.py`** is the entire program. Key behaviors:

- `PRODUCTS` — list of `(product_name, url)` pairs at the top of `check.py`. Add entries here to watch additional Apple refurb pages.
- `check_apple_refurb(product, url)` — fetches the given refurb page, regex-parses it for listings matching "Refurbished...{product}...M4", then filters by `MEMORY_SIZES` and `PRICE_CAP`. Returns list of hit dicts.
- `main()` — iterates over `PRODUCTS`, loads `state.json` (previous run's hits keyed by `retailer|variant|price`), posts only *new* keys to Slack, then saves the current hits back to `state.json`.
- **Deduplication**: `state.json` is committed back to the repo after each run by the workflow. This means a listing only triggers one Slack alert even across many runs.
- `TEST_PING=1` short-circuits everything — sends a dummy Slack message and exits without scraping.

## Environment variables / secrets

| Name | Source | Purpose |
|------|--------|---------|
| `SLACK_WEBHOOK_URL` | GitHub secret | Slack incoming webhook. Empty = dry-run. |
| `SLACK_MENTION_USER_IDS` | GitHub secret | Optional comma-separated Slack user IDs to @-mention |
| `MEMORY_SIZES` | Workflow env var | Comma-separated memory sizes to match (e.g. `"64GB,96GB,128GB"`). Any match triggers alert. Empty = any. |
| `PRICE_CAP` | Workflow env var | Dollar ceiling for alerts. `0` = no cap. |
| `TEST_PING` | Workflow input | Set to `1` to send test ping and exit |

## Workflow

`.github/workflows/macmini.yml` runs on a `*/10 * * * *` cron and on `workflow_dispatch` (with a test-ping checkbox). After `check.py` runs, it commits `state.json` back if changed. Concurrency is set to `cancel-in-progress: false` so overlapping runs queue rather than drop.

## Adapting for a different product

Change the URL and the regex in `check_apple_refurb()`. Apple's refurb pages are server-rendered HTML — straightforward to parse. Other retailers (Amazon, Best Buy) block GitHub Actions IPs with 503s/CAPTCHAs.
