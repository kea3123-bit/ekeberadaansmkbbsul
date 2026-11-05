<?php
declare(strict_types=1);
date_default_timezone_set('Asia/Kuala_Lumpur');
require dirname(__DIR__).'/admin_action_notifications.php';
function ensure(bool $ok,string $why):void {if(!$ok)throw new RuntimeException($why);}
function date_key($v):string {
    if(is_numeric($v))return gmdate('Y-m-d',((int)floor((float)$v)-25569)*86400);
    return substr((string)$v,0,10);
}
function time_text($v):string {return trim(substr((string)$v,-8,5));}
function must_admin(array $u):void {if(!(bool)($u['pentadbir']??false))throw new RuntimeException('Akses pentadbir tidak dibenarkan.');}
$GLOBALS['sqls']=[];
$GLOBALS['absences']=[
 ['id'=>'TH-1','status'=>'MENUNGGU','emel'=>'a@example.test','nama'=>'Pegawai A','jenis'=>'MESYUARAT','mod'=>'KEBERADAAN','tarikhmula'=>46331,'tarikhakhir'=>46331,'dihantarpada'=>46330.5],
 ['id'=>'TH-2','status'=>'DILULUSKAN','emel'=>'b@example.test','nama'=>'Pegawai B','jenis'=>'CUTI','mod'=>'TIDAK_HADIR','tarikhmula'=>46330,'tarikhakhir'=>46330,'dihantarpada'=>46329.5]
];
$GLOBALS['reviews']=[
 ['id'=>'SW-1','statussemakan'=>'BELUM DIAMBIL MAKLUM','emel'=>'c@example.test','nama'=>'Pegawai C','jenis'=>'LEWAT','sesi'=>1,'tarikh'=>'2026-11-04','wakturekod'=>'08:10','wakturujukan'=>'07:30'],
 ['id'=>'SW-2','statussemakan'=>'DIAMBIL MAKLUM','emel'=>'d@example.test','nama'=>'Pegawai D','jenis'=>'BALIK AWAL','sesi'=>1,'tarikh'=>'2026-11-03','wakturekod'=>'15:00','wakturujukan'=>'16:30'],
 ['id'=>'SW-3','statussemakan'=>null,'emel'=>'e@example.test','nama'=>'Pegawai E','jenis'=>'BALIK AWAL','sesi'=>1,'tarikh'=>'2026-11-02','wakturekod'=>'15:00','wakturujukan'=>'16:30']
];
function rows(string $sql,array $params=[]):array {
    $GLOBALS['sqls'][]=$sql;
    ensure($params===[],'Admin query must not take user-selected unsafe SQL');
    if(str_contains($sql,'FROM tidak_hadir')){
        ensure(str_contains($sql,"status='MENUNGGU'"),'Missing approval-status filter');
        return array_values(array_filter($GLOBALS['absences'],fn($r)=>$r['status']==='MENUNGGU'));
    }
    if(str_contains($sql,'FROM semakan_waktu')){
        ensure(str_contains($sql,"statussemakan='BELUM DIAMBIL MAKLUM'"),'Missing acknowledgement status filter');
        return array_values(array_filter($GLOBALS['reviews'],fn($r)=>in_array($r['statussemakan'],['BELUM DIAMBIL MAKLUM',null,''],true)));
    }
    throw new RuntimeException('Unexpected query: '.$sql);
}
try{
    ek_admin_pending_actions(['pentadbir'=>0]);
    throw new RuntimeException('Non-admin incorrectly authorized');
}catch(RuntimeException $ex){ensure(str_contains($ex->getMessage(),'Akses pentadbir'),'Wrong non-admin rejection');}
ensure(count($GLOBALS['sqls'])===0,'Non-admin queried privileged data');
$admin=['pentadbir'=>1,'emel'=>'admin@example.test'];
$summary=ek_admin_pending_actions($admin);
ensure($summary['absenceCount']===1&&$summary['timeReviewCount']===2&&$summary['total']===3,'Pending counts incorrect');
ensure($summary['requests'][0]['id']==='TH-1'&&$summary['requests'][0]['kind']==='ABSENCE','Approval detail missing');
ensure($summary['timeReviews'][0]['kind']==='TIME_REVIEW'&&$summary['timeReviews'][0]['session']===1,'Time review detail missing');
ensure(count($GLOBALS['sqls'])===2,'Only two read-only queries should be executed');
foreach($GLOBALS['sqls'] as $q)ensure(str_starts_with(trim($q),'SELECT '),'Notification must be read-only');
$GLOBALS['absences'][0]['status']='DILULUSKAN';
$GLOBALS['reviews'][0]['statussemakan']='DIAMBIL MAKLUM';
$GLOBALS['reviews'][2]['statussemakan']='DITOLAK';
$done=ek_admin_pending_actions($admin);
ensure($done['total']===0&&$done['absenceCount']===0&&$done['timeReviewCount']===0,
 'Notification must disappear once actions are completed');
echo "ADMIN_PENDING_ACTIONS_READ_ONLY_AND_ACCESS_CHECK_PASS\n";
