# Keep-Alive & Health-Check (added 2026-08-23)

Set up by the **hotelPandL** Claude Code session. Documented here because the
three apps have separate repos / separate Claude Code sessions.

## What was added

- `.github/workflows/keepalive.yml` — a **daily** GitHub Actions workflow that:
  1. Does a **real DB write** (`PATCH /rest/v1/keepalive?id=eq.1`) to keep the
     Supabase project awake.
  2. **Health-checks** this app (`https://instanoucentista.streamlit.app/`).
  3. Exits non-zero if either fails, so GitHub sends the **native failed-run
     email** to the repo owner.
- GitHub repo **secrets** `SUPABASE_URL` and `SUPABASE_SERVICE_KEY` (set on
  2026-08-23).

## Important context

- **Shared Supabase project**: instaHotel, hotelPandL and suppliers ALL use the
  same project `lngrockgpnwaizzyvwsk`. This DB auto-pauses after ~7 days idle
  and, when paused, its host stops resolving in DNS — which breaks **all three
  apps** at once (this actually happened 2026-08-03 and 2026-08-16).
- The DB write here is **redundant by design** with the identical workflows in
  hotelPandL and suppliers: one project, kept alive from three repos, so it
  survives even if one repo goes quiet.
- A dedicated table `keepalive(id int pk, last_ping timestamptz)` (row id=1,
  RLS on — service_role bypasses it) was created in the shared project. It
  already exists; don't recreate it.

## Gotchas / to know

- **GitHub disables scheduled workflows after 60 days of no repo activity.** Any
  commit (or a manual "Run workflow") re-enables it.
- To actually receive the failure email, keep **GitHub Actions notifications on**
  (github.com/settings/notifications -> Actions -> failed workflows).
- The workflow lives on the **`main`** branch (default branch) so the cron
  fires; a copy is on `local` for visibility.
- A write (not a read) is used on purpose: a read can be served from cache
  without hitting Postgres, so it didn't reliably prevent the pause.

## Manual test

Actions tab -> "Supabase Keep-Alive" -> "Run workflow", or:
`gh workflow run keepalive.yml --repo thierrykleinorama-cloud/instaHotel`
Expected: `DB OK (HTTP 200)` + `App OK (HTTP 3xx)` + `All checks passed`.
