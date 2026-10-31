-- Safe, additive MySQL migration for temporary 1-week self-service PIN recovery.
-- Does NOT drop or truncate anything. web_auth, pengguna, web_sessions,
-- kehadiran, ek_email_outbox and existing PIN hashes are preserved.
CREATE TABLE IF NOT EXISTS ek_pin_recovery (
  email VARCHAR(254) NOT NULL,
  code_hash VARCHAR(255) NOT NULL,
  requested_at DATETIME NOT NULL,
  expires_at DATETIME NOT NULL,
  attempts TINYINT UNSIGNED NOT NULL DEFAULT 0,
  day_key DATE NOT NULL,
  day_count TINYINT UNSIGNED NOT NULL DEFAULT 1,
  request_ip_hash CHAR(64) CHARACTER SET ascii COLLATE ascii_general_ci DEFAULT NULL,
  PRIMARY KEY (email),
  KEY ix_pin_recovery_expires (expires_at),
  KEY ix_pin_recovery_ip (request_ip_hash,requested_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
