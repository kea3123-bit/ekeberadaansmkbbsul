# Audit kelajuan MySQL / Google Drive — 29 Oktober 2026

**Repository:** `kea3123-bit/ekeberadaansmkbbsul`  
**Branch untuk semua pindaan:** `refactor/performance-v2`

## Kesimpulan penting: kod di branch tidak semestinya kod frontend live

Pada masa audit, fail `gh-pages/index.html` dalam repo mempunyai preconnect ke
`script.google.com`, manakala `gh-pages/sw.js` menyenaraikan
`gas-shim.8a36f9e99c8e.js`. Itu ialah binaan **Google Apps Script**.
Branch `refactor/performance-v2` juga mempunyai `web/gas-shim.js` dan
`Scripts.html` yang menggunakan `google.script.run`.

Sebaliknya, projek `main/mysql-ui/` mengandungi frontend **PHP/MySQL** yang
menghantar permintaan ke `https://ppdkmy.edu.my/ekeberadaansmkbbsul/api.php`.
Kehadiran `gh-pages` berasaskan GAS tidak membuktikan tetapan Pages sudah
menggunakan branch itu (GitHub juga mempunyai sumber deployment Actions).
Periksa **Settings → Pages → Build and deployment** dan Network browser
sebelum mendakwa frontend live sudah bermigrasi.

**Jangan sesekali deploy semula `refactor/performance-v2` menggunakan
`github-pages.yml` lama sebagai pengganti frontend MySQL.**
Workflow lama membina UI Apps Script, bukan PHP/MySQL. Tukar sumber builder
kepada frontend MySQL dahulu dan sahkan ujian end-to-end sebelum sebarang
publish ke `gh-pages`. Fail PHP dalam branch ini adalah untuk hosting cPanel,
bukan kod yang boleh dijalankan oleh GitHub Pages.

## Bottleneck yang dikesan dan dibetulkan dalam branch

1. **Gambar profil boleh menyekat refresh:** `refreshBoot()` dahulu
   menggunakan `await loadOwnProfilePhoto(true)`, menyebabkan setiap refresh
   menunggu Google Drive serta membuang faedah cache gambar. Kini gambar
   dijalankan secara berasingan daripada pembaharuan bootstrap.
2. **Carian gambar berulang:** tambah deduplication untuk permintaan serentak
   dan backoff 60 saat selepas kegagalan. Gambar berjaya kekal dalam
   `state.photoCache` sehingga versi foto berubah atau sync dijalankan.
3. **Query MySQL N+1 pada panel Pentadbir:** `admin_data()` menggunakan
   `array_map('public_user',$us)`; `public_user()` menjalankan satu query
   `web_auth` bagi setiap pegawai. Untuk 70 pegawai itu sehingga 70 query
   tambahan, dan laporan bulanan memanggil `admin_data()` berulang.
   Kini `public_users_bulk()` membaca metadata auth dalam **satu** query
   dan memoize sepanjang *satu permintaan PHP sahaja*; logik PIN lama kekal.
4. **Had panggilan Workspace:** `php/workspace_bridge.php` masih mempunyai
   timeout 50 saat per RPC. Photo-first startup sepatutnya tidak bergantung
   pada latensi Google ini. Hanya gambar/PDF/Sheet menggunakan Google Workspace;
   kehadiran/login MySQL tidak patut melaluinya.

## Ujian

- `php php/tests/public-users-bulk-test.php`: 70 akaun dan hanya satu
  panggilan query metadata auth walaupun report diproses berulang.
- `php php/tests/admin-report-settings-test.php`: ringkasan laporan dan
  tetapan tidak rosak.
- `node --check < Scripts.html`: sintaks JavaScript.
- `php php/tests/profile-photo-lookup-test.php`: ID Drive dicari dan
  disimpan tanpa mengubah PIN.
- `apps-script/tests/workspace-bridge-routing.test.js`: JSON/HMAC/Drive route.

Semua ujian disenaraikan dalam workflow
`Validate PHP report fix and package cPanel hotfix`. Keputusan CI,
latensi sebenar atau kadar keberhasilan pada hosting live mesti disemak secara
berasingan sebelum mendakwa peningkatan numerik.

## Cara mengukur di browser (tanpa kongsi PIN/token)

Buka DevTools → Network → Preserve log → reload sekali:

- `https://ppdkmy.edu.my/ekeberadaansmkbbsul/api.php`:
  laluan MySQL/PHP sebenar.
- `https://script.google.com/macros/s/.../exec` untuk login, punch atau
  data admin: frontend lama masih menggunakan Apps Script/Sheets.
- Jika PHP/MySQL, bandingkan masa `resumeSession`, `getBootstrapData`,
  `getAdminData` dengan `getProfilePhoto`. Jika ketiga-tiga yang pertama
  cepat tetapi foto lambat, bottleneck ialah Google Drive. Jika panggilan
  MySQL sendiri lambat, semak indeks dan hosting PHP/MySQL.
- Untuk menyiasat, cukup catat **nama fungsi dan Duration**; jangan kongsi
  header Authorization, token sesi, body respons atau nama/emel pengguna.

## Penerbitan

Perubahan kod di branch tidak memasang PHP di cPanel, dan tidak menerbitkan
versi baru Apps Script. Backup dahulu sebelum mengemas kini fail PHP:
`php/api.php` dan `php/_lib.php` (bersama modul Workspace jika hendak
menggunakan carian foto). Jangan overwrite `php/config.local.php`, reset
database atau tukar login/PIN. Ujian sebenar perlu dilakukan pada staging
jika ada sebelum produksi.
