<?php
declare(strict_types=1);
// No network or live MySQL: direct temporary self-reset regression.
class PinTestDb {
  private bool $transaction=false;
  function beginTransaction():void{$this->transaction=true;}
  function inTransaction():bool{return $this->transaction;}
  function commit():void{$this->transaction=false;}
  function rollBack():void{$this->transaction=false;}
}
$testDb=new PinTestDb();
$ledger=null;$savedHash='';$revoked=0;$legacyCleared=false;$audits=0;
$_SERVER['REMOTE_ADDR']='192.0.2.31';
function db(){global $testDb;return $testDb;}
function user_by_email($email,$active=true){
  return $email==='staff@example.test'?['emel'=>$email,'nama'=>'Staff','aktif'=>1]:null;
}
function one($sql,$args=[]){
  global $ledger;
  if(strpos($sql,'COUNT(*) AS n')!==false)return ['n'=>0];
  if(strpos($sql,'FROM ek_pin_recovery')!==false)return $ledger;
  throw new RuntimeException('Unexpected SQL: '.$sql);
}
function execute_sql($sql,$args=[]){
  global $ledger,$savedHash,$revoked,$legacyCleared;
  if(strpos($sql,'INSERT INTO ek_pin_recovery')!==false){
    $ledger=[
      'requested_at'=>gmdate('Y-m-d H:i:s'),
      'day_key'=>gmdate('Y-m-d'),'day_count'=>$args[2],
      'code_hash'=>$args[1]
    ];
  }elseif(strpos($sql,'INSERT INTO web_auth')!==false){
    $savedHash=$args[1];
  }elseif(strpos($sql,'DELETE FROM web_sessions')!==false){
    $revoked++;
  }elseif(strpos($sql,'UPDATE pengguna')!==false){
    $legacyCleared=true;
  }else throw new RuntimeException('Unexpected SQL: '.$sql);
  return 1;
}
function audit_event($email,$action,$target,$details=''){global $audits;$audits++;}
function create_session($u){return ['ok'=>true,'token'=>'fake-token','deviceToken'=>'fake-token','boot'=>['user'=>['email'=>$u['emel']]]];}
function enqueue_workspace_email(){throw new RuntimeException('No email should ever be called');}
require_once dirname(__DIR__).'/pin_recovery.php';
function check($ok,$desc){if(!$ok)throw new RuntimeException($desc);}
check(pin_recovery_public_status()['requiresEmailCode']===false,'OTP must be disabled');
check(pin_recovery_public_status()['pinLength']===6,'PIN length must be 6');
check(pin_recovery_public_status()['endsAt']==='2026-11-07T23:59:59+08:00','Expiry required');
if(pin_recovery_available()){
  try{
    pin_recovery_confirm('staff@example.test','12345','12345');
    throw new RuntimeException('Invalid PIN accepted');
  }catch(InvalidArgumentException $e){check(strpos($e->getMessage(),'6 digit')!==false,'Incorrect PIN validation');}
  try{
    pin_recovery_confirm('staff@example.test','123456','654321');
    throw new RuntimeException('Mismatched PIN accepted');
  }catch(InvalidArgumentException $e){check(strpos($e->getMessage(),'sepadan')!==false,'Mismatch check broken');}
  $result=pin_recovery_confirm('staff@example.test','654321','654321');
  check(($result['ok']??false)===true,'Session was not created');
  check(password_verify('654321',$savedHash),'New PIN is not hashed correctly');
  check($revoked===1,'Old sessions not revoked');
  check($legacyCleared===true,'Legacy PIN fallback still enabled');
  check($ledger!==null && $ledger['day_count']===1,'Rate limit not tracked');
  check($audits===1,'Reset was not audited');
  try{
    pin_recovery_confirm('staff@example.test','654321','654321');
    throw new RuntimeException('Rapid repeat accepted');
  }catch(RuntimeException $e){check(strpos($e->getMessage(),'satu minit')!==false,'Cooldown missing');}
  echo "PASS: direct six-digit PIN reset, automatic session, no email, rate limit and 7-day expiry\n";
}else{
  echo "PASS: direct recovery disabled outside 2026-10-31 through 2026-11-07\n";
}
