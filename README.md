# macmini-watch

Polls Apple Refurb, Amazon, and Best Buy every 10 minutes for an M4 Mac mini at $599 or less. Posts to Slack `#product-updates` on a new hit.

## Setup

1. Create a GitHub Actions secret named `SLACK_WEBHOOK_URL` with the incoming webhook URL.
2. Push the repo. The cron starts on its own.

## Local test run

```sh
SLACK_WEBHOOK_URL="" python3 check.py
```

(Empty webhook = dry-run; hits print to stderr instead of posting.)

## Notes

- Apple Refurb is the only retailer where $599-or-less actually shows up regularly. Amazon and Best Buy almost never list new units below MSRP, so those checks are mostly a safety net.
- Amazon often blocks GitHub Actions IPs with a CAPTCHA page. If that's happening, the script logs `[amazon] blocked` and skips it. No false positives.
- State is committed back to `state.json` after each run so duplicate hits don't re-alert.
