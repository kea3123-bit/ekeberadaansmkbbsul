-- eKeberadaan MySQL AUDIT FIX: additive runtime prerequisites only.
-- Safe on an existing live MySQL database; creates missing tables, no data reset.
CREATE TABLE IF NOT EXISTS audit (
  _row_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
  _source_row INT UNSIGNED NOT NULL DEFAULT 0,
  masa DATETIME(6) NOT NULL,
  pelaku VARCHAR(128) NOT NULL,
  tindakan VARCHAR(128) NOT NULL,
  sasaran VARCHAR(255) NOT NULL,
  butiran TEXT DEFAULT NULL,
  KEY ix_audit_masa (masa)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS cuti_umum (
  tarikh DATE NOT NULL PRIMARY KEY,
  nama VARCHAR(160) NOT NULL,
  jenis VARCHAR(32) NOT NULL DEFAULT 'MANUAL',
  sumber VARCHAR(32) NOT NULL DEFAULT 'ADMIN',
  aktif TINYINT(1) NOT NULL DEFAULT 1,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS ek_pin_recovery (
  email VARCHAR(254) NOT NULL PRIMARY KEY,
  code_hash VARCHAR(255) NOT NULL,
  requested_at DATETIME NOT NULL,
  expires_at DATETIME NOT NULL,
  attempts TINYINT UNSIGNED NOT NULL DEFAULT 0,
  day_key DATE NOT NULL,
  day_count TINYINT UNSIGNED NOT NULL DEFAULT 1,
  request_ip_hash CHAR(64) CHARACTER SET ascii COLLATE ascii_general_ci DEFAULT NULL,
  KEY ix_pin_recovery_expires (expires_at),
  KEY ix_pin_recovery_ip (request_ip_hash,requested_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS ek_email_outbox (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
  dedupe_key CHAR(64) CHARACTER SET ascii COLLATE ascii_general_ci NOT NULL,
  recipient VARCHAR(254) NOT NULL,
  subject VARCHAR(180) NOT NULL,
  body_text TEXT NOT NULL,
  body_html MEDIUMTEXT DEFAULT NULL,
  status ENUM('pending','sending','retry','sent','dead') NOT NULL DEFAULT 'pending',
  attempts TINYINT UNSIGNED NOT NULL DEFAULT 0,
  next_attempt_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  claimed_at DATETIME DEFAULT NULL,
  sent_at DATETIME DEFAULT NULL,
  last_error VARCHAR(250) DEFAULT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_ek_email_dedupe (dedupe_key),
  KEY ix_ek_email_ready (status,next_attempt_at,id),
  KEY ix_ek_email_claimed (status,claimed_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
