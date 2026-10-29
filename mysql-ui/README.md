# eKeberadaan — MySQL Frontend (kea3123-bit)

## Data architecture
- GitHub Pages (`https://kea3123-bit.github.io/ekeberadaansmkbbsul/`) serves HTML/JS/CSS only.
- Login, user accounts, punch-clock records, absences, review, admin and reporting **read/write MySQL exclusively** via authenticated JSON RPC at `https://ppdkmy.edu.my/ekeberadaansmkbbsul/api.php`.
- The PHP API reads database credentials from `php/config.local.php` **on cPanel only**. Never put this file, passwords, PIN peppers, SQL dumps, or student/staff records in GitHub.
- Google Workspace integration (Drive profile images, Google Docs/PDF/Sheets exports) continues **only through the signed cPanel → Apps Script Workspace bridge** in the separate PHP backend. Google Sheets is not used for login or attendance data.
- The original `Code.gs` and `Scripts.html` at repository root are retained as historical Workspace source. Production GitHub Pages uses **`mysql-ui/`**. Do not deploy the root Google Sheets UI again.

## Deployment
- GitHub workflow `.github/workflows/mysql-pages.yml` builds `mysql-ui/index.php` into static HTML, then pushes to branch **gh-pages**.
- In repo Settings > Pages choose **Deploy from a branch** → **gh-pages** → **/ (root)**.
- Commits made by GitHub Actions with `GITHUB_TOKEN` do not trigger GitHub Pages build. To trigger a new GitHub Pages deployment, push a small commit to `gh-pages` with a real user's GitHub credential or run an administrator-authorized workflow using a token that triggers Pages.
- The service worker retirement script unregisters prior Google Sheets PWA caching and deletes caches starting with `eke-static-`.

## Required cPanel patch
The API PHP must allow HTTPS origin `https://kea3123-bit.github.io` (as well as `https://farshoffs.github.io`). The API uses explicit authentication tokens in JSON; CORS is **not authentication**.
Update **only** `public_html/ekeberadaansmkbbsul/api.php` and `public_html/ekeberadaansmkbbsul/php/api.php` using the CORS patch from the `farshoffs` backend. Preserve `php/config.local.php` and database.

## Validation
Use Chrome DevTools > Network while checking login:
- PASS: requests to `https://ppdkmy.edu.my/ekeberadaansmkbbsul/api.php`
- FAIL: `script.google.com/macros/...` requests for login/punch/absence/storage

From browser console:
```js
fetch('https://ppdkmy.edu.my/ekeberadaansmkbbsul/api.php', {
  method: 'POST', credentials: 'omit',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({fn:'getApiStatus',args:[]})
}).then(async r => console.log(r.status, await r.text())).catch(console.error);
```
Expected: HTTP 200 and `healthy:true` (only if the cPanel PHP patch is deployed).

## Google Drive profile pictures (MySQL)

The production frontend is in this repository, but the deployed PHP API is
maintained in `farshoffs/ekeberadaansmkbbsul/php/`. An update to GitHub Pages
does **not** deploy PHP to cPanel.

1. Back up the installed `public_html/ekeberadaansmkbbsul/php/api.php`.
   Deploy the latest `farshoffs/ekeberadaansmkbbsul/php/api.php` (or merge
   its `profileRootFolderId` mapping if cPanel contains custom modifications).
   Preserve the existing `php/config.local.php` and MySQL database.
2. Ensure `php/workspace_bridge.php`, `php/workspace_services.php`,
   `apps-script/97_WorkspaceBridge.gs`, and the signed `workspaceBridgePost_`
   doPost hook have all been deployed. Never paste the bridge secret into GitHub.
3. Pentadbir Sistem → Tetapan → Keselamatan & Profil: enter the **folder ID**
   from the Drive root folder URL, click **Simpan tetapan**, and confirm the
   page says the ID was saved. Then click **Sync Sekarang**.
4. Required hierarchy: root folder → `01 - Pengurusan` / `02 - Guru` /
   `03 - Anggota Kumpulan Pelaksana` / `04 - Praktikum` / `05 - MySTEP`
   → exact staff-name folder → `eoperasi.png`.
   The Google account running Apps Script must have Drive access.
5. Reload the application after a successful sync. The dashboard requests
   `getProfilePhoto` from PHP; the PHP bridge retrieves the private photo from
   Drive. The public website must never include Google Drive credentials.

If the avatar still shows an initial, read the new diagnostic below **Sync
Sekarang**. It distinguishes missing folder configuration, unmatched names,
backend bridge failures and image retrieval errors.

## Google Workspace limits
The signed bridge currently implements profile photos, Drive-based photo sync, PDF and Sheet export. **Automated Gmail/MailApp notifications and old timed triggers are not migrated**. Do not continue running older GAS notifications that read Google Sheets as though it were the authoritative database; they could send incorrect messages. A separate MySQL-backed notification queue and signed Workspace email handler are required for full email parity.

## Troubleshooting: "Ralat PHP pada hosting" when generating monthly reports

If **Pentadbir Sistem → Jana Laporan → Jana PDF Template** or **Jana Template ke Sheet** displays `Ralat PHP pada hosting ... Rujukan: XXXXXXXX`:

1. The reference is a **per-request PHP error-log ID**, not a fixed error code. Search cPanel → Metrics → Errors or File Manager → `error_log` for `[eKeberadaan API XXXXXXXX]` (replace `XXXXXXXX` with the reference actually displayed). The log contains the exception class, source path and line. Do not share passwords, PINs or MySQL credentials.
2. Check that all of these exist together in **cPanel**, not just in GitHub: `public_html/ekeberadaansmkbbsul/api.php`, `php/api.php`, `php/_lib.php`, `php/workspace_services.php` and `php/workspace_bridge.php`. The two-file CORS-only ZIP does **not** install Workspace modules. A missing module is one possible cause of the generic PHP error, especially when Drive photos also fail.
3. Obtain the matching PHP files from the **same release** in [the backend repository](https://github.com/farshoffs/ekeberadaansmkbbsul), preferably the dedicated cPanel package generated by its `Build cPanel upload package` workflow. Back up the installed files before updating. **Never overwrite** `php/config.local.php`, import the database again, or upload secrets to GitHub.
4. If the modules are present, inspect the matching log line before changing any code. The PHP bridge also depends on private `workspace_gas_url` and `workspace_bridge_secret` settings and the latest Apps Script `workspaceBridgePost_` deployment; configuration failures normally return a different, more specific message.
5. After deploying, re-test **both** monthly PDF and Sheet export. The `getApiStatus` health check above verifies only the core PHP endpoint, **not** MySQL data access, Workspace module installation, Google permissions, or report generation.

Backend diagnostic patch: [Workspace modules PR](https://github.com/farshoffs/ekeberadaansmkbbsul/pull/3). GitHub Pages updates do **not** deploy this PHP patch to cPanel.

**Current output limitation:** The PHP monthly reporting path presently generates a **single daily-summary table** (dates and attendance counts) through the Workspace bridge. The frontend description promises multiple report templates (Ringkasan, Lewat/Balik Awal, Perakam Waktu, Individu), but those full sections have not yet been implemented in the PHP report generator. A successful export does not by itself mean full template parity.
