# Railway Cron Jobs

Cron jobs are now defined as code in `.railway/railway.ts` (Railway Infrastructure
as Code) instead of being clicked together in the dashboard. Each job is a `fn`
resource that runs one Django management command on a schedule and exits.

## Jobs (source of truth: `.railway/railway.ts`)

| Service                   | Schedule (UTC)          | Command                                        | Notes |
|---------------------------|-------------------------|------------------------------------------------|-------|
| `cron-update-scores`      | `*/15 * * * 0,1,4,6`    | `python manage.py update_scores`               | CRITICAL — resolves picks. Days: 0=Sun,1=Mon,4=Thu,6=Sat |
| `cron-sync-schedule`      | `0 6 * * 1`             | `python manage.py sync_nfl_schedule --season 2026` | Weekly, Mondays |
| `cron-pick-reminders`     | `0 * * * 0,1,3,4,6`     | `python manage.py send_pick_reminders`         | Hourly on game-adjacent days |
| `cron-generate-cpu-picks` | `0 5 * * *`             | `python manage.py generate_cpu_picks`          | Optional vs-CPU feature |

Railway runs cron in UTC, minimum granularity is every 5 minutes, and it skips a
run if the previous one is still going — so keep each command idempotent.

Off-season: leave them running (each command exits quickly when there are no
games) or set an unreachable schedule like `0 0 30 2 *`.

## Environment variables

Cron services inherit config from the IaC file:
- `DATABASE_URL` — wired from the Postgres resource in `.railway/railway.ts`.
- `DJANGO_SETTINGS_MODULE` — literal `primetimepix.settings.production`.
- `SECRET_KEY`, `BREVO_API_KEY`, `SITE_URL` — read from Railway **Shared
  Variables** (`ctx.shared.*`). Promote these to shared variables once
  (dashboard → Variables → Shared Variables) so every cron inherits them.

## Applying (Railway CLI >= 5.42.1)

```bash
# one-time setup
npm i -g @railway/cli        # or: brew install railway
railway login
railway link                 # select the primetimepix project + environment

# from the repo root
railway config plan          # SAFE: previews the diff, changes nothing
railway config apply         # applies after you confirm
```

`railway config plan` is the safety gate. Because IaC is declarative for the
whole environment, confirm the plan **only ADDS the four cron services**. If it
proposes deleting your `web` service or `Postgres`, stop and fix the resource
names in `.railway/railway.ts` to match your live services (or run
`railway config migrate` to generate the baseline from your existing
`railway.toml`, then paste in the cron block).

## Migrating off railway.toml

`railway.toml` (config-as-code) is deprecated and stops being read on
2026-12-01. Once `railway config apply` succeeds with this IaC file, the web
service is managed here and `railway.toml` can be removed.
