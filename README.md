# eKeberadaan SMKBBSUL

## Production architecture (29 Oktober 2026)

**Frontend:** https://kea3123-bit.github.io/ekeberadaansmkbbsul/ — static GitHub Pages, generated from `mysql-ui/` on branch `refactor/performance-v2`.

**Backend:** PHP API at `https://ppdkmy.edu.my/ekeberadaansmkbbsul/api.php` — MySQL is the only authoritative store for accounts, authentication, sessions, punch records, absences, reviews and administration.

**Google Workspace:** Used only through a signed PHP → Apps Script bridge for Google Drive profile photos, PDF/Google Sheet report outputs and **MailApp email delivery**. Notification events are queued in MySQL and delivered by an independent cPanel cron worker. Do **not** use the former Sheets-based login, attendance or RPC path in production.

### Canonical source

- `mysql-ui/Index.html`, `mysql-ui/Scripts.html`, `mysql-ui/Styles.html`, `mysql-ui/Logo.html` — frontend source.
- `mysql-ui/php/index.php` — static HTML renderer that replaces `google.script.run` with direct PHP API requests during the GitHub Actions build.
- `php/api.php`, `php/_lib.php`, `php/workspace_services.php`, `php/workspace_bridge.php` — cPanel PHP backend source. Deployment to cPanel is **separate** from Pages.
- `apps-script/Bridges.gs`, `apps-script/97_WorkspaceBridge.gs` — optional, signed Workspace operations. Google Web App deployment is **separate**.
- `docs/PERFORMANCE_AUDIT_MYSQL_2026-10-29.md` — performance bottlenecks and deployment verification.

### Deployment safeguards

The only Pages publisher in this branch, `.github/workflows/github-pages.yml`, builds from `mysql-ui/`, validates that the generated HTML contains the direct PHP API and no Google Sheets RPC, then checks cPanel PHP API health and CORS from `https://kea3123-bit.github.io` before updating `gh-pages`.

The older root `Index.html`, `Scripts.html`, `Styles.html`, `Logo.html`, `web/gas-shim.js` and `scripts/build-pages.py` are **legacy Apps Script frontend source, not production**. Never run the old GAS static publisher against `gh-pages` or point GitHub Pages at those files.

GitHub Pages hosts static files only: it cannot serve PHP or access MySQL directly. PHP must already be configured on cPanel. Keep `php/config.local.php`, MySQL credentials, PIN peppers, session secrets and Workspace HMAC secrets out of GitHub.

### Verification

In Chrome → DevTools → Network, after reloading the production URL:

- Login, session, attendance and admin operations should POST JSON to `ppdkmy.edu.my/ekeberadaansmkbbsul/api.php`.
- They **must not** call `script.google.com/macros/s/.../exec?bridge=1` or `userCodeAppPanel`.
- Photo retrieval may use the Google Workspace bridge **server-to-server** from cPanel; it should not block initial dashboard render.
- The service worker must be the `eke-pwa-shell-v1` PHP/MySQL version, not `eke-static-...` from the old GAS build.

If the deployment workflow fails, leave the existing public site in place. Inspect the workflow logs rather than bypassing health/CORS checks. Do not reset PINs or re-import MySQL to repair a frontend deployment.

Timezone: `Asia/Kuala_Lumpur`.

**Deployment:** The frontend may be published independently; updated PHP, the additive `ek_email_outbox` table, the Workspace script and cPanel cron still need separate deployment. See [`docs/MYSQL_WORKSPACE_CUTOVER_2026-10-30.md`](docs/MYSQL_WORKSPACE_CUTOVER_2026-10-30.md).
