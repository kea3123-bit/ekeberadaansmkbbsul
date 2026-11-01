# eKeberadaan SMKBBSUL

Baseline awal: **Global Login Fix**.

## Struktur include semasa

1. `Scripts.html` mengandungi JavaScript mentah dan **TIDAK** mempunyai tag `<script>` / `</script>`.
2. `Index.html` membungkus `<?!= include('Scripts'); ?>` dalam tag `<script>`.
3. Oleh sebab partial `Scripts.html` bukan HTML standalone, `include()` dalam `Code.gs` **mesti** menggunakan raw template content:

```javascript
function include(filename) {
  return HtmlService.createTemplateFromFile(filename).getRawContent();
}
```

Jangan gunakan `HtmlService.createHtmlOutputFromFile(filename).getContent()` untuk struktur ini kerana Apps Script akan cuba parse `Scripts.html` sebagai HTML dan menghasilkan `Exception: Malformed HTML content: const state = ...`.

## Deploy

Selepas perubahan, deploy sebagai **NEW VERSION** dan buka URL `/exec`.

Ujian console selepas deploy:

```js
typeof checkDelimaAccount
// "function"

window.__EK_SCRIPTS_LOADED__
// true
```

Repo ini ialah source of truth untuk perubahan eKeberadaan selepas 6 September 2026.

## Legacy Google Sheets e-mel — retired after MySQL migration (1 Nov 2026)

The historical root `Code.gs` no longer sends e-mails via `MailApp` or creates time-based notification triggers. **The production system is MySQL/PHP and cPanel cron `php/cli/workspace_mail_worker.php`.** Keep the signed `mysql-ui/workspace/97_WorkspaceBridge.gs` and all Gmail/Drive/Docs functions required by the current PHP integration; do not delete the Apps Script project.

### One-time change required in the actual Google Apps Script editor

**A GitHub commit does not automatically replace the Apps Script editor source or delete triggers already installed in Google's scheduler.**

1. Open the original Google Sheets-bound Apps Script project in script.google.com and select **Triggers** (clock icon).
2. Remove the three old installable trigger handlers, if present:
   - `sendPunchReminderTrigger`
   - `sendYesterdayAttendanceReportTrigger`
   - `checkExpiredPresenceWithoutPunchTrigger`
3. In **Project Settings → Script Properties**, set `EK_EMAIL_NOTIFICATIONS_ENABLED` to `FALSE`. This blocks the historical mail workflow even if an old trigger fires.
4. If the editor project has been updated to this `Code.gs` version, execute `disableLegacyEmailTriggers()` once while signed in as the account that created the triggers. Confirm the returned `count` and `deleted` entries. Triggers owned by another Google account must be removed by that owner.
5. Do not run the old `setupSystem`, `installEmailNotificationsFromMenu`, or old reminder buttons from archived source. The updated version no longer installs/sends legacy e-mail, but older deployed copies may.
6. Verify cPanel cron continues normally, and that new notification records appear in MySQL `ek_email_outbox` with statuses such as `pending` → `sent`.

The Gmail address used to send e-mails may remain the same. What matters is that notification **data and job scheduling** come only from MySQL now.
