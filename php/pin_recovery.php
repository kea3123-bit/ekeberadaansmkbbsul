<?php
declare(strict_types=1);
/**
 * Temporary one-week direct PIN setup (user-requested).
 * NO email code, NO email link, NO notification transport in the reset path.
 * Server-enforced expiry: 2026-11-07 23:59:59 Asia/Kuala_Lumpur.
 * Rate-limited and audited. Does not change attendance records or other users.
 */
function pin_recovery_available(): bool {
    $now=new DateTimeImmutable('now',new DateTimeZone('Asia/Kuala_Lumpur'));
    return $now>=new DateTimeImmutable('2026-10-31 00:00:00',new DateTimeZone('Asia/Kuala_Lumpur'))
        && $now<=new DateTimeImmutable('2026-11-07 23:59:59',new DateTimeZone('Asia/Kuala_Lumpur'));
}
function pin_recovery_public_status():array {
    return ['enabled'=>pin_recovery_available(),'endsAt'=>'2026-11-07T23:59:59+08:00',
            'requiresEmailCode'=>false,'pinLength'=>6];
}
function pin_recovery_normalize_email($raw):string {
    $email=strtolower(trim((string)$raw));
    if(strlen($email)>254||!filter_var($email,FILTER_VALIDATE_EMAIL))
        throw new InvalidArgumentException('Masukkan alamat emel DELIMa yang sah.');
    return $email;
}
/** Legacy endpoint must not send OTP mail anymore. */
function pin_recovery_request($rawEmail):array {
    if(!pin_recovery_available())
        throw new RuntimeException('Tempoh reset PIN sementara telah tamat.');
    throw new RuntimeException('Kod pengesahan emel sudah dibuang. Refresh aplikasi untuk terus mencipta PIN baharu.');
}
/** Public reset operation: email + two matching six-digit PIN fields. */
function pin_recovery_confirm($rawEmail,$rawPin,$rawConfirm):array {
    if(!pin_recovery_available())
        throw new RuntimeException('Tempoh reset PIN sementara telah tamat.');
    $email=pin_recovery_normalize_email($rawEmail);
    $pin=(string)$rawPin;$confirm=(string)$rawConfirm;
    if(!preg_match('/^[0-9]{6}$/D',$pin)||!hash_equals($pin,$confirm))
        throw new InvalidArgumentException('PIN baharu mesti 6 digit dan kedua-duanya sepadan.');
    $u=user_by_email($email);
    if(!$u)throw new RuntimeException('Akaun tidak dijumpai atau tidak aktif.');
    // Only moderate abusive request volume during this exceptional temporary period.
    $ipHash=hash('sha256',(string)($_SERVER['REMOTE_ADDR']??''));
    $ipRequests=one('SELECT COUNT(*) AS n FROM ek_pin_recovery
         WHERE request_ip_hash=? AND requested_at>DATE_SUB(UTC_TIMESTAMP(),INTERVAL 1 HOUR)',[$ipHash]);
    if((int)($ipRequests['n']??0)>=150)
        throw new RuntimeException('Terlalu banyak permintaan daripada rangkaian ini. Cuba kemudian.');
    db()->beginTransaction();
    try {
        $prior=one('SELECT requested_at,day_key,day_count FROM ek_pin_recovery WHERE email=? FOR UPDATE',[$email]);
        if($prior){
            $last=strtotime((string)$prior['requested_at'].' UTC');
            if($last!==false&&time()-$last<60)
                throw new RuntimeException('PIN baru ditetapkan. Cuba sekali lagi selepas satu minit.');
            if((string)$prior['day_key']===gmdate('Y-m-d')&&(int)$prior['day_count']>=5)
                throw new RuntimeException('Had reset PIN harian telah dicapai. Cuba esok.');
        }
        $count=$prior&&(string)$prior['day_key']===gmdate('Y-m-d')?(int)$prior['day_count']+1:1;
        // The original OTP table is retained only as an abuse-control ledger:
        // no OTP is generated, sent, stored, or checked.
        execute_sql('INSERT INTO ek_pin_recovery
             (email,code_hash,requested_at,expires_at,attempts,day_key,day_count,request_ip_hash)
             VALUES (?, ?, UTC_TIMESTAMP(),UTC_TIMESTAMP(),0,UTC_DATE(),?,?)
             ON DUPLICATE KEY UPDATE code_hash=VALUES(code_hash),
             requested_at=VALUES(requested_at),expires_at=VALUES(expires_at),
             attempts=0,day_key=VALUES(day_key),day_count=VALUES(day_count),
             request_ip_hash=VALUES(request_ip_hash)',
             [$email,hash('sha256',random_bytes(32)),$count,$ipHash]);
        execute_sql('INSERT INTO web_auth (email,pin_hash,must_change_pin,attempts,locked_until)
             VALUES (?,?,0,0,NULL) ON DUPLICATE KEY UPDATE pin_hash=VALUES(pin_hash),
             must_change_pin=0,attempts=0,locked_until=NULL',
             [$email,password_hash($pin,PASSWORD_DEFAULT)]);
        execute_sql('DELETE FROM web_sessions WHERE email=?',[$email]);
        execute_sql("UPDATE pengguna SET passwordsalt='',passwordhash='',authtype='PHP_PIN_V1',
             wajibtukarpassword=0 WHERE emel=?",[$email]);
        db()->commit();
    }catch(Throwable $e){
        if(db()->inTransaction())db()->rollBack();
        throw $e;
    }
    audit_event($email,'RESET_PIN_SEMINGGU',$email,'Penetapan PIN terus; tanpa kod emel; sesi lama dibatalkan.');
    return create_session($u);
}
