# eKeberadaan — MySQL Frontend (kea3123-bit)

## Data architecture
- GitHub Pages (`https://kea3123-bit.github.io/ekeberadaansmkbbsul/`) serves HTML/JS/CSS only.
- Login, user accounts, punch-clock records, absences, review, admin and reporting **read/write MySQL exclusively** via authenticated JSON RPC at `https://ppdkmy.edu.my/ekeberadaansmkbbsul/api.php`.
- The PHP API reads database credentials from `php/config.local.php` **on cPanel only**. Never put this file, passwords, PIN peppers, SQL dumps, or student/staff records in GitHub.
- Google Workspace integration (Drive profile images, Google Docs/PDF/Sheets exports) continues **only through the signed cPanel → Apps Script Workspace bridge** in the separate PHP backend. Google Sheets is not used for login or attendance data.
- The original `Code.gs` and `Scripts.html` at repository root are retained as historical Workspace source. Production GitHub Pages uses **`mysql-ui/`**. Do not deploy the root Google Sheets UI again.

## Current development branch and publisher

- **Source branch:** `refactor/performance-v2` in **this same repository**.
- **Live Pages publisher:** `.github/workflows/github-pages.yml` on this branch, generating static HTML from `mysql-ui/` and checking cPanel API health/CORS before staging the `gh-pages` output.
- **Never republish** root `Scripts.html` via the old `scripts/build-pages.py`; that bundles Google Apps Script RPC and makes the site slow.
- **PHP backend source:** `php/` in this branch; deploy to cPanel separately, preserving `php/config.local.php` and MySQL data.
- **Google Workspace bridge:** `apps-script/97_WorkspaceBridge.gs` in this branch; deploy a New version separately in Google Apps Script.

## Deployment
- GitHub workflow `.github/workflows/github-pages.yml` on `refactor/performance-v2` renders `mysql-ui/index.php` into static HTML, validates PHP API health and CORS, and then stages **gh-pages**.
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
maintained in this repository's `php/` folder on `refactor/performance-v2`. An update to GitHub Pages
does **not** deploy PHP to cPanel.

1. Back up the installed `public_html/ekeberadaansmkbbsul/php/api.php`.
   Deploy this branch's `php/api.php` (or merge
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
