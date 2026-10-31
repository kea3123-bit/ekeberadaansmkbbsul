<?php
declare(strict_types=1);
/**
 * Database-free regression test: submitted Keberadaan must use a valid MySQL
 * INSERT even though the source table has a column named MOD (reserved).
 * Never inserts data into production.
 */
$source=(string)file_get_contents(dirname(__DIR__).'/api.php');
$start=strpos($source,'function submit_absence(');
$end=$start===false?false:strpos($source,"\nfunction time_reviews(",$start);
if($start===false || $end===false)throw new RuntimeException('submit_absence() could not be located.');
eval(substr($source,$start,$end-$start));
function valid_day(string $date):string {return $date;}
function valid_time($time):string {return (string)$time;}
function presence_types():array {return ['URUSAN RASMI'];}
function absence_types():array {return ['CUTI'];}
function now_myt():string {return '2026-10-31 14:00:00';}
function excel_number($date):float {return 46326.58;}
function one(string $query,array $args=[]):?array {
    if(strpos($query,'MAX(_source_row)')!==false)return ['n'=>466];
    throw new RuntimeException('Unexpected SELECT');
}
$queries=[];$audits=[];
function execute_sql(string $query,array $args=[]):int {
    global $queries;$queries[]=['query'=>$query,'params'=>$args];
    return 1;
}
function audit_event(string $actor,string $action,string $id,string $details=''):void {
    global $audits;$audits[]=compact('actor','action','id');
}
$user=['emel'=>'staff@example.test','nama'=>'Pegawai Ujian','kategori'=>'AKP','jawatan'=>'Pembantu'];
$request=['mode'=>'KEBERADAAN','type'=>'URUSAN RASMI',
  'startDate'=>'2026-10-31','endDate'=>'2026-10-31',
  'startTime'=>'12:00','endTime'=>'14:31',
  'note'=>'Bertolak ke Putrajaya untuk Program Duta Guru'];
$result=submit_absence($user,$request);
if(($result['ok']??false)!==true || count($queries)!==1 || count($audits)!==1)
    throw new RuntimeException('Request flow should perform exactly one INSERT and audit.');
$sql=$queries[0]['query'];
if(strpos($sql,'INSERT INTO tidak_hadir')===false || strpos($sql,',`mod`,')===false || strpos($sql,',mod,')!==false)
    throw new RuntimeException('Reserved MySQL MOD identifier must use backticks.');
if(substr_count($sql,'?')!==16 || count($queries[0]['params'])!==16)
    throw new RuntimeException('SQL placeholders do not match bound insert values.');
if($queries[0]['params'][12]!=='KEBERADAAN' ||
   $queries[0]['params'][13]!=='12:00' ||
   $queries[0]['params'][14]!=='14:31')
    throw new RuntimeException('Presence mode and times lost during query generation.');
echo "PASS absence submit: reserved MOD quoted, 16 placeholders, correct presence timing, no MySQL writes\n";
