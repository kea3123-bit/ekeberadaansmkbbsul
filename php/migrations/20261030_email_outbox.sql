-- eKeberadaan: additive MySQL outbox migration (NO resets or data deletion).
-- Run once in the SAME database used by php/config.local.php.
-- Email sending is a separate cPanel cron process, never inline with login/punch.
CREATE TABLE IF NOT EXISTS ek_email_outbox (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  dedupe_key CHAR(64) CHARACTER SET ascii COLLATE ascii_general_ci NOT NULL,
  recipient VARCHAR(254) NOT NULL,
  subject VARCHAR(180) NOT NULL,
  body_text TEXT NOT NULL,
  body_html MEDIUMTEXT NULL,
  status ENUM('pending','sending','retry','sent','dead') NOT NULL DEFAULT 'pending',
  attempts TINYINT UNSIGNED NOT NULL DEFAULT 0,
  next_attempt_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  claimed_at DATETIME NULL,
  sent_at DATETIME NULL,
  last_error VARCHAR(250) NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY(id),
  UNIQUE KEY uq_ek_email_dedupe (dedupe_key),
  KEY ix_ek_email_ready (status,next_attempt_at,id),
  KEY ix_ek_email_claimed (status,claimed_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
