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

## Google Workspace limits
The signed bridge currently implements profile photos, Drive-based photo sync, PDF and Sheet export. **Automated Gmail/MailApp notifications and old timed triggers are not migrated**. Do not continue running older GAS notifications that read Google Sheets as though it were the authoritative database; they could send incorrect messages. A separate MySQL-backed notification queue and signed Workspace email handler are required for full email parity.
