<?php
declare(strict_types=1);
date_default_timezone_set('Asia/Kuala_Lumpur');
require dirname(__DIR__).'/time_exception_reasons.php';
function check_case(bool $condition,string $why):void{if(!$condition)throw new RuntimeException($why);}
function date_key($x):string{return substr((string)$x,0,10);}
function time_text($x):string{return substr((string)($x??''),11,5)?:substr((string)($x??''),0,5);}
function settings_raw():array{return [
  'SYSTEM_MODE'=>'REAL','THURSDAY_WBF_ENABLED'=>'TRUE','THURSDAY_WBF_IN_FROM'=>'07:30',
  'THURSDAY_WBF_IN_TO'=>'09:00','THURSDAY_WBF_OUT_FROM'=>'15:00',
  'THURSDAY_WBF_OUT_TO'=>'16:30','THURSDAY_WBF_DURATION_MINUTES'=>450];}
function schedule(array $u,array $s):array{return ['s1In'=>'07:30','s1Out'=>'16:30','s2In'=>'','s2Out'=>''];}
function today():string{return '2026-11-02';}
function now_myt():string{return '2026-11-02 10:25:00';}
function excel_number($t):float{return 46300.5;}
function audit_event($actor,$event,$id,$note=''):void{}
$akp=['emel'=>'a@example.test','nama'=>'A','jawatan'=>'Pembantu Tadbir','kategori'=>'AKP'];
$ppp=['emel'=>'b@example.test','nama'=>'B','jawatan'=>'Guru','kategori'=>'PPP'];
$wbf=['tarikh'=>'2026-10-29','masuk'=>'2026-10-29 07:18:00','balik'=>'2026-10-29 15:05:00','masuk2'=>null,'balik2'=>null,'sumber'=>'PHP_MYSQL'];
check_case(count(ek_reason_incidents($wbf,$akp,settings_raw()))===0,'AKP WBF 07:18 to 15:05 must not be Balik Awal');
check_case(count(ek_reason_incidents($wbf,$ppp,settings_raw()))===1,'PPP 15:05 must be Balik Awal');
$wbf['masuk2']='2026-10-29 11:45:00';
$wbf['balik2']='2026-10-29 17:00:00';
check_case(count(ek_reason_incidents($wbf,$ppp,settings_raw()))===0,'Final Sesi 2 OUT must supersede Sesi 1 OUT');
$day='2026-11-02';$event=[
 'tarikh'=>$day,'masuk'=>'2026-11-02 08:15:00','balik'=>'2026-11-02 16:35:00',
 'masuk2'=>null,'balik2'=>null,'sumber'=>'PHP_MYSQL'
];
check_case(ek_reason_incidents($event,$ppp,settings_raw())[0]['type']==='LEWAT','Actual late must be recognized');
$other=[['status'=>'DILULUSKAN','mode'=>'KEBERADAAN','startDate'=>$day,'endDate'=>$day,
    'startTime'=>'13:00','endTime'=>'15:00']];
$covered=[['status'=>'MENUNGGU','mode'=>'KEBERADAAN','startDate'=>$day,'endDate'=>$day,
    'startTime'=>'07:30','endTime'=>'08:30']];
check_case(!ek_reason_request_covers($other,$day,'07:30','08:15'),'Unrelated afternoon Keberadaan must not excuse morning late');
check_case(ek_reason_request_covers($covered,$day,'07:30','08:15'),'Pending matching Keberadaan must suppress the prompt');
$covered[0]['status']='DITOLAK';
check_case(!ek_reason_request_covers($covered,$day,'07:30','08:15'),'Rejected Keberadaan must not suppress prompt');
$leave=[['status'=>'DILULUSKAN','mode'=>'TIDAK_HADIR','startDate'=>$day,'endDate'=>$day]];
check_case(ek_reason_request_covers($leave,$day,'07:30','08:15'),'Same-day approved leave suppresses prompt');
$GLOBALS['attendance']=$event;
$GLOBALS['applications']=[];
$GLOBALS['storedReasons']=[];
$GLOBALS['writes']=[];
function all_absence_rows():array{return $GLOBALS['applications'];}
function rows(string $sql,array $args=[]):array{
  if(str_contains($sql,'FROM kehadiran'))return [$GLOBALS['attendance']];
  throw new RuntimeException('Unexpected SQL: '.$sql);
}
function one(string $sql,array $args=[]):?array{
  if(str_contains($sql,'GET_LOCK'))return ['locked'=>1];
  if(str_contains($sql,'RELEASE_LOCK'))return ['released'=>1];
  if(str_contains($sql,'FROM semakan_waktu')){
    $id='SW-MYSQL-20261102-'.substr(hash('sha256','b@example.test|2026-11-02|LEWAT|1'),0,18);
    if(isset($GLOBALS['storedReasons'][$id])){
      return ['id'=>$id,'tarikh'=>'2026-11-02','jenis'=>'LEWAT','sesi'=>1,
        'emel'=>'b@example.test','sebabpengguna'=>$GLOBALS['storedReasons'][$id]];
    }
    return null;
  }
  throw new RuntimeException('Unexpected query '.$sql);
}
function attendance_row(string $email,string $date):?array{return $email==='b@example.test'?$GLOBALS['attendance']:null;}
function execute_sql(string $query,array $args=[]):int{
  $GLOBALS['writes'][]=[$query,$args];
  if(str_contains($query,'INSERT INTO semakan_waktu')){
    $GLOBALS['storedReasons'][$args[0]]='';
  }
  if(str_contains($query,'UPDATE semakan_waktu')){
    $GLOBALS['storedReasons'][$args[1]]=$args[0];
  }
  return 1;
}
$results=ek_reason_my_pending($ppp);
check_case(count($results)===1,'Owner pending list should create a single late incident');
check_case(str_starts_with($results[0]['id'],'SW-MYSQL-'),'Inserted incident must use deterministic MySQL ID');
$id=$results[0]['id'];
try{ek_reason_save($akp,$id,'Terlewat kerana banjir kilat');throw new RuntimeException('Wrong owner accepted');}
catch(InvalidArgumentException $ok){}
$save=ek_reason_save($ppp,$id,'Terlewat kerana banjir kilat');
check_case($save['ok']===true,'User reason did not persist');
check_case(ek_reason_my_pending($ppp)===[],'Submitted reason should not show again');
check_case(count(array_filter($GLOBALS['writes'],fn($e)=>str_contains($e[0],'UPDATE semakan_waktu')))==1,'Reason write must occur only once');
echo "SELF_SERVICE_TIME_REASON_TESTS_OK\n";
