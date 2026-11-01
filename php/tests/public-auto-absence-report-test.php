<?php
declare(strict_types=1);
/** No DB credentials or network; verifies read-only MySQL report projection. */
$staff=[
 ['emel'=>'a@example.test','nama'=>'AUTO A','kategori'=>'PPP','jawatan'=>'Guru','aktif'=>1],
 ['emel'=>'b@example.test','nama'=>'APPROVED B','kategori'=>'PPP','jawatan'=>'Guru','aktif'=>1],
 ['emel'=>'c@example.test','nama'=>'PUNCHED C','kategori'=>'PPP','jawatan'=>'Guru','aktif'=>1],
 ['emel'=>'d@example.test','nama'=>'INACTIVE D','kategori'=>'PPP','jawatan'=>'Guru','aktif'=>0],
 ['emel'=>'e@example.test','nama'=>'PENDING E','kategori'=>'PPP','jawatan'=>'Guru','aktif'=>1],
];
$physical=[
 ['_row_id'=>1,'emel'=>'A@Example.Test','tarikh'=>'2026-11-01','nama'=>'AUTO A','status'=>'TIDAK HADIR','sumber'=>'AUTO_TIDAK_HADIR','masuk'=>null,'masuk2'=>null],
 ['_row_id'=>2,'emel'=>'b@example.test','tarikh'=>'2026-11-01','nama'=>'APPROVED B','status'=>'TIDAK HADIR','sumber'=>'AUTO_TIDAK_HADIR','masuk'=>null,'masuk2'=>null],
 ['_row_id'=>3,'emel'=>'c@example.test','tarikh'=>'2026-11-01','nama'=>'PUNCHED C','status'=>'TIDAK HADIR','sumber'=>'AUTO_TIDAK_HADIR','masuk'=>'2026-11-01 08:55:00','masuk2'=>null],
 ['_row_id'=>4,'emel'=>'d@example.test','tarikh'=>'2026-11-01','nama'=>'INACTIVE D','status'=>'TIDAK HADIR','sumber'=>'AUTO_TIDAK_HADIR','masuk'=>null,'masuk2'=>null],
 ['_row_id'=>5,'emel'=>'e@example.test','tarikh'=>'2026-11-01','nama'=>'PENDING E','status'=>'TIDAK HADIR','sumber'=>'AUTO_TIDAK_HADIR','masuk'=>null,'masuk2'=>null],
 ['_row_id'=>6,'emel'=>'a@example.test','tarikh'=>'2026-11-01','nama'=>'AUTO A','status'=>'TIDAK HADIR','sumber'=>'AUTO_TIDAK_HADIR','masuk'=>null,'masuk2'=>null],
 ['_row_id'=>7,'emel'=>'a@example.test','tarikh'=>'2026-11-02','nama'=>'AUTO A','status'=>'TIDAK HADIR','sumber'=>'AUTO_TIDAK_HADIR','masuk'=>null,'masuk2'=>null],
];
function rows(string $sql,array $params=[]):array {
    global $staff,$physical;
    if(str_contains($sql,'FROM pengguna'))return $staff;
    if(str_contains($sql,'FROM kehadiran'))return array_values(array_filter($physical,fn($r)=>$r['tarikh']>=$params[0]&&$r['tarikh']<=$params[1]));
    throw new RuntimeException('Unexpected query '.$sql);
}
function date_key($x):string {return (string)$x;}
function time_text($x):string {
    if($x===null||$x==='')return '';
    return substr((string)$x,11,5);
}
require dirname(__DIR__).'/absence_auto_report.php';
$active=[
 ['email'=>'b@example.test','status'=>'DILULUSKAN','mode'=>'TIDAK_HADIR','startDate'=>'2026-11-01','endDate'=>'2026-11-01'],
 ['email'=>'e@example.test','status'=>'MENUNGGU','mode'=>'KEBERADAAN','startDate'=>'2026-11-01','endDate'=>'2026-11-01'],
];
$rows=mysql_auto_unexplained_absence_rows('2026-11-01','2026-11-01',$active);
if(count($rows)!==1)throw new RuntimeException('Must include only unexplained active employee; got '.count($rows));
$x=$rows[0];
if($x['name']!=='AUTO A'||$x['mode']!=='TIDAK_HADIR'||$x['type']!=='TIADA PENJELASAN'||
    $x['status']!=='TIDAK MOHON'||$x['source']!=='AUTO_TIDAK_HADIR')
    throw new RuntimeException('Auto report row does not follow public PDF status contract');
if($x['startDate']!=='2026-11-01'||$x['endDate']!=='2026-11-01')throw new RuntimeException('Date mismatch');
$next=mysql_auto_unexplained_absence_rows('2026-11-02','2026-11-02',$active);
if(count($next)!==1||$next[0]['startDate']!=='2026-11-02')throw new RuntimeException('Range filtering failed');
$approved=[['email'=>'a@example.test','status'=>'DILULUSKAN','startDate'=>'2026-11-01','endDate'=>'2026-11-02']];
foreach(mysql_auto_unexplained_absence_rows('2026-11-01','2026-11-01',$approved) as $r) if($r['email']==='a@example.test') throw new RuntimeException('Approved overlapping leave duplicated');
echo "PUBLIC_AUTO_ABSENCE_PDF_TESTS_OK\n";
