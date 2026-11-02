-- eKeberadaan: Sebab pengguna untuk rekod lewat / balik awal.
-- Jalankan sekali melalui phpMyAdmin > pilih database > SQL.
-- MariaDB 10.11 (seperti export 02/11/2026); tidak ubah sebarang rekod.
-- Ulasan pentadbir (ulasan) dan statussemakan kekal berasingan.
ALTER TABLE `semakan_waktu`
  ADD COLUMN IF NOT EXISTS `sebabpengguna` VARCHAR(800) NULL DEFAULT NULL AFTER `ulasan`,
  ADD COLUMN IF NOT EXISTS `sebabdihantarpada` DATETIME NULL DEFAULT NULL AFTER `sebabpengguna`;
