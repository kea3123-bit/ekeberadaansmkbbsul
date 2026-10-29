<?php
declare(strict_types=1);

/** Regression: admin list must not run 1 SQL lookup per staff member. */
$source=(string)file_get_contents(dirname(__DIR__).'/_lib.php');
$start=strpos($source,'function public_user(');
$end=$start===false?false:strpos($source,"\nfunction settings_raw(",$start);
if($start===false||$end===false)throw new RuntimeException('public_user/public_users_bulk not found');
eval(substr($source,$start,$end-$start));

$queryCount=0;$singleCount=0;
function rows(string $sql,array $args=[]):array {
    global $queryCount;
    if(strpos($sql,'FROM web_auth')===false)throw new RuntimeException('Unexpected SQL query');
    $queryCount++;
    return [['email'=>'user00@example.test','must_change_pin'=>0]];
}
function one(string $sql,array $args=[]):?array {
    global $singleCount;
    $singleCount++;
    return null;
}
$users=[];
for($i=0;$i<70;$i++){
    $users[]=[
      'emel'=>sprintf('user%02d@example.test',$i),
      'nama'=>'Staf '.$i,
      'aktif'=>1,'kategori'=>'AKP','pentadbir'=>0,
      'authtype'=>$i===2?'PIN_V1':'',
      'passwordsalt'=>$i===2?'salt':'',
      'passwordhash'=>$i===2?'hash':''
    ];
}
$converted=public_users_bulk($users);
if(count($converted)!==70)throw new RuntimeException('Missing converted staff');
if($queryCount!==1||$singleCount!==0)throw new RuntimeException('Unexpected per-user SQL lookups');
if(!$converted[0]['pinSet'] || $converted[0]['authType']!=='PHP_PIN_V1')throw new RuntimeException('PHP PIN lost');
if(!$converted[2]['pinSet'] || $converted[2]['authType']!=='PIN_V1')throw new RuntimeException('Legacy PIN migration metadata lost');
if($converted[1]['pinSet'])throw new RuntimeException('Unprovisioned account incorrectly has PIN');
public_users_bulk($users);
if($queryCount!==1||$singleCount!==0)throw new RuntimeException('Monthly export repeated PIN SQL lookup');
echo "PASS: 70 staff, one auth query across repeated admin reports; PIN metadata unchanged\n";
