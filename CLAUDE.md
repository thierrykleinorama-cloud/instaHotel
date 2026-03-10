# InstaHotel — Mandatory Rules

These rules are NON-NEGOTIABLE. Follow them on EVERY task, EVERY session.

## 1. Read Before Acting

**At the START of every session**, before doing any work:
1. Read `tasks/todo.md` — the BACKLOG section is the SINGLE canonical TODO list
2. Read the memory MEMORY.md for current project status
3. Understand what's already done before proposing anything

**Before modifying any file**, read it first. Never propose changes to code you haven't read.

## 2. Update As You Go (NOT at the end)

After completing ANY feature or fix, update ALL of these **immediately**:
- `tasks/todo.md` — mark items done, add new items to BACKLOG
- `tasks/lessons.md` — add lessons learned (errors, patterns, rules)
- Memory `MEMORY.md` — update current status section
- Memory `architecture.md` — if new files/services/pages were added

**NEVER batch these updates at the end of a session.** Do them incrementally after each meaningful step.

## 3. No Parallel TODO Lists

`tasks/todo.md` BACKLOG is the ONE source of truth. Never maintain a separate TODO list in MEMORY.md, conversation, or anywhere else. When proposing next steps, always read the BACKLOG first.

## 4. Test Before User

Always test changes yourself first (Python script, import check, syntax check). Only ask the user to test AFTER verifying it works. Save test outputs (screenshots, images) with meaningful names.

## 5. Minimal Confirmations

Do NOT ask for confirmation unless there is a risk of data loss or safety concern. Just do it.

## 6. Prompts in `/src/prompts/`

All API prompts must be in separate files under `src/prompts/`, never hardcoded in services or pages.

## 7. Session State Resilience

Maximize session state preservation on page refresh. Initialize all keys with defaults at page top. Save generated content to session state immediately. For critical outputs, persist to DB.

## 8. Deploy = merge local → main + push

Always on `local` branch for development. "Deploy" means: `git checkout main && git merge local && git push origin main && git checkout local`.

## 9. Supabase DDL via Management API

Direct Postgres and PostgREST can't run DDL. Always use the Management API (see MEMORY.md for pattern).

## 10. Key File Locations

- Canonical TODO: `tasks/todo.md` (BACKLOG section)
- Lessons: `tasks/lessons.md`
- Project memory: auto-memory `MEMORY.md`
- Architecture: auto-memory `architecture.md`
- Prompts: `src/prompts/`
- DB migrations: `supabase/`
