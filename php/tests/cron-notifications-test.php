<?php
declare(strict_types=1);
date_default_timezone_set('Asia/Kuala_Lumpur');
$GLOBALS['attendance']=[
 ['_row_id'=>1,'emel'=>'staff@example.com','tarikh'=>'2026-11-01','masuk'=>'2026-11-01 07:45:00',
  'balik'=>'2026-11-01 15:00:00','status'=>'LEWAT / BALIK AWAL','statuswaktu'=>'LEWAT|BALIK AWAL','sumber'=>'PHP_MYSQL']
];
$GLOBALS['savedReviews']=[];$GLOBALS['mail']=[];$GLOBALS['dead']=0;$GLOBALS['backlog']=0;$GLOBALS['settings']=['SYSTEM_MODE'=>'REAL','SYSTEM_START_DATE'=>'2026-09-01'];
function settings_raw():array{return $GLOBALS['settings'];}
function date_key($v):string{return substr((string)$v,0,10);}
function today():string{return '2026-11-01';}
function now_myt():string{return '2026-11-01 15:01:00';}
function time_text($v):string{return strlen((string)$v)>5?substr((string)$v,11,5):(string)$v;}
function excel_number($v):float{return 55555.1234;}
function schedule(array $u,array $s):array{return ['s1In'=>'07:30','s1Out'=>'16:30','s2In'=>'11:30','s2Out'=>'15:00'];}
function rows(string $sql,array $args=[]):array {
  if(str_contains($sql,'FROM pengguna') && str_contains($sql,'pentadbir=1'))return [['emel'=>'admin@example.com']];
  if(str_contains($sql,'FROM pengguna'))return [
   ['emel'=>'staff@example.com','nama'=>'STAFF','jawatan'=>'GURU','kategori'=>'PPP','pentadbir'=>0,'aktif'=>1],
   ['emel'=>'admin@example.com','nama'=>'ADMIN','kategori'=>'Pengurusan','pentadbir'=>1,'aktif'=>1]];
  if(str_contains($sql,'FROM kehadiran'))return $args[0]==='2026-11-01'?$GLOBALS['attendance']:[];
  return [];
}
function one(string $sql,array $args=[]):?array {
  if(str_contains($sql,'GET_LOCK'))return ['locked'=>1];
  if(str_contains($sql,'FROM semakan_waktu')){
    foreach($GLOBALS['savedReviews'] as $r)if($r['emel']===$args[0]&&$r['tarikh']===$args[1]&&$r['jenis']===$args[2])
      return ['id'=>$r['id'],'statussemakan'=>$r['statussemakan']];
    return null;
  }
  if(str_contains($sql,"status='dead'"))return ['n'=>$GLOBALS['dead']];
  if(str_contains($sql,"status IN ('pending','retry')"))return ['n'=>$GLOBALS['backlog']];
  return ['released'=>1];
}
function execute_sql(string $sql,array $args=[]):int{
  if(str_contains($sql,'INSERT INTO semakan_waktu')){
    // id,created,date,email,name,job,category,type,session,...
    $GLOBALS['savedReviews'][]=['id'=>$args[0],'tarikh'=>$args[2],'emel'=>$args[3],
      'jenis'=>$args[7],'statussemakan'=>'BELUM DIAMBIL MAKLUM'];
    return 1;
  }
  throw new RuntimeException('Unexpected SQL write: '.$sql);
}
function enqueue_workspace_email(string $event,string $recipient,string $title,string $body):bool{
  $GLOBALS['mail'][$event.'|'.$recipient]=[$title,$body];return true;
}
require dirname(__DIR__).'/cron_notifications.php';
function check(bool $yes,string $msg):void {if(!$yes)throw new RuntimeException($msg);}
$r=mysql_time_review_jobs();
check($r['created']===2,'Must create separate late and early reviews');
check(count($GLOBALS['savedReviews'])===2,'Rows not persisted');
check(count($GLOBALS['mail'])===2,'Admin should receive two deduplicated notifications');
$r=mysql_time_review_jobs();
check($r['created']===0&&count($GLOBALS['mail'])===2,'Repeated cron duplicated reviews or mails');
$GLOBALS['attendance'][0]['sumber']='ADMIN_MANUAL';
$r=mysql_time_review_jobs();
check($r['created']===0,'Manual correction must be excluded');
// Check the optional second session independently of first-session flags.
$GLOBALS['attendance'][0]['sumber']='PHP_MYSQL';
$GLOBALS['attendance'][0]['status']='HADIR';
$GLOBALS['attendance'][0]['statuswaktu']='';
$GLOBALS['attendance'][0]['masuk2']='11:45';
$GLOBALS['attendance'][0]['balik2']='14:45';
$GLOBALS['savedReviews']=[];$GLOBALS['mail']=[];
$r=mysql_time_review_jobs();
check($r['created']===2,'Session 2 with configured references should create two reviews');
check(count($GLOBALS['mail'])===2,'Session 2 should notify admins once for each exception');
$r=mysql_time_review_jobs();
check($r['created']===0,'Session 2 retry created duplicates');
$GLOBALS['attendance'][0]['masuk2']='';$GLOBALS['attendance'][0]['balik2']='';
$GLOBALS['dead']=0;$GLOBALS['backlog']=10;$GLOBALS['mail']=[];
$r=mysql_dead_mail_monitor();
check($r['queued']===0,'No alert for a small backlog');
$GLOBALS['dead']=4;
$r=mysql_dead_mail_monitor();
check($r['dead']===4 && $r['queued']===1 && count($GLOBALS['mail'])===1,'Dead mail monitor should alert admin');
$r=mysql_dead_mail_monitor();
check(count($GLOBALS['mail'])===1,'Dead mail alert must be deduplicated by date');
$GLOBALS['settings']['EMAIL_NOTIFICATIONS_ENABLED']='FALSE';$GLOBALS['mail']=[];
$r=mysql_dead_mail_monitor();
check($r['queued']===0,'Monitor must respect disabled outbound notifications');
echo "MYSQL_CRON_NOTIFICATIONS_TESTS_OK\n";
