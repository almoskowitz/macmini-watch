# macmini-watch

A tiny GitHub Actions cron that watches Apple's Certified Refurbished store for an **M4 Mac mini** at-or-below a target price and pings a Slack channel when one shows up.

Runs every ~10 minutes, dedupes hits so you don't get spammed, and shuts up entirely when there's no inventory. Roughly 100 lines of Python with no dependencies.

## How it works

1. `check.py` fetches `https://www.apple.com/shop/refurbished/mac/mac-mini`.
2. Parses the page for listings that mention "Mac mini" + "M4" with a price at-or-below `PRICE_CAP`.
3. Compares against `state.json` (committed back to the repo each run) so duplicate listings only alert once.
4. POSTs new hits to a Slack incoming webhook.

GitHub Actions cron is best-effort and typically lands every 10–20 minutes — fine for refurb watch, not fine if you need sub-minute polling.

## Setup

1. **Fork this repo** (or use it as a template).
2. **Create a Slack incoming webhook**:
   - https://api.slack.com/apps → Create New App → From scratch
   - Activate Incoming Webhooks → Add New Webhook to Workspace → pick the channel
   - Copy the URL (looks like `https://hooks.slack.com/services/...`)
3. **Add the webhook as a repo secret**:
   - Settings → Secrets and variables → Actions → New repository secret
   - Name: `SLACK_WEBHOOK_URL`
   - Value: the webhook URL
4. **(Optional) Tune the price cap**:
   - Edit the `PRICE_CAP` env var in `.github/workflows/macmini.yml`
   - Default is `600`
5. **(Optional) Tag a Slack user on real hits**:
   - Add a repo secret `SLACK_MENTION_USER_IDS` with one or more Slack user IDs (e.g. `U07PCFNRLH3` or `U07PCFNRLH3,U08ABCDE123`).
   - All Slack messages (including test pings) will be prefixed with `<@user>` mentions.
6. The cron starts on its own once pushed.

## Manual test ping

Confirms the webhook is wired up without waiting for inventory.

Actions tab → **Mac Mini stock watch** → **Run workflow** → check **Send a Slack test ping and exit** → Run.

You should see a `:rotating_light: Mac mini $X hit — TEST` message in your Slack channel within a few seconds.

## Local dry-run

```sh
SLACK_WEBHOOK_URL="" python3 check.py
```

Empty webhook = dry-run. The script logs what it would have posted to stderr instead of actually posting.

## Adapting it

This is purpose-built for Apple Refurb Mac mini M4. To watch a different product:

- Change the URL and the regex in `check_apple_refurb()` to match the new page.
- Apple's refurb site is server-rendered HTML, which makes parsing trivial. Other retailers (Amazon, Best Buy) heavily block GitHub Actions IPs with 503s and CAPTCHAs — a previous version of this repo tried and gave up. If you need those, expect to use a third-party scraping service.

## License

MIT — see [LICENSE](LICENSE).
