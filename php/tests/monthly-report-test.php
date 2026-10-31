<?php
declare(strict_types=1);
require_once dirname(__DIR__).'/monthly_reports.php';
function rows(string $sql,array $args=[]): array {
    if(strpos($sql,'FROM pengguna')!==false) {
        $r=[];for($i=1;$i<=90;$i++){
            $r[]=['emel'=>'staff'.$i.'@example.test','nama'=>'Staf '.$i,'kategori'=>'PPP'];
        }
        return $r;
    }
    if(strpos($sql,'FROM kehadiran')!==false)
        return [['tarikh'=>'2026-10-01','emel'=>'staff1@example.test',
          'masuk'=>'2026-10-01 08:10:00','balik'=>'2026-10-01 16:30:00']];
    throw new RuntimeException('Unexpected SQL: '.$sql);
}
function date_key($date):string{return substr((string)$date,0,10);}
function all_absence_rows():array{return [];}
function settings_raw():array{return ['DEFAULT_S1_IN'=>'07:30','DEFAULT_S1_OUT'=>'16:30'];}
function schedule(array $u,array $s):array{return ['s1In'=>'07:30','s1Out'=>'16:30'];}
function attendance_public(?array $r,array $schedule):?array {
  return $r?['inTime'=>'08:10','outTime'=>'16:30','inTime2'=>'','outTime2'=>'','status'=>'LEWAT']:null;
}
$parts=mysql_monthly_report_sections(['pentadbir'=>1],'2026-10-01','2026-10-31');
if(count($parts)!==8)throw new RuntimeException('Expected summary, exceptions, 5 punch weeks and individual.');
if($parts[0]['name']!=='RINGKASAN'||count($parts[0]['rows'])!==31)
    throw new RuntimeException('Monthly 31-day summary incomplete.');
if($parts[1]['name']!=='LEWAT BALIK AWAL'||count($parts[1]['rows'])!==1)
    throw new RuntimeException('Late exception missing.');
if(count($parts[2]['rows'])!==90||count($parts[7]['rows'])!==90)
    throw new RuntimeException('Missing staff from card or individual summary.');
$total=array_sum(array_map(static fn($part)=>count($part['rows']),$parts));
if($total<500)throw new RuntimeException('Not all monthly staff records retained: '.$total);
if($parts[2]['rows'][0][2]!=='08:10/16:30')
    throw new RuntimeException('First punch time not retained in weekly matrix.');
echo "PASS: 90 staff x 31 days, 8 sections, 31 daily totals, no silent 250-row truncation\n";
