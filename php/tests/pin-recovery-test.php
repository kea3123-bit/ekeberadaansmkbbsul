<?php
declare(strict_types=1);
// Deterministic, database-free security regression for self-service PIN recovery.
class RecoveryTestDb {
    public $active=false;
    public function beginTransaction(){ $this->active=true; }
    public function commit(){ $this->active=false; }
    public function rollBack(){ $this->active=false; }
    public function inTransaction(){return $this->active;}
}
$db=new RecoveryTestDb();
$record=null;$outbox=[];$pinHash='';$sessionRevokes=0;$legacyCleared=false;
$knownEmail='staff@example.test';
function db(){global $db;return $db;}
function user_by_email($email,$active=true) {
    global $knownEmail;
    return $email===$knownEmail?['emel'=>$email,'aktif'=>1,'nama'=>'Staff']:null;
}
function one($query,$params=[]) {
    global $record;
    if(strpos($query,'COUNT(*) AS n')!==false)return ['n'=>0];
    if(strpos($query,'FROM ek_pin_recovery')!==false)return $record;
    throw new RuntimeException('Unexpected SELECT: '.$query);
}
function execute_sql($query,$params=[]) {
    global $record,$outbox,$pinHash,$sessionRevokes,$legacyCleared;
    if(strpos($query,'INSERT INTO ek_pin_recovery')!==false) {
        $record=['requested_at'=>gmdate('Y-m-d H:i:s'),
          'expires_at'=>gmdate('Y-m-d H:i:s',time()+1800),
          'code_hash'=>$params[1], 'attempts'=>0,'day_key'=>gmdate('Y-m-d'),'day_count'=>$params[2]];
    }elseif(strpos($query,'INSERT IGNORE INTO ek_email_outbox')!==false) {
        $outbox[]=$params;
    }elseif(strpos($query,'UPDATE ek_pin_recovery SET attempts')!==false) {
        $record['attempts']++;
    }elseif(strpos($query,'DELETE FROM ek_pin_recovery')!==false){
        $record=null;
    }elseif(strpos($query,'INSERT INTO web_auth')!==false) {
        $pinHash=$params[1];
    }elseif(strpos($query,'DELETE FROM web_sessions')!==false) {
        $sessionRevokes++;
    }elseif(strpos($query,'UPDATE pengguna')!==false) {
        $legacyCleared=true;
    }else throw new RuntimeException('Unexpected UPDATE: '.$query);
    return 1;
}
function create_session($u) { return ['ok'=>true,'token'=>'test-session','deviceToken'=>'test-session','boot'=>['user'=>['email'=>$u['emel']]]]; }
function audit_event($actor,$act,$target,$detail=''){}
require_once __DIR__.'/../pin_recovery.php';
function check($ok,$why){if(!$ok)throw new RuntimeException($why);}
check(pin_recovery_public_status()['codeLength']===8,'Expected 8-digit code');
check(pin_recovery_public_status()['codeMinutes']===30,'OTP TTL must be 30 minutes');
check(pin_recovery_public_status()['endsAt']==='2026-11-07T23:59:59+08:00','Disable deadline missing');
// CI may execute after the temporary window has closed: only exercise recovery
// when it is still enabled; the exact expiry assertion always runs.
if(pin_recovery_available()){
  $unknown=pin_recovery_request('unknown@example.test');
  check($unknown['ok']===true && count($outbox)===0,'Account enumeration or unexpected email');
  $_SERVER['REMOTE_ADDR']='192.0.2.44';
  $result=pin_recovery_request($knownEmail);
  check($result['ok']===true && count($outbox)===1,'Queued email expected');
  check($record!==null && strpos($record['code_hash'],'$2')===0,'Code must be hashed at rest');
  check(preg_match('/[0-9]{8}/',$outbox[0][3],$match)===1,'8-digit code absent from queued mail');
  $code=$match[0];
  check(!password_verify('00000000',$record['code_hash']),'Unrelated code accepted');
  pin_recovery_request($knownEmail);
  check(count($outbox)===1,'Cooldown must prevent repeated requests');
  try{pin_recovery_confirm($knownEmail,'00000000','654321','654321');throw new RuntimeException('Invalid code was accepted');}
  catch(RuntimeException $e){check(strpos($e->getMessage(),'Kod tidak sah')!==false,'Unexpected error');}
  check($record['attempts']===1,'Failed OTP attempt should persist');
  $res=pin_recovery_confirm($knownEmail,$code,'654321','654321');
  check($res['ok']===true && $record===null,'Code not consumed');
  check(password_verify('654321',$pinHash),'New PIN hash missing');
  check($sessionRevokes===1,'Old sessions not revoked');
  check($legacyCleared,'Old Sheets PIN migration fallback still active');
  echo "PASS: email proof, OTP hash, rate limit, single use, PIN update and session revocation\n";
}else echo "PASS: recovery is closed after deadline; temporary OTP tests skipped\n";
