<?php
declare(strict_types=1);
date_default_timezone_set('Asia/Kuala_Lumpur');
$src=file_get_contents(dirname(__DIR__).'/api.php');
$begin=strpos($src,'function punch_card_chief_verification(');
$end=strpos($src,'function admin_data(', $begin);
if($begin===false||$end===false)throw new RuntimeException('Missing punch card functions');
eval(substr($src,$begin,$end-$begin));
function ok(bool $value,string $msg):void {if(!$value)throw new RuntimeException($msg);}
function date_key($value):string {
    if($value===null||$value==='')return '';
    if(is_numeric($value))return gmdate('Y-m-d',((int)floor((float)$value)-25569)*86400);
    return substr((string)$value,0,10);
}
function time_text($value):string {
    if($value===null||$value==='')return '';
    return substr((string)$value,-8,5)==='-11-'?'':substr((string)$value,11,5);
}
function excel_number($v):float {return (strtotime(substr((string)$v,0,10).' UTC')/86400)+25569;}
function today():string {return '2026-11-16';}
function now_myt():string {return '2026-11-16 17:00:00';}
function settings_raw():array {return [
    'SYSTEM_START_DATE'=>'2026-09-01',
    'WORKING_DAYS'=>'SUN,MON,TUE,WED,THU',
    'ABSENT_AFTER'=>'10:00',
    'SCHOOL_NAME'=>'Test School'
];}
function schedule(array $u,array $s):array {return ['s1In'=>'07:30','s1Out'=>'16:30','s2In'=>'','s2Out'=>''];}
function attendance_public(array $x,array $sch):array {return [
 'inTime'=>substr((string)($x['masuk']??''),11,5),
 'outTime'=>substr((string)($x['balik']??''),11,5),
 'inTime2'=>'','outTime2'=>''
];}
function public_holidays_safe(...$args):array {return [];}
function user_by_email(string $email,bool $activeOnly=true):?array {
    if($email==='principal@example.test')return ['emel'=>$email,'nama'=>'Pengarah Sekolah','jawatan'=>'Pengetua'];
    if($email==='other@example.test')return ['emel'=>$email,'nama'=>'Penolong','jawatan'=>'Penolong Kanan'];
    return null;
}
function public_user(array $u):array {return ['name'=>$u['nama'],'email'=>$u['emel']];}
$GLOBALS['reads']=[];
function rows(string $sql,array $args=[]):array {
    $GLOBALS['reads'][]=$sql;
    if(str_contains($sql,'FROM kehadiran'))return [
      ['tarikh'=>'2026-11-10','emel'=>'staff@example.test','masuk'=>'2026-11-10 07:48:00',
       'status'=>'LEWAT','statuswaktu'=>'LEWAT','sumber'=>'PHP_MYSQL'],
      ['tarikh'=>'2026-11-13','emel'=>'staff@example.test','masuk'=>'2026-11-13 08:10:00',
       'balik'=>'2026-11-13 14:30:00','status'=>'LEWAT / BALIK AWAL','statuswaktu'=>'LEWAT,BALIK AWAL','sumber'=>'PHP_MYSQL'],
      ['tarikh'=>'2026-11-15','emel'=>'staff@example.test','masuk'=>'2026-11-15 07:15:00',
       'status'=>'HADIR','statuswaktu'=>'','sumber'=>'PHP_MYSQL']
    ];
    if(str_contains($sql,'FROM tidak_hadir'))return [
      ['id'=>'NA-16','emel'=>'staff@example.test','status'=>'DILULUSKAN','mod'=>'TIDAK_HADIR',
       'tarikhmula'=>'2026-11-16','tarikhakhir'=>'2026-11-16','jenis'=>'LAIN-LAIN',
       'disemakoleh'=>'principal@example.test','disemakpada'=>'2026-11-15'],
      ['id'=>'KE-15','emel'=>'staff@example.test','status'=>'DILULUSKAN','mod'=>'KEBERADAAN',
       'tarikhmula'=>'2026-11-15','tarikhakhir'=>'2026-11-15','jenis'=>'MESYUARAT',
       'disemakoleh'=>'principal@example.test','disemakpada'=>'2026-11-14'],
      ['id'=>'NA-11','emel'=>'staff@example.test','status'=>'MENUNGGU','mod'=>'TIDAK_HADIR',
       'tarikhmula'=>'2026-11-11','tarikhakhir'=>'2026-11-11','jenis'=>'CUTI',
       'disemakoleh'=>'','disemakpada'=>null],
      ['id'=>'NA-12','emel'=>'staff@example.test','status'=>'DITOLAK','mod'=>'TIDAK_HADIR',
       'tarikhmula'=>'2026-11-12','tarikhakhir'=>'2026-11-12','jenis'=>'CUTI',
       'disemakoleh'=>'principal@example.test','disemakpada'=>'2026-11-12']
    ];
    if(str_contains($sql,'FROM semakan_waktu'))return [
      ['id'=>'SW-10','tarikh'=>'2026-11-10','jenis'=>'LEWAT','sesi'=>1,
       'statussemakan'=>'DIAMBIL MAKLUM','disemakoleh'=>'principal@example.test',
       'namapelulus'=>'Pengarah Sekolah','disemakpada'=>'2026-11-15','ulasan'=>'Diambil maklum'],
      ['id'=>'SW-13-IN','tarikh'=>'2026-11-13','jenis'=>'LEWAT','sesi'=>1,
       'statussemakan'=>'DIAMBIL MAKLUM','disemakoleh'=>'principal@example.test',
       'namapelulus'=>'Pengarah Sekolah','disemakpada'=>'2026-11-15'],
      ['id'=>'SW-13-OUT','tarikh'=>'2026-11-13','jenis'=>'BALIK AWAL','sesi'=>1,
       'statussemakan'=>'BELUM DIAMBIL MAKLUM','disemakoleh'=>null,'namapelulus'=>null,'disemakpada'=>null]
    ];
    throw new RuntimeException('Unexpected DB read '.$sql);
}
$staff=['emel'=>'staff@example.test','nama'=>'Staff','kategori'=>'PPP','aktif'=>1];
$card=punch_card($staff,'2026-11');
$by=[];foreach($card['records'] as $r)$by[$r['day']]=$r;
ok(($by[10]['chiefVerification']['label']??'')==='MAKLUM','Approved LEWAT must show MAKLUM');
ok(($by[10]['chiefVerification']['entries'][0]['reviewerJobTitle']??'')==='Pengetua','Real reviewer job title missing');
ok(($by[10]['chiefVerification']['entries'][0]['reviewerName']??'')==='Pengarah Sekolah','Real reviewer name missing');
ok(($by[13]['chiefVerification']??null)===null,'Mixed approved/pending late+early must NOT be signed');
ok(($by[11]['chiefVerification']??null)===null,'Pending absence must NOT be signed');
ok(($by[12]['chiefVerification']??null)===null,'Rejected absence must NOT be signed');
ok(($by[15]['chiefVerification']['label']??'')==='LULUS','Approved Keberadaan with punch must be signed as request approval');
ok(($by[16]['chiefVerification']['label']??'')==='LULUS','Approved TIDAK_HADIR must be signed as request approval');
ok(($by[16]['chiefVerification']['kind']??'')==='TIDAK_HADIR','Sign approval kind must preserve absent mode');
ok(($by[9]['chiefVerification']??null)===null,'Ordinary/unreviewed day must not have a fake approval');
$withFakeApproval=[
 'date'=>'2026-11-10','status'=>'LEWAT','statusFlags'=>['LEWAT'],
 'reviewItems'=>[['type'=>'LEWAT','session'=>1,'reviewStatus'=>'DIAMBIL MAKLUM','reviewerEmail'=>'']]
];
ok(punch_card_chief_verification($withFakeApproval,[],[])===null,
 'Reviewed status with no approver identity must not generate a signature');
$missingOtherIncident=[
 'date'=>'2026-11-10','status'=>'LEWAT / BALIK AWAL','statusFlags'=>['LEWAT','BALIK AWAL'],
 'reviewItems'=>[['type'=>'LEWAT','session'=>1,'reviewStatus'=>'DIAMBIL MAKLUM','reviewerEmail'=>'principal@example.test']]
];
ok(punch_card_chief_verification($missingOtherIncident,[],[])===null,
 'One acknowledged incident cannot approve another missing incident');
echo "PUNCH_CARD_CHIEF_VERIFICATION_MANUAL_TIME_AND_ABSENCE_OK\n";
