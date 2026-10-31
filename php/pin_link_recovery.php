<?php
declare(strict_types=1);
/**
 * Temporary PIN reset without typing email codes.
 * Existing authenticated device: reset immediately.
 * Expired device: create PIN now, activate using a single-use email link.
 * Closes automatically 7 Nov 2026 23:59:59 MYT.
 */
require_once __DIR__.'/pin_recovery.php';
function pin_link_reset_apply(array $user,string $newHash):array {
    $email=strtolower(trim((string)$user['emel']));
    db()->beginTransaction();
    try {
        execute_sql('INSERT INTO web_auth (email,pin_hash,must_change_pin,attempts,locked_until)
            VALUES (?,?,0,0,NULL) ON DUPLICATE KEY UPDATE pin_hash=VALUES(pin_hash),
            must_change_pin=0,attempts=0,locked_until=NULL',[$email,$newHash]);
        execute_sql('DELETE FROM web_sessions WHERE email=?',[$email]);
        execute_sql("UPDATE pengguna SET passwordsalt='',passwordhash='',authtype='PHP_PIN_V1',wajibtukarpassword=0 WHERE emel=?",[$email]);
        execute_sql('DELETE FROM ek_pin_link_recovery WHERE email=?',[$email]);
        db()->commit();
    }catch(Throwable $e){
        if(db()->inTransaction())db()->rollBack();
        throw $e;
    }
    audit_event($email,'RESET_PIN_KENDIRI',$email,'Sesi sah atau pautan emel sekali guna');
    return create_session($user);
}
function pin_link_reset_begin($rawEmail,$rawPin,$rawConfirm,$rawDevice=''):array {
    if(!pin_recovery_available())throw new RuntimeException('Tempoh reset PIN sementara telah tamat.');
    $email=pin_recovery_normalize_email($rawEmail);
    $pin=(string)$rawPin;$confirm=(string)$rawConfirm;
    if(!preg_match('/^[0-9]{6}$/D',$pin) || !hash_equals($pin,$confirm))
        throw new InvalidArgumentException('PIN baharu mesti 6 digit dan kedua-duanya sepadan.');
    $user=user_by_email($email);
    if(!$user)throw new RuntimeException('Akaun tidak aktif atau tidak dijumpai.');
    $hash=password_hash($pin,PASSWORD_DEFAULT);
    $device=(string)$rawDevice;
    if($device!=='' && strlen($device)<=128){
        try {
            $trusted=require_user($device,false,false);
            if(hash_equals(strtolower((string)$trusted['emel']),$email)){
                return array_merge(['mode'=>'immediate'],pin_link_reset_apply($user,$hash));
            }
        }catch(Throwable $ignored){ /* Old/revoked tokens require email proof. */ }
    }
    // No authenticated browser session: prove DELIMa mailbox ownership by link.
    $generic=['ok'=>true,'mode'=>'email','message'=>'Jika akaun ini berdaftar, pautan pengesahan dihantar ke emel DELIMa. Klik pautan itu untuk aktifkan PIN baharu. Pautan sah 30 minit.'];
    $ipHash=hash('sha256',(string)($_SERVER['REMOTE_ADDR']??''));
    require_once __DIR__.'/email_queue.php';
    $token=bin2hex(random_bytes(32));
    $url='https://kea3123-bit.github.io/ekeberadaansmkbbsul/#pin-reset='.
        rawurlencode($token).'&email='.rawurlencode($email);
    try {
        $volume=one('SELECT COUNT(*) AS n FROM ek_pin_link_recovery
            WHERE request_ip_hash=? AND requested_at>DATE_SUB(UTC_TIMESTAMP(), INTERVAL 1 HOUR)',[$ipHash]);
        if((int)($volume['n']??0)>=150)return $generic;
        db()->beginTransaction();
        $prior=one('SELECT requested_at,day_key,day_count FROM ek_pin_link_recovery WHERE email=? FOR UPDATE',[$email]);
        if($prior) {
            $last=strtotime((string)$prior['requested_at'].' UTC');
            if($last!==false && time()-$last<120){db()->rollBack();return $generic;}
            if((string)$prior['day_key']===gmdate('Y-m-d') && (int)$prior['day_count']>=5){
                db()->rollBack();return $generic;
            }
        }
        $dayCount=$prior && (string)$prior['day_key']===gmdate('Y-m-d')?(int)$prior['day_count']+1:1;
        execute_sql('INSERT INTO ek_pin_link_recovery
            (email,token_hash,pin_hash,requested_at,expires_at,day_key,day_count,request_ip_hash)
            VALUES (?,?,?,UTC_TIMESTAMP(),DATE_ADD(UTC_TIMESTAMP(),INTERVAL 30 MINUTE),UTC_DATE(),?,?)
            ON DUPLICATE KEY UPDATE token_hash=VALUES(token_hash),pin_hash=VALUES(pin_hash),
              requested_at=VALUES(requested_at),expires_at=VALUES(expires_at),
              day_key=VALUES(day_key),day_count=VALUES(day_count),
              request_ip_hash=VALUES(request_ip_hash)',
            [$email,hash('sha256',$token),$hash,$dayCount,$ipHash]);
        $queued=enqueue_workspace_email('pin-link:'.$email.':'.bin2hex(random_bytes(12)),
            $email,'eKeberadaan: Aktifkan PIN baharu',
            "Klik pautan berikut untuk mengesahkan dan mengaktifkan PIN baharu:\n\n".$url.
            "\n\nPautan sah selama 30 minit, sekali guna sahaja. Jika bukan anda, abaikan emel ini. Jangan kongsi pautan.");
        if(!$queued)throw new RuntimeException('Email outbox unavailable');
        db()->commit();
    }catch(Throwable $e){
        if(db()->inTransaction())db()->rollBack();
        error_log('[eKeberadaan PIN link] Queue failed: '.get_class($e));
        throw new RuntimeException('Tidak dapat menghantar pautan pengesahan. Cuba semula kemudian.');
    }
    return $generic;
}
function pin_link_reset_activate($rawEmail,$rawToken):array {
    if(!pin_recovery_available())throw new RuntimeException('Tempoh reset PIN sementara telah tamat.');
    $email=pin_recovery_normalize_email($rawEmail);$token=(string)$rawToken;
    if(!preg_match('/^[a-f0-9]{64}$/D',$token))
        throw new RuntimeException('Pautan tidak sah atau telah tamat.');
    $user=user_by_email($email);
    if(!$user)throw new RuntimeException('Pautan tidak sah atau telah tamat.');
    db()->beginTransaction();
    try {
        $record=one('SELECT token_hash,pin_hash,expires_at FROM ek_pin_link_recovery WHERE email=? FOR UPDATE',[$email]);
        if(!$record || !hash_equals((string)$record['token_hash'],hash('sha256',$token)) ||
           strtotime((string)$record['expires_at'].' UTC')<=time())
            throw new RuntimeException('Pautan tidak sah atau telah tamat. Mohon semula dari Lupa PIN.');
        execute_sql('INSERT INTO web_auth (email,pin_hash,must_change_pin,attempts,locked_until)
            VALUES (?,?,0,0,NULL) ON DUPLICATE KEY UPDATE pin_hash=VALUES(pin_hash),
            must_change_pin=0,attempts=0,locked_until=NULL',
            [$email,(string)$record['pin_hash']]);
        execute_sql('DELETE FROM web_sessions WHERE email=?',[$email]);
        execute_sql("UPDATE pengguna SET passwordsalt='',passwordhash='',authtype='PHP_PIN_V1',wajibtukarpassword=0 WHERE emel=?",[$email]);
        execute_sql('DELETE FROM ek_pin_link_recovery WHERE email=?',[$email]);
        db()->commit();
    }catch(Throwable $e){
        if(db()->inTransaction())db()->rollBack();
        throw $e;
    }
    audit_event($email,'RESET_PIN_PAUTAN_EMEL',$email,'Pautan sekali guna disahkan');
    return create_session($user);
}
