# Database Backups & Error Monitoring (Ops Runbook)

Two safety nets that must be live before the season starts. Neither can be
enabled purely from the codebase — they require one-time actions in the Railway
and Sentry dashboards.

## 1. Sentry error monitoring

The code is already wired (`primetimepix/settings/production.py`). It is a
**no-op until `SENTRY_DSN` is set**, so nothing breaks if you skip it — but you
should not run a live season blind.

1. Create a project at <https://sentry.io> → choose **Django**.
2. Copy the DSN it gives you.
3. In Railway → your service → **Variables**, add:
   - `SENTRY_DSN` = the DSN from Sentry
   - (optional) `SENTRY_ENVIRONMENT` = `production`
   - (optional) `SENTRY_TRACES_SAMPLE_RATE` = `0.1` (lower = cheaper)
4. Redeploy. On boot you'll no longer see the `SENTRY_DSN not set` log line.
5. Verify by triggering a test error (e.g. hit a URL that raises) and confirming
   it appears in Sentry.

`send_default_pii=False` is set, so user emails/IPs are not sent by default.

## 2. Railway Postgres backups

### Option A — Railway managed backups (recommended, set once)
1. Railway → your **Postgres** service → **Backups** tab.
2. Enable **scheduled backups** (daily is fine for a weekly-cadence app).
3. Confirm the retention window and note where to click **Restore**.

### Option B — Manual / off-Railway dump (belt-and-suspenders)
Run from any machine that has `pg_dump` and your production `DATABASE_URL`.

```bash
# One-off compressed logical backup
pg_dump "$DATABASE_URL" -Fc -f "ptp_$(date +%Y%m%d_%H%M).dump"

# Restore into a target database
pg_restore --clean --no-owner -d "$TARGET_DATABASE_URL" ptp_YYYYMMDD_HHMM.dump
```

You can get `DATABASE_URL` from Railway → Postgres → **Variables**, or via the
CLI: `railway variables`.

### Before-the-season drill
Do this once so a real restore isn't your first restore:
1. Take a manual dump (Option B).
2. Spin up a scratch Postgres (local Docker or a Railway dev DB).
3. Restore into it and confirm row counts look sane
   (`select count(*) from picks_pick;`).

## Related

- Cron jobs (schedule sync, score updates, grading) are documented in
  `CRON_JOBS.md`.
- The grading pipeline is idempotent — re-running `calculate_results` is safe
  (covered by `apps/picks/test_pipeline.py`).
