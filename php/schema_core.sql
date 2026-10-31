-- eKeberadaan clean, NO-DATA reference schema for disposable staging.
-- NEVER use this file as an overwrite/import on the production database.
-- Additive CREATE IF NOT EXISTS only; pre-existing tables are unchanged.
-- Historical workbook-only tables are not application runtime dependencies.
SET NAMES utf8mb4;
CREATE TABLE IF NOT EXISTS `pengguna` (
  `_row_id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `_source_row` INT UNSIGNED NOT NULL DEFAULT 0,
  `aktif` TINYINT DEFAULT 1,
  `nama` VARCHAR(64) DEFAULT NULL,
  `emel` VARCHAR(64) DEFAULT NULL,
  `kategori` VARCHAR(64) DEFAULT NULL,
  `pentadbir` TINYINT DEFAULT 0,
  `waktulewat` VARCHAR(64) DEFAULT NULL,
  `maksmasuk` VARCHAR(64) DEFAULT NULL,
  `waktubalik` VARCHAR(64) DEFAULT NULL,
  `catatan` VARCHAR(64) DEFAULT NULL,
  `passwordsalt` VARCHAR(64) DEFAULT NULL,
  `passwordhash` VARCHAR(64) DEFAULT NULL,
  `dikuncisehingga` VARCHAR(64) DEFAULT NULL,
  `authtype` VARCHAR(64) DEFAULT NULL,
  `jawatan` VARCHAR(64) DEFAULT NULL,
  `sesi1masuk` VARCHAR(64) DEFAULT NULL,
  `sesi1keluar` VARCHAR(64) DEFAULT NULL,
  `sesi2masuk` VARCHAR(64) DEFAULT NULL,
  `sesi2keluar` VARCHAR(64) DEFAULT NULL,
  `fotoprofilfileid` VARCHAR(64) DEFAULT NULL,
  `wajibtukarpassword` INT DEFAULT 0,
  `versisesi` INT DEFAULT 0,
  `gagallogin` INT DEFAULT 0,
  `passworddikemaskinipada` DOUBLE DEFAULT NULL,
  `fotoprofildikemaskinipada` DOUBLE DEFAULT NULL,
  PRIMARY KEY (`_row_id`),
  KEY idx_pengguna_emel (`emel`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `kehadiran` (
  `_row_id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `_source_row` INT UNSIGNED NOT NULL DEFAULT 0,
  `tarikh` DATE DEFAULT NULL,
  `emel` VARCHAR(64) DEFAULT NULL,
  `nama` VARCHAR(64) DEFAULT NULL,
  `kategori` VARCHAR(64) DEFAULT NULL,
  `masuk` DATETIME(6) DEFAULT NULL,
  `balik` DATETIME(6) DEFAULT NULL,
  `masuk2` DOUBLE DEFAULT NULL,
  `balik2` DOUBLE DEFAULT NULL,
  `masuklat` DOUBLE DEFAULT NULL,
  `masuklng` DOUBLE DEFAULT NULL,
  `baliklat` DOUBLE DEFAULT NULL,
  `baliklng` DOUBLE DEFAULT NULL,
  `masuk2lat` DOUBLE DEFAULT NULL,
  `masuk2lng` DOUBLE DEFAULT NULL,
  `balik2lat` DOUBLE DEFAULT NULL,
  `balik2lng` DOUBLE DEFAULT NULL,
  `dikemaskinipada` DOUBLE DEFAULT NULL,
  `masukjarakm` INT DEFAULT NULL,
  `masukakurasim` INT DEFAULT NULL,
  `balikjarakm` INT DEFAULT NULL,
  `balikakurasim` INT DEFAULT NULL,
  `masuk2jarakm` INT DEFAULT NULL,
  `masuk2akurasim` INT DEFAULT NULL,
  `balik2jarakm` INT DEFAULT NULL,
  `balik2akurasim` INT DEFAULT NULL,
  `status` VARCHAR(64) DEFAULT NULL,
  `sumber` VARCHAR(64) DEFAULT NULL,
  `disuntingoleh` VARCHAR(64) DEFAULT NULL,
  `masukip` VARCHAR(64) DEFAULT NULL,
  `balikip` VARCHAR(64) DEFAULT NULL,
  `masuk2ip` VARCHAR(64) DEFAULT NULL,
  `balik2ip` VARCHAR(64) DEFAULT NULL,
  `statuswaktu` VARCHAR(64) DEFAULT NULL,
  `extra_aj` VARCHAR(64) DEFAULT NULL,
  `sebabedit` VARCHAR(512) DEFAULT NULL,
  `ipsemakan` VARCHAR(255) DEFAULT NULL,
  PRIMARY KEY (`_row_id`),
  KEY idx_kehadiran_tarikh_emel (`tarikh`,`emel`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `tidak_hadir` (
  `_row_id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `_source_row` INT UNSIGNED NOT NULL DEFAULT 0,
  `id` VARCHAR(64) DEFAULT NULL,
  `emel` VARCHAR(64) DEFAULT NULL,
  `nama` VARCHAR(64) DEFAULT NULL,
  `kategori` VARCHAR(64) DEFAULT NULL,
  `jenis` VARCHAR(64) DEFAULT NULL,
  `status` VARCHAR(64) DEFAULT NULL,
  `disemakoleh` VARCHAR(64) DEFAULT NULL,
  `mod` VARCHAR(64) DEFAULT NULL,
  `masamula` VARCHAR(64) DEFAULT NULL,
  `masaakhir` VARCHAR(64) DEFAULT NULL,
  `jawatan` VARCHAR(64) DEFAULT NULL,
  `dihantarpada` DOUBLE DEFAULT NULL,
  `disemakpada` DOUBLE DEFAULT NULL,
  `dikemaskinipada` DOUBLE DEFAULT NULL,
  `tarikhmula` INT DEFAULT NULL,
  `tarikhakhir` INT DEFAULT NULL,
  `catatan` VARCHAR(512) DEFAULT NULL,
  `ulasanpengetua` VARCHAR(128) DEFAULT NULL,
  PRIMARY KEY (`_row_id`),
  KEY idx_th_emel (`emel`),
  KEY idx_th_id (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `semakan_waktu` (
  `_row_id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `_source_row` INT UNSIGNED NOT NULL DEFAULT 0,
  `id` VARCHAR(64) DEFAULT NULL,
  `emel` VARCHAR(64) DEFAULT NULL,
  `nama` VARCHAR(64) DEFAULT NULL,
  `jawatan` VARCHAR(64) DEFAULT NULL,
  `kategori` VARCHAR(64) DEFAULT NULL,
  `jenis` VARCHAR(64) DEFAULT NULL,
  `statussemakan` VARCHAR(64) DEFAULT NULL,
  `disemakoleh` VARCHAR(64) DEFAULT NULL,
  `namapelulus` VARCHAR(64) DEFAULT NULL,
  `diciptapada` DOUBLE DEFAULT NULL,
  `tarikh` DATE DEFAULT NULL,
  `sesi` INT DEFAULT NULL,
  `wakturekod` DOUBLE DEFAULT NULL,
  `wakturujukan` DOUBLE DEFAULT NULL,
  `disemakpada` DOUBLE DEFAULT NULL,
  `ulasan` VARCHAR(128) DEFAULT NULL,
  PRIMARY KEY (`_row_id`),
  KEY idx_semakan_tarikh (`tarikh`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `tetapan` (
  `_row_id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `_source_row` INT UNSIGNED NOT NULL DEFAULT 0,
  `kunci` VARCHAR(64) DEFAULT NULL,
  `nilai` TEXT DEFAULT NULL,
  `keterangan` VARCHAR(255) DEFAULT NULL,
  PRIMARY KEY (`_row_id`),
  KEY idx_tetapan_kunci (`kunci`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `audit` (
  `_row_id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `_source_row` INT UNSIGNED NOT NULL DEFAULT 0,
  `masa` DATETIME(6) NOT NULL,
  `pelaku` VARCHAR(128) NOT NULL,
  `tindakan` VARCHAR(128) NOT NULL,
  `sasaran` VARCHAR(255) NOT NULL,
  `butiran` TEXT DEFAULT NULL,
  PRIMARY KEY (`_row_id`),
  KEY ix_audit_masa (`masa`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `cuti_umum` (
  `tarikh` DATE NOT NULL,
  `nama` VARCHAR(160) NOT NULL,
  `jenis` VARCHAR(32) NOT NULL DEFAULT 'MANUAL',
  `sumber` VARCHAR(32) NOT NULL DEFAULT 'ADMIN',
  `aktif` TINYINT NOT NULL DEFAULT 1,
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`tarikh`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `web_auth` (
  `email` VARCHAR(128) NOT NULL,
  `pin_hash` VARCHAR(255) NOT NULL,
  `must_change_pin` TINYINT NOT NULL DEFAULT 0,
  `attempts` INT NOT NULL DEFAULT 0,
  `locked_until` DATETIME DEFAULT NULL,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`email`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `web_sessions` (
  `token_hash` CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  `email` VARCHAR(128) NOT NULL,
  `expires_at` DATETIME NOT NULL,
  `created_at` DATETIME NOT NULL,
  PRIMARY KEY (`token_hash`),
  KEY ix_web_sessions_email (`email`),
  KEY ix_web_sessions_expire (`expires_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `web_setup_state` (
  `id` TINYINT UNSIGNED NOT NULL,
  `installed` TINYINT NOT NULL DEFAULT 0,
  `installed_at` DATETIME DEFAULT NULL,
  `installed_by` VARCHAR(128) DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `ek_email_outbox` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `dedupe_key` CHAR(64) CHARACTER SET ascii COLLATE ascii_general_ci NOT NULL,
  `recipient` VARCHAR(254) NOT NULL,
  `subject` VARCHAR(180) NOT NULL,
  `body_text` TEXT NOT NULL,
  `body_html` MEDIUMTEXT DEFAULT NULL,
  `status` ENUM('pending','sending','retry','sent','dead') NOT NULL DEFAULT 'pending',
  `attempts` TINYINT UNSIGNED NOT NULL DEFAULT 0,
  `next_attempt_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `claimed_at` DATETIME DEFAULT NULL,
  `sent_at` DATETIME DEFAULT NULL,
  `last_error` VARCHAR(250) DEFAULT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY uq_ek_email_dedupe (`dedupe_key`),
  KEY ix_ek_email_ready (`status`,`next_attempt_at`,`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `ek_pin_recovery` (
  `email` VARCHAR(254) NOT NULL,
  `code_hash` VARCHAR(255) NOT NULL,
  `requested_at` DATETIME NOT NULL,
  `expires_at` DATETIME NOT NULL,
  `attempts` TINYINT UNSIGNED NOT NULL DEFAULT 0,
  `day_key` DATE NOT NULL,
  `day_count` TINYINT UNSIGNED NOT NULL DEFAULT 1,
  `request_ip_hash` CHAR(64) CHARACTER SET ascii COLLATE ascii_general_ci DEFAULT NULL,
  PRIMARY KEY (`email`),
  KEY ix_pin_recovery_expires (`expires_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT IGNORE INTO web_setup_state (id,installed) VALUES (1,0);
