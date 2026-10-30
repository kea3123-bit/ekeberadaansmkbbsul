# eKeberadaan — cutover Google Sheets → PHP/MySQL (30 October 2026)

**Source repository:** `kea3123-bit/ekeberadaansmkbbsul`  
**Existing branch:** `refactor/performance-v2` (the branch `refactor/v2-performance` is NOT present).
**Public site:** https://kea3123-bit.github.io/ekeberadaansmkbbsul/

## Target architecture

1. Browser / PWA at GitHub Pages → CORS-safe `POST https://ppdkmy.edu.my/ekeberadaansmkbbsul/api.php`.
2. cPanel PHP → MySQL: authoritative users, email/PIN hashes, trusted sessions, attendance, absences, reviews, audit, settings, report inputs.
3. Google Workspace Apps Script → **isolated HMAC-signed tools only**: Drive profile images, PDF/Sheet *output*, MailApp delivery. Google Sheets is not queried as the application's database.
4. Notification events → MySQL `ek_email_outbox` → dedicated cPanel cron PHP worker → signed Apps Script `sendEmail`. No Google HTTP requests in login, punch, submission or review.
5. PDF/Sheet exports are user-initiated; the export data comes from MySQL, and the Workspace app only creates files.

## Deployment order (must complete before turning on MySQL frontend)

1. **Backup** the live MySQL database and the final Google Sheets attendance snapshot. Choose a reconciliation/cutover timestamp. Any punch or absence entered in Google Sheets after the last import must be migrated, or it will not appear in MySQL. Never truncate tables to deploy application code.
2. In cPanel `public_html/ekeberadaansmkbbsul`, upload **`api.php`, `php/_lib.php`, `php/api.php`, `php/workspace_bridge.php`, `php/workspace_services.php`, `php/email_queue.php`, and `php/cli/workspace_mail_worker.php`** from this branch. Preserve the existing **private** `php/config.local.php`. Include `php/.htaccess` and `php/cli/.htaccess`, and check Apache can read public PHP files. Do not publish the CLI worker.
3. In phpMyAdmin on the **same database** configured by cPanel, run additive `php/migrations/20261030_email_outbox.sql`. This creates one table; it never drops, truncates or edits user/attendance/PIN tables.
4. In original Google Apps Script project, deploy `apps-script/Bridges.gs` and `apps-script/97_WorkspaceBridge.gs` from this branch using **Deploy → Manage deployments → Edit existing Web App → New version → Deploy**. Authorize Drive, Docs, Sheets and MailApp scopes using the deploying account. Confirm both sides have the same **private** `EK_WORKSPACE_BRIDGE_SECRET` / `workspace_bridge_secret` value without exposing it.
5. Confirm `php/config.local.php` contains correct private MySQL credentials, `workspace_gas_url` (existing HTTPS `/exec` endpoint), `workspace_bridge_secret`, and if needed the **original** `legacy_pin_pepper` to verify imported Google Sheets PIN_V1 hashes. PHP hashes in `web_auth` stay in MySQL; do not reset them. Never paste a pepper or PIN into GitHub.
6. Set cPanel **Cron Jobs** to run every minute, using an appropriate absolute PHP CLI path, e.g. `/usr/local/bin/php /home/ACCOUNT/public_html/ekeberadaansmkbbsul/php/cli/workspace_mail_worker.php` (replace `ACCOUNT` with real hosting account, confirm `php` executable in cPanel). Do not put secrets in cron command. Email can be retried up to six attempts; an unconfigured cron does not prevent login or punch. The same cron also queues **07:00 yesterday's MySQL attendance summary** and enabled **PUNCH_REMINDER_TIME** reminders on configured workdays.
7. **Check live API before publish**: POST `getLoginPageData` using `Content-Type: text/plain;charset=UTF-8` and `Origin: https://kea3123-bit.github.io`; expect 200 JSON, `ok=true`, `mode=delima-email-pin`, and `Access-Control-Allow-Origin` exactly the Pages origin. Test a trusted user's MySQL attendance read and that their PIN login succeeds. Do not log tokens.
8. GitHub Actions `Publish MySQL eKeberadaan with isolated Workspace services` on `refactor/performance-v2` builds hashed PWA JS/CSS/logo, runs unit checks and **refuses to update `gh-pages` if cPanel API/MySQL/CORS is not ready**. Run the workflow again only after backend is verified if it failed its readiness gate.
9. Once MySQL site and notifications are confirmed, **run `disableLegacySheetTriggersAfterMySqlCutover()` once in the **Apps Script editor** to disable old spreadsheet-based Apps Script notification triggers** (old Sheets attendance reminder, yesterday reports) so stale Google Sheets records do not generate duplicate notifications. Do NOT disable the Workspace bridge Web App.

## Verification and rollback

- In DevTools Network, all login/punch/absence/admin API posts must go to `ppdkmy.edu.my/.../api.php`; no `exec?bridge=1` for primary operations.
- `getProfilePhoto` is an optional API action after the dashboard loads; a failure must not block punch. Email outbox is asynchronous, not called from the browser.
- `ek_email_outbox`: pending → sending → sent; inspect counts, NOT email bodies, for failures.
- The PHP/MySQL worker uses at-least-once delivery with six-hour Google-side deduplication for retries. Exceptional timeouts after a mail has been accepted can still duplicate messages.
- If the API is blocked by a cPanel firewall or MySQL auth fails, **do not** force the Pages deployment; correct hosting permissions/CORS first. The existing live Sheets build remains until Pages is safely replaced.
- Keep old Google Sheets data as a **read-only backup**, not a second write target. A frontend rollback requires deliberate reconciliation to avoid losing MySQL-only records.
