<?php
declare(strict_types=1);
date_default_timezone_set('Asia/Kuala_Lumpur');
require dirname(__DIR__).'/time_exception_reasons.php';
function check_it(bool $ok,string $msg):void{if(!$ok)throw new RuntimeException($msg);}
function today():string{return '2026-11-05';}
function date_key($v):string{return substr((string)$v,0,10);}
function time_text($v):string {
    if(!$v)return '';
    $v=(string)$v;
    if(preg_match('/^\d{4}-\d\d-\d\d ([0-2]\d:[0-5]\d)/',$v,$m))return $m[1];
    return substr($v,0,5);
}
function settings_raw():array{return [
 'SYSTEM_MODE'=>'REAL','SYSTEM_START_DATE'=>'2026-11-01',
 'THURSDAY_WBF_ENABLED'=>'FALSE'
];}
function schedule(array $u,array $s):array{return [
 's1In'=>'07:30','s1Out'=>'16:30','s2In'=>'','s2Out'=>''
];}
$user=['emel'=>'owner@example.test','nama'=>'TEST USER','kategori'=>'PPP','jawatan'=>'Guru'];
$attendance=[
 ['tarikh'=>'2026-11-05','emel'=>'owner@example.test','status'=>'AUTO_TIDAK_HADIR',
  'sumber'=>'AUTO_TIDAK_HADIR','masuk'=>'2026-11-05 08:15:00','balik'=>null,'masuk2'=>null,'balik2'=>null],
 ['tarikh'=>'2026-11-04','emel'=>'owner@example.test','status'=>'HADIR','sumber'=>'PHP_MYSQL',
  'masuk'=>'2026-11-04 08:10:00','balik'=>'2026-11-04 15:05:00','masuk2'=>null,'balik2'=>null],
 ['tarikh'=>'2026-11-03','emel'=>'owner@example.test','status'=>'LEWAT','sumber'=>'PHP_MYSQL',
  'masuk'=>'2026-11-03 08:15:00','balik'=>'2026-11-03 16:40:00','masuk2'=>null,'balik2'=>null],
 ['tarikh'=>'2026-11-02','emel'=>'owner@example.test','status'=>'LEWAT','sumber'=>'PHP_MYSQL',
  'masuk'=>'2026-11-02 08:11:00','balik'=>'2026-11-02 16:42:00','masuk2'=>null,'balik2'=>null]
];
$reviews=[
 ['id'=>'existing-nov-2','emel'=>'owner@example.test','tarikh'=>'2026-11-02',
  'jenis'=>'LEWAT','sesi'=>1,'sebabpengguna'=>'Sudah diterangkan kepada pihak sekolah']
];
$applications=[
 ['email'=>'owner@example.test','status'=>'DILULUSKAN','mode'=>'KEBERADAAN',
  'startDate'=>'2026-11-04','endDate'=>'2026-11-04','startTime'=>'14:30','endTime'=>'16:30'],
 ['email'=>'owner@example.test','status'=>'MENUNGGU','mode'=>'KEBERADAAN',
  'startDate'=>'2026-11-03','endDate'=>'2026-11-03','startTime'=>'07:30','endTime'=>'08:30']
];
function all_absence_rows():array{return $GLOBALS['applications'];}
function rows(string $sql,array $args=[]):array{
    global $attendance,$reviews;
    if(str_contains($sql,'FROM sejarah_jadual'))return [];
    if(str_contains($sql,'FROM kehadiran'))return array_values(array_filter($attendance,static fn($r)=>
      strtolower($r['emel'])===$args[0]&&$r['tarikh']>=$args[1]&&$r['tarikh']<=$args[2]));
    if(str_contains($sql,'FROM semakan_waktu'))return array_values(array_filter($reviews,static fn($r)=>
      strtolower($r['emel'])===$args[0]&&$r['tarikh']>=$args[1]&&$r['tarikh']<=$args[2]));
    throw new RuntimeException('Unexpected SQL: '.$sql);
}
check_it(count(ek_reason_incidents($attendance[0],$user,settings_raw()))===1,
    'AUTO_TIDAK_HADIR source with a real late punch must not be excluded');
$summary=ek_reason_my_summary($user);
check_it($summary['pendingCount']===2,'Only Nov 5 and Nov 4 late remain (got '.$summary['pendingCount'].')');
check_it($summary['pastDays']===1&&$summary['todayCount']===1&&$summary['pendingDays']===2,
    'Notification must count distinct past dates and today correctly');
check_it($summary['rows'][0]['date']==='2026-11-05'&&$summary['rows'][0]['type']==='LEWAT',
    'Most recent unresolved case must be shown first');
check_it(ek_reason_requires_before_out($user,'2026-11-05',$attendance[0])!==[],
    'OUT should be blocked while user has not explained same-day late arrival');
check_it(ek_reason_requires_before_out($user,'2026-11-04',$attendance[1])!==[],
    'Historic missing reason must remain available for the old-day notification');
$reviews[]=[
 'id'=>'nov-5-saved','emel'=>'owner@example.test','tarikh'=>'2026-11-05','jenis'=>'LEWAT',
 'sesi'=>1,'sebabpengguna'=>'Sebab telah diisi selepas Rakam Masuk'
];
check_it(ek_reason_requires_before_out($user,'2026-11-05',$attendance[0])===[],
    'OUT must become available after explanation is stored');
$after=ek_reason_my_summary($user);
check_it($after['todayCount']===0&&$after['pastDays']===1,
    'After explaining today, only older unresolved days should trigger notification');
$applications[]=[
 'email'=>'owner@example.test','status'=>'DILULUSKAN','mode'=>'TIDAK_HADIR',
 'startDate'=>'2026-11-04','endDate'=>'2026-11-04'
];
check_it(ek_reason_my_summary($user)['pendingCount']===0,
    'Approved date-wide leave must suppress any previous-day reminder');
$applications[]=[
 'email'=>'owner@example.test','status'=>'DITOLAK','mode'=>'TIDAK_HADIR',
 'startDate'=>'2026-11-05','endDate'=>'2026-11-05'
];
$reviews=array_values(array_filter($reviews,static fn($r)=>$r['id']!=='nov-5-saved'));
check_it(ek_reason_my_summary($user)['todayCount']===1,
    'Rejected leave must not suppress a required explanation');
echo "TIME_REASON_BACKLOG_AUTO_SOURCE_GATE_AND_COVERAGE_OK\n";
