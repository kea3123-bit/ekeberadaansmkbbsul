<?php
declare(strict_types=1);
date_default_timezone_set('Asia/Kuala_Lumpur');
function valid_day(string $d):string{return $d;}
function date_key($d):string{return is_numeric($d)?gmdate('Y-m-d',(int)round(((float)$d-25569)*86400)):substr((string)$d,0,10);}
function time_text($v):string{return (string)$v;}
function schedule(array $u,array $s):array{return ['s1In'=>$s['DEFAULT_S1_IN']??'07:30'];}
function settings_raw():array{return ['WORKING_DAYS'=>'SUN,MON,TUE,WED,THU','SYSTEM_START_DATE'=>'2026-09-01'];}
function public_holidays_safe(?string $a=null,?string $b=null):array{return [['tarikh'=>'2026-11-02']];}
$GLOBALS['calls']=[];$GLOBALS['queued']=[];
function rows(string $sql,array $args=[]):array{
    $GLOBALS['calls'][]=$sql;
    if(str_contains($sql,'FROM tidak_hadir'))return [
       ['emel'=>'a@example.com','tarikhmula'=>'2026-11-01','tarikhakhir'=>'2026-11-01',
        'masamula'=>'08:00','masaakhir'=>'11:00','status'=>'DILULUSKAN','mod'=>'KEBERADAAN']];
    if(str_contains($sql,'FROM kehadiran'))return [];
    if(str_contains($sql,'FROM pengguna'))return [
       ['emel'=>'a@example.com','nama'=>'A'],['emel'=>'b@example.com','nama'=>'B']];
    return [];
}
function enqueue_workspace_email(string $key,string $recipient,string $subject,string $text):bool {
    $GLOBALS['queued'][$key.'|'.$recipient]=true;return true;
}
function one(string $sql,array $args=[]):?array{return ['total'=>2,'masuk'=>1,'balik'=>1];}
require dirname(__DIR__).'/mail_schedule.php';
$s=settings_raw();
if(!mysql_school_day('2026-11-01',$s))throw new RuntimeException('Sunday should be working day');
if(mysql_school_day('2026-11-02',$s))throw new RuntimeException('Holiday should not be working day');
if(mysql_school_day('2026-11-06',$s))throw new RuntimeException('Friday should not be working day');
if(!mysql_request_exempts_punch(['mod'=>'KEBERADAAN','status'=>'DILULUSKAN',
  'masamula'=>'08:00','masaakhir'=>'11:00'],'09:00'))throw new RuntimeException('Active presence not exempt');
if(mysql_request_exempts_punch(['mod'=>'KEBERADAAN','status'=>'DILULUSKAN',
  'masamula'=>'08:00','masaakhir'=>'11:00'],'12:00'))throw new RuntimeException('Expired presence should not exempt');
queue_punch_reminders_mysql('2026-11-01','09:00');
if(isset($GLOBALS['queued']['punch-reminder:2026-11-01|a@example.com']))throw new RuntimeException('Presence false reminder');
if(!isset($GLOBALS['queued']['punch-reminder:2026-11-01|b@example.com']))throw new RuntimeException('Missing reminder');
$GLOBALS['queued']=[];
queue_punch_reminders_mysql('2026-11-01','12:00');
if(!isset($GLOBALS['queued']['punch-reminder:2026-11-01|a@example.com']))throw new RuntimeException('Expired presence should be eligible');
$GLOBALS['queued']=[];
queue_punch_reminders_mysql('2026-11-02','09:00');
if(count($GLOBALS['queued']))throw new RuntimeException('Public holiday should not send reminders');
echo "MYSQL_TRIGGER_CUTOVER_TESTS_OK\n";
