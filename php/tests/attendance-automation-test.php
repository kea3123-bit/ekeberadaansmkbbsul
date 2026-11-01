<?php
declare(strict_types=1);
date_default_timezone_set('Asia/Kuala_Lumpur');
$GLOBALS['clock']='10:15';$GLOBALS['requests']=[];$GLOBALS['emailStatus']='pending';$GLOBALS['punch']=null;$GLOBALS['executed']=[];$GLOBALS['queued']=[];
function settings_raw():array{return ['SYSTEM_MODE'=>'REAL','ABSENT_AFTER'=>'10:00'];}
function today():string{return '2026-11-01';}
function now_myt():string{return '2026-11-01 '.$GLOBALS['clock'].':00';}
function mysql_school_day(string $date,array $s,?array $h=null):bool{return true;}
function mysql_active_requests_on(string $date):array{return $GLOBALS['requests'];}
function time_text($x):string{return (string)$x;}
function excel_number($x):float{return 123.5;}
function rows(string $sql,array $args=[]):array {
  if(str_contains($sql,'FROM kehadiran'))return $GLOBALS['punch']?[$GLOBALS['punch']]:[];
  if(str_contains($sql,'FROM pengguna')&&str_contains($sql,'pentadbir'))
    return [['emel'=>'manager@example.com']];
  if(str_contains($sql,'FROM pengguna'))
    return [['emel'=>'staff@example.com','nama'=>'Staf','kategori'=>'PPP']];
  return [];
}
function one(string $sql,array $args=[]):?array {
  if(str_contains($sql,'GET_LOCK'))return ['locked'=>1];
  if(str_contains($sql,'FROM ek_email_outbox'))return ['status'=>$GLOBALS['emailStatus'],'attempts'=>$GLOBALS['emailStatus']==='sent'?1:0,'sent_at'=>$GLOBALS['emailStatus']==='sent'?'2026-11-01 03:20:00':null];
  return ['released'=>1];
}
class MockDb {private bool $tx=false;
  function beginTransaction():void{$this->tx=true;}
  function inTransaction():bool{return $this->tx;}
  function commit():void{$this->tx=false;}
  function rollBack():void{$this->tx=false;}
}
function db():MockDb {static $db;return $db??=new MockDb();}
function attendance_row(string $mail,string $date):?array{return $GLOBALS['punch'];}
function execute_sql(string $sql,array $args=[]):int{$GLOBALS['executed'][]=[$sql,$args];return 1;}
function enqueue_workspace_email(string $key,string $recipient,string $subject,string $msg):bool{
  $GLOBALS['queued'][]=$key.'|'.$recipient;return true;
}
require dirname(__DIR__).'/attendance_jobs.php';
function reset_case():void {
  $GLOBALS['requests']=[];$GLOBALS['punch']=null;$GLOBALS['queued']=[];$GLOBALS['executed']=[];
  $GLOBALS['emailStatus']='pending';$GLOBALS['clock']='10:15';
}
function expect_true(bool $x,string $msg):void{if(!$x)throw new RuntimeException($msg);}
reset_case();$GLOBALS['clock']='09:45';
expect_true(run_mysql_attendance_jobs()['marked']===0,'No early absence');
reset_case();expect_true(run_mysql_attendance_jobs()['marked']===1,'Missing absence after cutoff');
reset_case();$GLOBALS['punch']=['emel'=>'staff@example.com','masuk'=>'2026-11-01 07:15','status'=>'HADIR'];
expect_true(run_mysql_attendance_jobs()['marked']===0,'Punch should prevent absence');
reset_case();$GLOBALS['requests']=['staff@example.com'=>[['mod'=>'KEBERADAAN','status'=>'DILULUSKAN','masaakhir'=>'11:00']]];
expect_true(run_mysql_attendance_jobs()['marked']===0,'Presence before end should prevent absence');
reset_case();$GLOBALS['clock']='11:20';
$GLOBALS['requests']=['staff@example.com'=>[['mod'=>'KEBERADAAN','status'=>'DILULUSKAN','masaakhir'=>'11:00']]];
expect_true(run_mysql_attendance_jobs()['marked']===0,'Do not finalize before admin mail sent');
expect_true(count($GLOBALS['queued'])===1,'Presence alert should be queued');
$GLOBALS['emailStatus']='sent';
expect_true(run_mysql_attendance_jobs()['marked']===1,'Finalize presence after email confirmed');
reset_case();$GLOBALS['clock']='11:20';
$GLOBALS['requests']=['staff@example.com'=>[['mod'=>'KEBERADAAN','status'=>'MENUNGGU','masaakhir'=>'11:00']]];
expect_true(run_mysql_attendance_jobs()['marked']===0,'Pending presence must not become absent');
echo "MYSQL_AUTO_ABSENCE_TESTS_OK\n";
