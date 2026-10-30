# eKeberadaan — PHP/MySQL architecture (30 October 2026)

## User-facing application

```text
Browser / installed PWA
  -> GitHub Pages (static UI, HTTPS)
  -> CORS-safe JSON POST to cPanel php/api.php (via public api.php)
  -> PDO / MySQL (single database of record)
       users / PIN hashes / sessions / attendance / absences / reviews / audit / settings
```

`mysql-ui/` is the **production frontend source**. `php/` and root
`api.php` are the **PHP/MySQL backend source**. MySQL handles every
login/punch/storage read and write. GitHub Pages never directly connects to
MySQL and never embeds credentials.

## Google Workspace integration — independent

```text
Optional profile photo / report export
  -> cPanel PHP service
  -> HMAC-signed POST to Apps Script Workspace endpoint
  -> Google Drive / Docs / Google Sheets report OUTPUT only

Absence event
  -> MySQL ek_email_outbox
  -> cPanel Cron (PHP CLI)
  -> HMAC-signed Apps Script sendEmail
  -> MailApp
```

Google Workspace must **never** be a second application database. Apps Script
`97_WorkspaceBridge.gs` is restricted to `photo`, `findPhoto`,
`syncPhotos`, `exportPdf`, `exportSheet`, `sendEmail` and `ping`.
The old `apps-script/10_Auth.gs`, `41_AttendanceData.gs` and other
Google Sheets database modules are retained only for historical rollback
and are **not** part of the MySQL application's runtime path.

Email delivery is asynchronous through `ek_email_outbox`; it does not block
login, attendance or absence submission if MailApp is unavailable.
The cPanel worker is the only client authorized to invoke the signed
`sendEmail` operation, and Google-side deduplication reduces retry duplicates.

## Release boundaries

- GitHub Actions `.github/workflows/github-pages.yml` checks the live
  PHP/MySQL API, CORS and the local build before updating `gh-pages`.
- cPanel PHP deployment is separate and requires an administrator to upload
  the validated backend files and run the additive mail outbox migration.
- The Apps Script Workspace Web App must be deployed with its existing /exec
  URL. The HMAC secret must match the server's private configuration.
- The cron email worker runs separately at cPanel. It cannot be invoked from
  GitHub Pages and contains no database credentials.
- No production data, PINs or session records are reset by code deployment.

**Cutover runbook:** `docs/MYSQL_WORKSPACE_CUTOVER_2026-10-30.md`.

Timezone: `Asia/Kuala_Lumpur`.
