<?php
declare(strict_types=1);
date_default_timezone_set('Asia/Kuala_Lumpur');
require dirname(__DIR__).'/monthly_reports.php';
$settings=['WORKING_DAYS'=>'SUN,MON,TUE,WED,THU','THURSDAY_WBF_ENABLED'=>'TRUE',
 'THURSDAY_WBF_IN_FROM'=>'07:30','THURSDAY_WBF_IN_TO'=>'09:00',
 'THURSDAY_WBF_OUT_FROM'=>'15:00','THURSDAY_WBF_OUT_TO'=>'16:30',
 'THURSDAY_WBF_DURATION_MINUTES'=>'450'];
$staff=[
 ['emel'=>'akp@example.test','nama'=>'AKP WBF','kategori'=>'AKP','jawatan'=>'Pembantu Tadbir'],
 ['emel'=>'pengetua@example.test','nama'=>'PENGETUA WBF','kategori'=>'Pengurusan','jawatan'=>'Pengetua'],
 ['emel'=>'ppp@example.test','nama'=>'PPP NORMAL','kategori'=>'PPP','jawatan'=>'Guru'],
 ['emel'=>'late@example.test','nama'=>'LATE COVERED','kategori'=>'PPP','jawatan'=>'Guru'],
 ['emel'=>'uncovered@example.test','nama'=>'LATE UNCOVERED','kategori'=>'PPP','jawatan'=>'Guru']
];
$att=[
 ['emel'=>'akp@example.test','tarikh'=>'2026-10-01','masuk'=>'07:18','balik'=>'15:05'],
 ['emel'=>'pengetua@example.test','tarikh'=>'2026-10-01','masuk'=>'08:15','balik'=>'15:30'],
 ['emel'=>'ppp@example.test','tarikh'=>'2026-10-01','masuk'=>'07:15','balik'=>'15:05'],
 ['emel'=>'late@example.test','tarikh'=>'2026-10-01','masuk'=>'08:10','balik'=>'16:35'],
 ['emel'=>'uncovered@example.test','tarikh'=>'2026-10-01','masuk'=>'08:10','balik'=>'16:35'],
];
$requests=[
 ['email'=>'pengetua@example.test','mode'=>'KEBERADAAN','status'=>'DILULUSKAN',
  'startDate'=>'2026-10-01','endDate'=>'2026-10-01','startTime'=>'15:20','endTime'=>'16:20',
  'type'=>'URUSAN SEKOLAH','note'=>''],
 ['email'=>'late@example.test','mode'=>'KEBERADAAN','status'=>'MENUNGGU',
  'startDate'=>'2026-10-01','endDate'=>'2026-10-01','startTime'=>'07:30','endTime'=>'08:30',
  'type'=>'MESYUARAT','note'=>''],
 ['email'=>'uncovered@example.test','mode'=>'KEBERADAAN','status'=>'DILULUSKAN',
  'startDate'=>'2026-10-01','endDate'=>'2026-10-01','startTime'=>'13:00','endTime'=>'15:00',
  'type'=>'TAKLIMAT','note'=>''],
];
function rows(string $query,array $args=[]):array {
 global $staff,$att;
 if(str_contains($query,'FROM pengguna'))return $staff;
 if(str_contains($query,'FROM kehadiran'))return array_values(array_filter($att,fn($x)=>$x['tarikh']>=$args[0]&&$x['tarikh']<=$args[1]));
 throw new RuntimeException('Unexpected SQL '.$query);
}
function date_key($v):string{return substr((string)$v,0,10);}
function all_absence_rows():array{global $requests;return $requests;}
function settings_raw():array{global $settings;return $settings;}
function public_holidays_safe($from=null,$to=null):array{return [];}
function schedule(array $u,array $s):array{return ['s1In'=>'07:30','s1Out'=>'16:30','s2Out'=>''];}
function attendance_public(?array $r,array $sch):?array{
 if(!$r)return null;
 return ['inTime'=>$r['masuk'],'outTime'=>$r['balik'],'inTime2'=>$r['masuk2']??'',
   'outTime2'=>$r['balik2']??'','status'=>'HADIR'];
}
function ck(bool $b,string $why):void{if(!$b)throw new RuntimeException($why);}
ck(mysql_monthly_wbf_out_reference($staff[0],$settings,'2026-10-01','07:18','16:30')==='15:00',
   'WBF arrival before 07:30 must use 07:30 start');
ck(mysql_monthly_wbf_out_reference($staff[1],$settings,'2026-10-01','08:15','16:30')==='15:45',
   'Pengetua should use 08:15 plus 450 min');
ck(mysql_monthly_wbf_out_reference($staff[2],$settings,'2026-10-01','07:15','16:30')==='16:30',
   'PPP must retain regular departure');
ck(mysql_monthly_wbf_out_reference($staff[0],$settings,'2026-10-02','07:18','16:30')==='16:30',
   'Friday must not apply Thursday WBF');
ck(mysql_monthly_wbf_out_reference($staff[0],$settings,'2026-10-01','09:10','16:30')==='16:30',
   'Late arrival after WBF_IN_TO must use regular departure');
$sections=mysql_monthly_report_sections(['pentadbir'=>1],'2026-10-01','2026-10-01');
$exceptions=$sections[1]['rows'];
ck(count($exceptions)===4,'Expected Pengetua early, PPP early, 2 late; AKP 15:05 is not early. got '.count($exceptions));
$by=[];foreach($exceptions as $ex)$by[$ex[2]]=$ex;
ck(!isset($by['akp@example.test']),'AKP WBF was incorrectly flagged early');
ck($by['pengetua@example.test'][4]==='BALIK AWAL','Pengetua 15:30 must be early vs 15:45');
ck(str_contains($by['pengetua@example.test'][10],'Keberadaan: '),'Covered early must show presence explanation');
ck($by['ppp@example.test'][10]==='TIADA PENJELASAN','PPP early without request must be highlighted');
ck(str_contains($by['late@example.test'][9],'Keberadaan:'),'Covered late must show presence request');
ck(str_contains($by['late@example.test'][9],'Menunggu'),'Pending request should be identifiable');
ck($by['uncovered@example.test'][9]==='TIADA PENJELASAN',
   'Unrelated afternoon presence cannot explain morning late arrival');
$summary=$sections[0]['rows'];
ck($summary[0][7]===0,'WBF early count in summary must be zero for AKP');
$card=$sections[2]['rows'];
ck(strpos($card[0][2],'BALIK AWAL')===false,'WBF day punch card must not show early');
$settings['THURSDAY_WBF_ENABLED']='FALSE';
$disabled=mysql_monthly_report_sections(['pentadbir'=>1],'2026-10-01','2026-10-01');
ck(count($disabled[1]['rows'])===5,'Disabling WBF must restore standard early departure');
$settings['THURSDAY_WBF_ENABLED']='TRUE';
$att[0]['balik']='14:50';
$att[0]['masuk2']='11:30';$att[0]['balik2']='15:05';
$second=mysql_monthly_report_sections(['pentadbir'=>1],'2026-10-01','2026-10-01');
$have=array_filter($second[1]['rows'],fn($r)=>$r[2]==='akp@example.test');
ck(!$have,'Optional second session final 15:05 should supersede first OUT 14:50 WBF 15:00');
echo "WBF_THURSDAY_REPORT_AND_UNEXPLAINED_CASES_OK\n";
