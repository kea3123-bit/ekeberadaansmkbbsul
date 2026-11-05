<?php
declare(strict_types=1);
date_default_timezone_set('Asia/Kuala_Lumpur');

/** Regression: Thursday 5 November, including a real 07:57 punch whose source
 * remains AUTO_TIDAK_HADIR, and historical schedule/WBF exceptions.
 */
function assert_cron(bool $ok,string $label):void {if(!$ok)throw new RuntimeException($label);}
function today():string{return '2026-11-05';}
function now_myt():string{return '2026-11-05 12:40:00';}
function date_key($raw):string {
    if(is_numeric($raw))return gmdate('Y-m-d',((int)floor((float)$raw)-25569)*86400);
    return substr((string)$raw,0,10);
}
function time_text($raw):string {
    if($raw===null||$raw==='')return '';
    $s=(string)$raw;
    if(preg_match('/^20\d\d-\d\d-\d\d (\d\d:\d\d)/',$s,$m))return $m[1];
    if(preg_match('/^\d\d:\d\d/',$s))return substr($s,0,5);
    return '';
}
function settings_raw():array{return [
    'SYSTEM_MODE'=>'REAL','SYSTEM_START_DATE'=>'2026-09-01',
    'THURSDAY_WBF_ENABLED'=>'FALSE'
];}
function schedule(array $person,array $settings):array {
    return ['s1In'=>'07:30','s1Out'=>'16:30','s2In'=>'','s2Out'=>''];
}
function excel_number($raw):float{return 46331.6;}
$GLOBALS['users']=[];
foreach(['autopunch','no-punch','historic','wbf','covered','manual','ack'] as $name) {
    $GLOBALS['users'][$name.'@example.test']=[
       'emel'=>$name.'@example.test','nama'=>strtoupper($name),
       'kategori'=>$name==='wbf'?'AKP':'PPP','jawatan'=>$name==='wbf'?'Pembantu Khidmat Am':'Guru',
       'pentadbir'=>0,'aktif'=>1
    ];
}
$GLOBALS['users']['admin@example.test']=[
  'emel'=>'admin@example.test','nama'=>'ADMIN','kategori'=>'Pengurusan','jawatan'=>'Pengetua','pentadbir'=>1,'aktif'=>1
];
$make=static fn(string $email,?string $in,?string $out,string $source,string $status='LEWAT')=>[
 'emel'=>$email,'tarikh'=>'2026-11-05','masuk'=>$in,'balik'=>$out,
 'masuk2'=>null,'balik2'=>null,'sumber'=>$source,'status'=>$status,'statuswaktu'=>$status==='LEWAT'?'LEWAT':''
];
$GLOBALS['attendance']=[
    $make('autopunch@example.test','2026-11-05 07:57:00',null,'AUTO_TIDAK_HADIR'),
    $make('no-punch@example.test',null,null,'AUTO_TIDAK_HADIR'),
    $make('historic@example.test','2026-11-05 08:00:00',null,'AUTO_TIDAK_HADIR'),
    $make('wbf@example.test','2026-11-05 08:15:00','2026-11-05 15:35:00','PHP_MYSQL','HADIR'),
    $make('covered@example.test','2026-11-05 08:00:00',null,'PHP_MYSQL'),
    $make('manual@example.test','2026-11-05 09:00:00',null,'ADMIN_MANUAL'),
    $make('ack@example.test','2026-11-05 08:00:00',null,'PHP_MYSQL')
];
$GLOBALS['history']=[];
foreach(array_keys($GLOBALS['users']) as $email) {
    $GLOBALS['history'][$email]=[[
      'berkuatkuasapada'=>46278,'sesi1masuk'=>'07:30','sesi1keluar'=>'16:30',
      'sesi2masuk'=>null,'sesi2keluar'=>null,'wbfenabled'=>0,'layakwbfkhamis'=>0
    ]];
}
$GLOBALS['history']['historic@example.test'][0]['sesi1masuk']='08:30';
$GLOBALS['history']['wbf@example.test'][0]=[
  'berkuatkuasapada'=>46278,'sesi1masuk'=>'08:30','sesi1keluar'=>'16:30',
  'sesi2masuk'=>null,'sesi2keluar'=>null,'wbfenabled'=>1,'layakwbfkhamis'=>1,
  'wbfmasukmula'=>0.3125,'wbfmasukakhir'=>0.375,
  'wbfkeluarmula'=>0.625,'wbfkeluarakhir'=>0.6875,'wbfminit'=>450
];
$GLOBALS['requests']=[[
  'emel'=>'covered@example.test','status'=>'MENUNGGU','mod'=>'KEBERADAAN',
  'tarikhmula'=>'2026-11-05','tarikhakhir'=>'2026-11-05',
  'masamula'=>'07:30','masaakhir'=>'08:30'
]];
$GLOBALS['saved']=[[
 'id'=>'SW-ALREADY-ACKNOWLEDGED','emel'=>'ack@example.test','tarikh'=>'2026-11-05',
 'jenis'=>'LEWAT','sesi'=>1,'statussemakan'=>'DIAMBIL MAKLUM'
]];
$GLOBALS['emails']=[];
$GLOBALS['historyReads']=[];
function rows(string $sql,array $args=[]):array {
    if(str_contains($sql,'FROM pengguna'))return array_values($GLOBALS['users']);
    if(str_contains($sql,'FROM tidak_hadir'))return $GLOBALS['requests'];
    if(str_contains($sql,'FROM sejarah_jadual')){
        $GLOBALS['historyReads'][$args[0]]=($GLOBALS['historyReads'][$args[0]]??0)+1;
        return $GLOBALS['history'][$args[0]]??[];
    }
    if(str_contains($sql,'FROM kehadiran'))
        return $args[0]==='2026-11-05'?$GLOBALS['attendance']:[];
    throw new RuntimeException('Unexpected query: '.$sql);
}
function one(string $sql,array $args=[]):?array {
    if(str_contains($sql,'GET_LOCK'))return ['locked'=>1];
    if(str_contains($sql,'RELEASE_LOCK'))return ['released'=>1];
    if(str_contains($sql,'FROM semakan_waktu')){
        foreach($GLOBALS['saved'] as $row)
            if($row['emel']===$args[0]&&$row['tarikh']===$args[1]&&
               $row['jenis']===$args[2]&&(int)$row['sesi']===(int)$args[3])
                return $row;
        return null;
    }
    throw new RuntimeException('Unexpected read: '.$sql);
}
function execute_sql(string $sql,array $args=[]):int {
    assert_cron(str_contains($sql,'INSERT INTO semakan_waktu'),'Cron must never change decisions or punch records');
    assert_cron(($args[11]??'')==='BELUM DIAMBIL MAKLUM','New incidents must require manual admin review');
    $GLOBALS['saved'][]=[
       'id'=>$args[0],'tarikh'=>$args[2],'emel'=>$args[3],
       'jenis'=>$args[7],'sesi'=>$args[8],'statussemakan'=>$args[11]
    ];
    return 1;
}
function enqueue_workspace_email(string $event,string $recipient,string $subject,string $body):bool {
    $GLOBALS['emails'][$event.'|'.$recipient]=true;
    return true;
}
require dirname(__DIR__).'/cron_notifications.php';
$result=mysql_time_review_jobs();
assert_cron($result['created']===2,'Expected one AUTO-source late and one WBF-aware early review, got '.json_encode($result));
assert_cron(count($GLOBALS['emails'])===2,'Only two new notifications should be queued');
$kinds=[];
foreach($GLOBALS['saved'] as $row)$kinds[$row['emel']][]=$row['jenis'];
assert_cron(($kinds['autopunch@example.test']??[])===['LEWAT'],'AUTO source with real 07:57 punch must create LEWAT review');
assert_cron(($kinds['wbf@example.test']??[])===['BALIK AWAL'],'WBF Thursday 15:35 vs 15:45 must create an early review');
foreach(['no-punch','historic','covered','manual'] as $name)
    assert_cron(!isset($kinds[$name.'@example.test']),'False review for '.$name);
assert_cron(($GLOBALS['saved'][0]['statussemakan']??'')==='DIAMBIL MAKLUM',
  'Previously acknowledged review must remain approved');
$again=mysql_time_review_jobs();
assert_cron($again['created']===0&&count($GLOBALS['emails'])===2,'Cron retry must be idempotent');
foreach($GLOBALS['historyReads'] as $email=>$reads)
    assert_cron($reads===2,'Each schedule should be queried at most once per cron run: '.$email);
echo "AUTO_SOURCE_ACTUAL_PUNCH_REVIEW_AND_HISTORICAL_WBF_PASS\n";
