<?php
declare(strict_types=1);
/**
 * Temporary self-service PIN recovery.
 * Opens 2026-10-31 and permanently closes after 2026-11-07 23:59 MYT.
 * Identity proof is an 8-digit single-use code sent ONLY to the existing
 * account's registered DELIMa email through the asynchronous Workspace outbox.
 * Never changes an account when a code is requested or sent.
 */
function pin_recovery_available(): bool {
    $now=new DateTimeImmutable('now',new DateTimeZone('Asia/Kuala_Lumpur'));
    return $now >= new DateTimeImmutable('2026-10-31 00:00:00',new DateTimeZone('Asia/Kuala_Lumpur'))
        && $now <= new DateTimeImmutable('2026-11-07 23:59:59',new DateTimeZone('Asia/Kuala_Lumpur'));
}
function pin_recovery_public_status(): array {
    return ['enabled'=>pin_recovery_available(),'endsAt'=>'2026-11-07T23:59:59+08:00',
      'codeLength'=>8,'codeMinutes'=>30];
}
function pin_recovery_normalize_email($raw): string {
    $email=strtolower(trim((string)$raw));
    if(strlen($email)>254 || !filter_var($email,FILTER_VALIDATE_EMAIL)) {
        throw new InvalidArgumentException('Masukkan alamat emel DELIMa yang sah.');
    }
    return $email;
}
function pin_recovery_request($rawEmail): array {
    $status=pin_recovery_public_status();
    if(!$status['enabled'])throw new RuntimeException('Tempoh reset PIN kendiri telah tamat. Hubungi Pentadbir Sistem.');
    $email=pin_recovery_normalize_email($rawEmail);
    $generic=['ok'=>true,'message'=>'Jika emel itu berdaftar dan aktif, kod 8 digit akan dihantar ke emel DELIMa. Sila semak Inbox atau Spam. Kod sah selama 30 minit.'];
    $u=user_by_email($email);
    if(!$u)return $generic; // Never reveal whether an email exists.
    $ip=(string)($_SERVER['REMOTE_ADDR']??'');
    $ipHash=hash('sha256',$ip);
    try {
        require_once __DIR__.'/email_queue.php';
        // School networks share public IPs; permit up to 150 distinct account
        // requests per IP/hour, while limiting one account to 5 codes/day.
        $global=one("SELECT COUNT(*) AS n FROM ek_pin_recovery
          WHERE request_ip_hash=? AND requested_at>DATE_SUB(UTC_TIMESTAMP(), INTERVAL 1 HOUR)",[$ipHash]);
        if((int)($global['n']??0)>=150)return $generic;
        db()->beginTransaction();
        $row=one('SELECT requested_at,day_key,day_count FROM ek_pin_recovery WHERE email=? FOR UPDATE',[$email]);
        if($row) {
            $last=strtotime((string)$row['requested_at'].' UTC');
            if($last!==false && time()-$last < 120){db()->rollBack();return $generic;}
            if((string)$row['day_key']===gmdate('Y-m-d') && (int)$row['day_count']>=5) {
                db()->rollBack();return $generic;
            }
        }
        $code=(string)random_int(10000000,99999999);
        $hash=password_hash($code,PASSWORD_DEFAULT);
        $dayCount=$row && (string)$row['day_key']===gmdate('Y-m-d') ? (int)$row['day_count']+1 : 1;
        execute_sql('INSERT INTO ek_pin_recovery (email,code_hash,requested_at,expires_at,attempts,day_key,day_count,request_ip_hash)
          VALUES (?,?,UTC_TIMESTAMP(),DATE_ADD(UTC_TIMESTAMP(), INTERVAL 30 MINUTE),0,UTC_DATE(),?,?)
          ON DUPLICATE KEY UPDATE code_hash=VALUES(code_hash),requested_at=VALUES(requested_at),
          expires_at=VALUES(expires_at),attempts=0,day_key=VALUES(day_key),day_count=VALUES(day_count),
          request_ip_hash=VALUES(request_ip_hash)',[$email,$hash,$dayCount,$ipHash]);
        $body="Kod pengesahan reset PIN eKeberadaan: ".$code."\n\n".
          "Kod ini sah selama 30 minit dan boleh digunakan sekali sahaja.\n".
          "Jika anda tidak meminta kod ini, abaikan emel ini. Jangan kongsi kod dengan sesiapa.\n\n".
          "Halaman rasmi: https://kea3123-bit.github.io/ekeberadaansmkbbsul/";
        $queued=enqueue_workspace_email('pin-recovery:'.$email.':'.bin2hex(random_bytes(12)),
            $email,'eKeberadaan: Kod pengesahan PIN',$body);
        if(!$queued)throw new RuntimeException('Email outbox is not available');
        db()->commit();
    }catch(Throwable $e) {
        if(db()->inTransaction())db()->rollBack();
        error_log('[eKeberadaan PIN recovery] Request could not queue: '.get_class($e));
        // Do not tell an attacker whether an address is in the users table.
    }
    return $generic;
}
function pin_recovery_confirm($rawEmail,$rawCode,$rawPin,$rawConfirm): array {
    if(!pin_recovery_available())
        throw new RuntimeException('Tempoh reset PIN kendiri telah tamat.');
    $email=pin_recovery_normalize_email($rawEmail);
    $code=trim((string)$rawCode);
    $pin=(string)$rawPin;
    $confirm=(string)$rawConfirm;
    if(!preg_match('/^[0-9]{8}$/D',$code))
        throw new InvalidArgumentException('Masukkan kod 8 digit daripada emel.');
    if(!preg_match('/^[0-9]{6}$/D',$pin) || !hash_equals($pin,$confirm))
        throw new InvalidArgumentException('PIN baharu mesti 6 digit dan kedua-duanya sepadan.');
    $u=user_by_email($email);
    if(!$u)throw new RuntimeException('Kod tidak sah atau telah tamat. Mohon kod baharu.');
    db()->beginTransaction();
    try {
        $record=one('SELECT code_hash,expires_at,attempts FROM ek_pin_recovery WHERE email=? FOR UPDATE',[$email]);
        if(!$record || (int)$record['attempts']>=5 ||
            strtotime((string)$record['expires_at'].' UTC')<=time()) {
            throw new RuntimeException('Kod tidak sah atau telah tamat. Mohon kod baharu.');
        }
        if(!password_verify($code,(string)$record['code_hash'])) {
            execute_sql('UPDATE ek_pin_recovery SET attempts=attempts+1 WHERE email=?',[$email]);
            db()->commit(); // Commit failed attempt count.
            throw new RuntimeException('Kod tidak sah atau telah tamat. Mohon kod baharu.');
        }
        // Code consumed in the same transaction as replacing the PIN.
        execute_sql('DELETE FROM ek_pin_recovery WHERE email=?',[$email]);
        execute_sql('INSERT INTO web_auth (email,pin_hash,must_change_pin,attempts,locked_until)
            VALUES (?,?,0,0,NULL)
            ON DUPLICATE KEY UPDATE pin_hash=VALUES(pin_hash),must_change_pin=0,
            attempts=0,locked_until=NULL',
            [$email,password_hash($pin,PASSWORD_DEFAULT)]);
        // Reject all existing (possibly stolen) session/device tokens.
        execute_sql('DELETE FROM web_sessions WHERE email=?',[$email]);
        // No future fallback to the original Sheets PIN after recovery.
        execute_sql("UPDATE pengguna SET passwordsalt='',passwordhash='',authtype='PHP_PIN_V1',
          wajibtukarpassword=0 WHERE emel=?",[$email]);
        db()->commit();
    }catch(Throwable $e) {
        if(db()->inTransaction())db()->rollBack();
        throw $e;
    }
    audit_event($email,'RESET_PIN_KENDIRI',$email,'Disahkan melalui kod emel; semua sesi lama dibatalkan.');
    return create_session($u);
}
