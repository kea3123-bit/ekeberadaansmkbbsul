<?php
declare(strict_types=1);
/** Exercise MySQL absence public/manager projections with fixture database rows. */
$source=file_get_contents(dirname(__DIR__).'/api.php');
function pull_fn(string $start,string $end,string $code):string {
    $from=strpos($code,'function '.$start.'(');
    $to=strpos($code,'function '.$end.'(',$from);
    if($from===false||$to===false||$to<=$from)throw new RuntimeException("Cannot extract ".$start);
    return substr($code,$from,$to-$from);
}
$GLOBALS['dbReads']=[];
function rows(string $sql,array $params=[]):array {
    $GLOBALS['dbReads'][]=$sql;
    if(str_contains($sql,'FROM pengguna'))return [
        ['emel'=>'admin@example.test','jawatan'=>'Pengetua','aktif'=>1,'nama'=>'Administrator'],
        ['emel'=>'teacher@example.test','jawatan'=>'Guru','aktif'=>1,'nama'=>'Teacher'],
        ['emel'=>'lost@example.test','jawatan'=>'','aktif'=>0,'nama'=>'Old Account']
    ];
    if(str_contains($sql,'FROM kehadiran'))return [];
    throw new RuntimeException('Unexpected SQL '.$sql);
}
function valid_day($value):string {return (string)$value;}
function today():string{return '2026-11-02';}
function settings_raw():array{return ['SYSTEM_START_DATE'=>'2026-09-01'];}
function public_user(array $user):array{return ['name'=>$user['nama']??''];}
function all_absence_rows():array{return [
  ['id'=>'r1','email'=>'teacher@example.test','name'=>'Teacher','status'=>'DILULUSKAN',
   'reviewedBy'=>'admin@example.test','startDate'=>'2026-11-02','endDate'=>'2026-11-05',
   'type'=>'CUTI REHAT KHAS','mode'=>'TIDAK_HADIR','category'=>'PPP','jobTitle'=>'Guru'],
  ['id'=>'r2','email'=>'teacher@example.test','name'=>'Teacher','status'=>'DITOLAK',
   'reviewedBy'=>'lost@example.test','startDate'=>'2026-11-02','endDate'=>'2026-11-02',
   'type'=>'LAIN-LAIN','mode'=>'TIDAK_HADIR','category'=>'PPP','jobTitle'=>'Guru'],
  ['id'=>'r3','email'=>'teacher@example.test','name'=>'Teacher','status'=>'MENUNGGU',
   'reviewedBy'=>'','startDate'=>'2026-11-02','endDate'=>'2026-11-03',
   'type'=>'KURSUS','mode'=>'KEBERADAAN','category'=>'PPP','jobTitle'=>'Guru']
];}
function date_key($d):string{return substr((string)$d,0,10);}
function time_text($v):string{return (string)($v??'');}
function assert_ok(bool $ok,string $msg):void{if(!$ok)throw new RuntimeException($msg);}
require dirname(__DIR__).'/absence_auto_report.php';
$pub=pull_fn('public_absences','management_absences',$source);
$pub=str_replace("require_once __DIR__.'/absence_auto_report.php';",'',$pub);
eval($pub);
$mgmt=pull_fn('management_absences','submit_absence',$source);
eval($mgmt);
$public=public_absences('2026-11-02','2026-11-02');
assert_ok(count($public['rows'])===2,'Public list must include approved and pending');
$approved=array_values(array_filter($public['rows'],fn($r)=>$r['id']==='r1'))[0];
assert_ok($approved['startDate']==='2026-11-02'&&$approved['endDate']==='2026-11-02','Filtered dates must remain clipped');
assert_ok($approved['originalStartDate']==='2026-11-02'&&$approved['originalEndDate']==='2026-11-05','Original date span must survive');
$management=management_absences(['nama'=>'Admin'],'2026-11-02','2026-11-02');
assert_ok(count($management['requests'])===3,'Management must retain approved, rejected and pending');
$byId=[];foreach($management['requests'] as $r)$byId[$r['id']]=$r;
assert_ok($byId['r1']['reviewerJobTitle']==='Pengetua','Approver job title must come from pengguna.jawatan');
assert_ok($byId['r2']['reviewerJobTitle']==='','Missing position must not invent Pengurusan');
assert_ok(!isset($byId['r3']['reviewerJobTitle'])||$byId['r3']['reviewerJobTitle']==='','Pending must not inherit another approver');
$count=count(array_filter($GLOBALS['dbReads'],fn($q)=>str_contains($q,'FROM pengguna')));
assert_ok($count===2,'Reviewer titles should be fetched in one additional query, not N+1; got '.$count);
echo "APPROVER_JOB_TITLE_AND_ORIGINAL_PUBLIC_DATES_OK\n";
