-- Additive migration: no DROP, TRUNCATE or PIN resets.
CREATE TABLE IF NOT EXISTS ek_pin_link_recovery (
  email VARCHAR(254) NOT NULL,
  token_hash CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  pin_hash VARCHAR(255) NOT NULL,
  requested_at DATETIME NOT NULL,
  expires_at DATETIME NOT NULL,
  day_key DATE NOT NULL,
  day_count TINYINT UNSIGNED NOT NULL DEFAULT 1,
  request_ip_hash CHAR(64) CHARACTER SET ascii COLLATE ascii_general_ci DEFAULT NULL,
  PRIMARY KEY (email),
  KEY ix_link_recovery_ip (request_ip_hash,requested_at),
  KEY ix_link_recovery_expiry (expires_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
