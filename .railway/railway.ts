// Railway Infrastructure as Code — PrimeTimePix
// -----------------------------------------------------------------------------
// Declares the whole Railway environment in one file: the web service, the
// Postgres database, and the scheduled cron jobs (previously documented as
// manual steps in CRON_JOBS.md). Apply with the Railway CLI (>= 5.42.1):
//
//   railway config plan     # preview the diff — CHANGES NOTHING (safety gate)
//   railway config apply    # apply after reviewing the plan
//
// IaC is DECLARATIVE: Railway is made to match this file exactly. Anything live
// but NOT described here is proposed for DELETION. That is why every existing
// web-service variable is listed below with preserve() — it tells Railway to
// KEEP the value it already has (secrets never get written into this repo).
//
//   >>> The goal of `railway config plan` is "0 to destroy". If a plan ever
//   >>> shows a delete for a service or a variable you rely on, STOP and add it
//   >>> here (service) or list it with preserve() (variable) before applying.
// -----------------------------------------------------------------------------

import { defineRailway, github, postgres, project, service, fn, preserve } from "railway/iac";

const REPO = "nateynate20/primetimepix";

export default defineRailway(() => {
  // ── Database ───────────────────────────────────────────────────────────────
  // Matches the existing Railway Postgres service (default name "Postgres").
  const db = postgres("Postgres");

  // ── Web ────────────────────────────────────────────────────────────────────
  // Matches the existing "primetimepix" web service. Build + start mirror your
  // railway.toml (which this replaces). Every existing variable is preserved so
  // none get wiped on apply.
  const web = service("primetimepix", {
    source: github(REPO),
    build: {
      builder: "NIXPACKS",
      buildCommand:
        "pip install -r requirements.txt && python manage.py collectstatic --noinput",
    },
    start:
      "python manage.py migrate --noinput && gunicorn primetimepix.wsgi:application --bind 0.0.0.0:$PORT",
    healthcheck: "/",
    healthcheckTimeout: 300,
    deploy: { restartPolicyType: "ON_FAILURE" },
    // Keep the 15 live variables exactly as they are in Railway today.
    env: {
      BREVO_API_KEY: preserve(),
      DATABASE_URL: preserve(),
      DEFAULT_FROM_EMAIL: preserve(),
      DJANGO_SETTINGS_MODULE: preserve(),
      NFL_API_KEY: preserve(),
      NFL_SEASON: preserve(),
      PYTHON_VERSION: preserve(),
      SECRET_KEY: preserve(),
      SENTRY_DSN: preserve(),
      SENTRY_ENVIRONMENT: preserve(),
      SENTRY_TRACES_SAMPLE_RATE: preserve(),
      SERVER_EMAIL: preserve(),
      SITE_NAME: preserve(),
      SITE_URL: preserve(),
      WEB_CONCURRENCY: preserve(),
    },
  });

  // Config the cron jobs need to run. DATABASE_URL comes straight from Postgres;
  // the rest are referenced from the web service so there is ONE source of truth
  // (change a value on "primetimepix" and the crons pick it up). WEB_CONCURRENCY
  // is gunicorn-only, so it is intentionally omitted here.
  const cronEnv = {
    DATABASE_URL: db.env.DATABASE_URL,
    DJANGO_SETTINGS_MODULE: web.env.DJANGO_SETTINGS_MODULE,
    SECRET_KEY: web.env.SECRET_KEY,
    PYTHON_VERSION: web.env.PYTHON_VERSION,
    NFL_API_KEY: web.env.NFL_API_KEY,
    NFL_SEASON: web.env.NFL_SEASON,
    BREVO_API_KEY: web.env.BREVO_API_KEY,
    DEFAULT_FROM_EMAIL: web.env.DEFAULT_FROM_EMAIL,
    SERVER_EMAIL: web.env.SERVER_EMAIL,
    SITE_NAME: web.env.SITE_NAME,
    SITE_URL: web.env.SITE_URL,
    SENTRY_DSN: web.env.SENTRY_DSN,
    SENTRY_ENVIRONMENT: web.env.SENTRY_ENVIRONMENT,
    SENTRY_TRACES_SAMPLE_RATE: web.env.SENTRY_TRACES_SAMPLE_RATE,
  } as const;

  // Helper: a cron job = a `fn` running one management command on a schedule,
  // that exits when done (restart policy NEVER so Railway doesn't relaunch it).
  const cron = (name: string, schedule: string, command: string) =>
    fn(name, {
      source: github(REPO),
      build: "pip install -r requirements.txt",
      start: command,
      env: cronEnv,
      deploy: {
        cronSchedule: schedule,
        restartPolicyType: "NEVER",
      },
    });

  // ── CRON JOBS ──────────────────────────────────────────────────────────────
  // Schedules are UTC. Minimum granularity on Railway is every 5 minutes; a run
  // is skipped if the previous one is still going, so keep each command idempotent.

  // 1) Update NFL scores — every 15 min on game days. CRITICAL: resolves picks.
  //    Cron day field: 0=Sun, 1=Mon, 4=Thu, 6=Sat.
  const updateScores = cron(
    "cron-update-scores",
    "*/15 * * * 0,1,4,6",
    "python manage.py update_scores",
  );

  // 2) Sync NFL schedule — weekly, Mondays 06:00 UTC.
  const syncSchedule = cron(
    "cron-sync-schedule",
    "0 6 * * 1",
    "python manage.py sync_nfl_schedule --season 2026",
  );

  // 3) Send pick reminders — hourly on game-adjacent days.
  const pickReminders = cron(
    "cron-pick-reminders",
    "0 * * * 0,1,3,4,6",
    "python manage.py send_pick_reminders",
  );

  // 4) Generate CPU picks — daily 05:00 UTC (optional vs-CPU feature).
  const cpuPicks = cron(
    "cron-generate-cpu-picks",
    "0 5 * * *",
    "python manage.py generate_cpu_picks",
  );

  return project("primetimepix", {
    resources: [db, web, updateScores, syncSchedule, pickReminders, cpuPicks],
  });
});
