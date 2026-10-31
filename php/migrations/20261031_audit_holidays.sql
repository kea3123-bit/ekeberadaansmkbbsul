-- ADDITIVE only. Import once in phpMyAdmin after database backup.
-- Cuti umum is referenced by the MySQL monthly punch-card API.
-- Does not DROP/TRUNCATE/modify existing attendance, PIN, sessions or email.
CREATE TABLE IF NOT EXISTS cuti_umum (
  tarikh DATE NOT NULL,
  nama VARCHAR(160) NOT NULL,
  jenis VARCHAR(32) NOT NULL DEFAULT 'MANUAL',
  sumber VARCHAR(32) NOT NULL DEFAULT 'ADMIN',
  aktif TINYINT(1) NOT NULL DEFAULT 1,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (tarikh)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
