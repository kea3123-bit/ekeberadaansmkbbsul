# eKeberadaan audit remediation — 31 October 2026

Branch: `refactor/performance-v2`. Database of record: **cPanel MySQL**.
Google Apps Script handles only signed optional Workspace tools (Drive photos, MailApp,
exporting MySQL reports). No main database calls are made to Google Sheets.

## Fixed in code

- **PIN/login:** missing optional OTP module no longer crashes `getLoginPageData`; checks that the recovery table exists before advertising the button. Includes the `pin_recovery.php` module in the cPanel release package.
- **Admin reset contract:** one-account admin reset shows a temporary six-digit PIN **once** in the authenticated admin panel, to hand to the intended staff member privately; bulk invites users to the secure email-code flow without changing their PIN or existing sessions.
- **XSS:** 31 dynamic HTML action arguments now use escaped attribute encoding. A regression test covers quoted names and potentially hostile markup.
- **Missing endpoints:** `adminAddPublicHoliday`, `adminDeletePublicHoliday`, `adminRepairAttendanceDuplicates` now exist and require admin authentication. Public holiday changes are auditable; duplicate cleanup removes only identical records and leaves conflicting punches untouched.
- **cPanel frontend drift:** `index.php` and `php/index.php` redirect old frontend pages to the canonical GitHub Pages PWA without redirecting `api.php`.
- **Monthly reports:** MySQL prepares summary, early/late, weekly punch-card and individual sections. Signed Workspace export creates multiple spreadsheet tabs and full PDF sections. It rejects too-large reports instead of silently dropping rows.
- **Concurrency:** new writes use `_row_id` auto-increment for ordering and `_source_row=0` to indicate newly created data (the original Excel row number is no longer treated as a global counter). The punch endpoint retains per-user/date advisory locks.
- **Schema and audits:** `php/schema_core.sql` is a no-data staging reference. `php/migrations/20261031_audit_additive.sql` creates only missing runtime tables (audit, holidays, email outbox, OTP) without touching historical attendance or PINs.
- **Sessions:** MySQL expiry and frontend cookie both use a fixed 30-day window, not 7-day rolling. SHA-256 token hashes are compared correctly when revoking the current trusted session; the admin UI labels creation time, not fictitious last-seen time.
- **Safety tests:** PHP unit tests, Workspace signed-bridge tests, frontend HTML/XSS regression and an isolated MySQL 8 staging test with 200 parallel attendance writes.

## Mandatory live release order

1. **Backup** entire MySQL production database and cPanel application files. Stop edits temporarily while replacing PHP.
2. In phpMyAdmin **import only** `php/migrations/20261031_audit_additive.sql` (or packaged `02_MYSQL_ADD_ONLY.sql`). No `DROP` or `TRUNCATE`.
3. Extract the reviewed cPanel ZIP to `public_html/ekeberadaansmkbbsul/`. It includes both PHP redirect pages, root API, backend and protected private modules. Preserve `php/config.local.php` unchanged. Check regular files `0644`, directories `0755`. Do not upload the old ZIP containing credentials or logs to GitHub.
4. Replace Apps Script `Bridges.gs` and `97_WorkspaceBridge.gs` **in the existing deployment project** and deploy **New version** at the same `/exec` URL. Do not reveal bridge secrets; ensure cPanel and Apps Script match. Keep the cPanel independent email cron running.
5. Test production `getLoginPageData`, OTP, login, attendance, absence submission/review, holiday CRUD, exact duplicate repair and PDF/Sheet export.
6. Only after the API health gate passes, run the existing GitHub Actions workflow `Publish MySQL eKeberadaan with isolated Workspace services` on `refactor/performance-v2`. The publishing workflow deliberately fails while production PHP returns HTTP 500 or does not pass CORS.
7. Verify installed PWA and cross-device sessions on iPhone and Android with real users.

## Limits and open verification

- No remote cPanel deployment, phpMyAdmin migration or Apps Script editor deployment is performed by GitHub commits. Until those actions are complete, the code fixes are **not necessarily live**.
- The downloaded cPanel snapshot lacked `pin_recovery.php`; the production PHP API returned HTTP 500 for `getLoginPageData` during CI verification. This must be corrected on hosting and confirmed via its PHP log.
- Full PDF exports can exceed Google Apps Script runtime or the 2.5 MB response limit; users receive a clear error and can export Sheets or choose a shorter date range. The app does not silently truncate.
- The 200 parallel staging inserts validate schema and the new row-allocation approach; they do not prove Google API quotas, cPanel web-server limits, real GPS behavior, Gmail delivery or 200 actual simultaneous punches in production.
- SHA-256 bearer tokens remain readable by the client (cross-origin GitHub Pages architecture). HTML injection was mitigated but a fully HttpOnly design would require same-site hosting or a different authentication transport.
- Existing exposed MySQL passwords or Workspace secrets should be rotated privately. Never include `config.local.php` or PHP `error_log` in a distributable artifact.
