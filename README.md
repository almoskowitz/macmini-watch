# macmini-watch

Polls Apple's Certified Refurbished store every ~10 minutes for an M4 Mac mini at $600 or less. Posts to Slack `#product-updates` on a new hit.

## Setup

1. Create a GitHub Actions secret named `SLACK_WEBHOOK_URL` with the incoming webhook URL.
2. Push the repo. The cron starts on its own.

## Manual test ping

Actions tab → Mac Mini stock watch → Run workflow → check **Send a Slack test ping and exit**. Confirms the webhook is wired up without waiting for inventory.

## Local test run

```sh
SLACK_WEBHOOK_URL="" python3 check.py
```

(Empty webhook = dry-run; hits print to stderr instead of posting.)

## Notes

- State is committed back to `state.json` after each run so duplicate hits don't re-alert. If a listing goes out of stock and comes back, you'll get re-pinged.
- GitHub Actions cron is best-effort; runs typically land every 10–20 min.
