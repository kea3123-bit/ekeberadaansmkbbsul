# Gambar profil tidak naik — pemulihan automatik MySQL + Google Drive

**Repository:** `kea3123-bit/ekeberadaansmkbbsul`  
**Branch:** `refactor/performance-v2`  
**Tarikh:** 29 Oktober 2026

## Punca yang ditemui dalam kod

Sebelum patch ini, `bootstrap()` memulangkan `hasProfilePhoto=false` jika `pengguna.fotoprofilfileid` masih kosong. UI kemudian **tidak memanggil** `getProfilePhoto`, jadi gambar tidak akan muncul walaupun fail `eoperasi.png` tersedia dalam Google Drive.

## Apa yang sudah berubah

- `php/_lib.php` — jika ID belum ada tetapi `PROFILE_ROOT_FOLDER_ID` sudah ditetapkan dalam MySQL, bootstrap membenarkan satu percubaan carian gambar semasa pengguna membuka aplikasi.
- `php/workspace_services.php` — backend mencari foto berdasarkan **nama dan kategori pengguna daripada MySQL**, bukan input ID rawak dari browser; jika dijumpai, simpan ID ke baris MySQL pengguna dan ambil imej. Pengguna lain tidak boleh meminta gambar tanpa kebenaran.
- `php/workspace_bridge.php` — benarkan operasi `findPhoto` dalam HMAC allowlist.
- `apps-script/97_WorkspaceBridge.gs` — operasi `findPhoto` membaca struktur Google Drive `kategori/nama/eoperasi.png`; menaikkan had gambar tunggal kepada 2.5MB dengan mesej jelas jika melebihi had.
- `Scripts.html` — jangan lagi telan ralat gambar tanpa sebarang mesej; paparkan sebab untuk pentadbir.
- `php/tests/profile-photo-lookup-test.php` dan `apps-script/tests/workspace-bridge-routing.test.js` — ujian tanpa pangkalan data atau kredensial sebenar.

**Tiada tindakan pada Google Sheets sebagai database.** Hanya ID gambar yang dijumpai akan ditulis ke MySQL pengguna.

## Langkah deploy ke live (wajib, GitHub tidak deploy cPanel/GAS)

1. GitHub Actions → `Validate PHP report fix and package cPanel hotfix`, run branch `refactor/performance-v2`. Muat turun `ekeberadaansmkbbsul-profile-photo-hotfix` setelah job berjaya.
2. Dalam cPanel File Manager pergi `public_html/ekeberadaansmkbbsul/php/`. Backup tiga fail lama kemudian **replace hanya**:
   - `_lib.php`
   - `workspace_services.php`
   - `workspace_bridge.php`
   
   Jangan sentuh `php/config.local.php`, PIN atau table MySQL.
3. Dalam projek Google Apps Script asal, kemas kini `Bridges.gs` dan `97_WorkspaceBridge.gs` dari branch sama. **Deploy → Manage deployments → Edit → New version → Deploy**, kekalkan URL `/exec`. Sahkan Web App boleh diakses server PHP (Execute as Me / Anyone menurut polisi Workspace) dan secret HMAC adalah sepadan, **tanpa mendedahkan secret**.
4. Dalam aplikasi sebagai Pentadbir Sistem → Tetapan, pastikan ID folder induk Drive telah disimpan. Struktur:
   `root / 03 - Anggota Kumpulan Pelaksana / NAMA PEGAWAI / eoperasi.png`
   (Untuk PPP: `02 - Guru`, Pengurusan: `01 - Pengurusan`.)
5. Refresh halaman / log masuk semula. Jika ID dalam MySQL masih kosong, aplikasi akan cuba carian automatik lalu simpan ID. Untuk padanan semua pegawai sekaligus, guna butang **Sync Gambar Profil**. Jika masih tiada, semak mesej ralat di bahagian penyelarasan gambar profil / browser console.
6. Jika hanya fail lama `php/api.php` masih digunakan, pembetulan laporan bulanan `9D1A5C6D` memerlukan deployment fail itu secara berasingan seperti panduan `CPANEL_PHP_HOTFIX_2026-10-29.md`.

## Batasan dan penyelesaian masalah

- Nama folder pegawai mesti sama selepas trim/case/normalisasi ruang dengan nama MySQL. Format fail mesti `eoperasi.png` (nama fail tak sensitif huruf besar/kecil).
- Akaun yang menjalankan Apps Script perlu mempunyai hak akses ke folder Drive dan fail.
- Gambar >2.5MB perlu dikurangkan saiznya; jangan masukkan kandungan imej ke GitHub.
- Jika status `Google Workspace bukan JSON` muncul, kemas kini dan deploy **Apps Script Bridge** dahulu. Fail yang hanya dikomit di GitHub tidak mengubah deployment sedia ada.
- Jika tiada `PROFILE_ROOT_FOLDER_ID`, UI tidak boleh menemui gambar secara automatik. Simpan dahulu melalui Tetapan Pentadbir.
- Branch ini mempunyai frontend Apps Script lama. Pakej `profile-photo-hotfix` ditujukan untuk **PHP di cPanel**, bukannya GitHub Pages; jangan deploy sumber Google Sheets sebagai pengganti frontend MySQL.
