# PHP/MySQL report hotfix — 29 Oktober 2026

**Repository:** `kea3123-bit/ekeberadaansmkbbsul`  
**Development branch:** `refactor/performance-v2`  
**Live PHP hosting:** `ppdkmy.edu.my` (cPanel).

## Punca yang disahkan

Rujukan cPanel `9D1A5C6D`:

```text
TypeError: public_settings() expects array, string given
php/_lib.php:185, called by php/api.php:510
```

Dalam fungsi `admin_data()`, `$s=settings_raw()` menyimpan array tetapan. Kod lama kemudian menggunakan `$s=$r['status']` untuk mengira ringkasan kehadiran. Ini menimpa array dengan string dan menyebabkan `public_settings($s)` gagal.

Kod branch ini telah menggunakan `$attendanceStatus` supaya array tetapan tidak ditimpa.

## Deploy satu fail sahaja (tanpa database migration)

1. Buka GitHub Actions pada **repo kea3123-bit sahaja** → **Validate PHP report fix and package cPanel hotfix** → pilih run branch `refactor/performance-v2`.
2. Muat turun artifact **`ekeberadaansmkbbsul-report-hotfix`**; ekstrak ZIP dan dapatkan `php/api.php`. (Artifact tersedia hanya selepas workflow berjaya.)
3. Dalam cPanel → File Manager, pergi ke `public_html/ekeberadaansmkbbsul/php/`.
4. Backup `api.php` lama, kemudian replace dengan `api.php` dari ZIP tadi. Jangan tersalah ganti root `public_html/ekeberadaansmkbbsul/api.php`.
5. Uji **Panel Pentadbir**, **Jana PDF Template**, dan **Jana Template ke Sheet** sekali lagi.

Fail hotfix juga boleh diambil terus dari `php/api.php` dalam branch `refactor/performance-v2`. Jika mahu pakej backend penuh, workflow menyediakan artifact `ekeberadaansmkbbsul-backend`, tetapi jangan ganti fail lain tanpa sebab yang dikenal pasti.

**JANGAN** overwrite `php/config.local.php`, reset PIN, reimport MySQL, atau upload fail konfigurasi/rekod staf ke GitHub.

## Ralat kedua yang berasingan

`Respons Google Workspace bukan JSON` di `php/workspace_bridge.php:54` turut berulang dalam `error_log`. Ini tidak diselesaikan oleh pembetulan TypeError. Semak cPanel Workspace URL/secret dan deployment Apps Script `workspaceBridgePost_` yang aktif secara peribadi, tanpa mendedahkan secret. Fail backend PHP sahaja tidak mengubah Google Apps Script yang telah dideploy.

## Catatan seni bina

Branch `refactor/performance-v2` asalnya menggunakan frontend + Apps Script + Google Sheets. Backend PHP/MySQL yang ditambah di `php/` adalah fail **untuk deployment cPanel berasingan**, bukan bertujuan menukar frontend branch ini secara automatik. GitHub Pages tidak boleh menjalankan PHP.
