<?php
declare(strict_types=1);
$source=file_get_contents(dirname(__DIR__).'/api.php');
$start=strpos($source,'function progressive_punch_radius(');
$end=strpos($source,'function punch_mysql(', $start);
if($start===false||$end===false)throw new RuntimeException('Progressive radius helper is missing');
eval(substr($source,$start,$end-$start));
function check(bool $good,string $label):void {if(!$good)throw new RuntimeException($label);}
$cases=[
 [90.0,0.0,true,90],[90,89.5,true,90],[90,90,true,90],
 [90,90.01,true,100],[90,99.99,true,100],[90,100,true,100],
 [90,100.001,true,110],[90,109.99,true,110],
 [90,114.0,true,120],[90,120,true,120],
 [90,120.1,true,130],[90,139.999,true,140],[90,140,true,140],
 [90,140.001,false,140],[90,160,false,140],
 [115,115,true,115],[115,115.1,true,125],[115,126,true,135],
 [115,138,true,140],[115,141,false,140],
 [135,139,true,140],[135,141,false,140],
 [140,140,true,140],[140,140.01,false,140],
 [160,160,true,160],[160,160.01,false,160]
];
foreach($cases as [$base,$distance,$allowed,$stage]) {
    $x=progressive_punch_radius((float)$distance,(float)$base);
    check($x['allowed']===$allowed,"Incorrect acceptance for $distance / $base");
    check(abs($x['usedRadiusM']-$stage)<0.00001,"Incorrect stage for $distance / $base");
    check($x['extended']===($stage>$base),"Incorrect progressive audit flag for $distance / $base");
}
try {progressive_punch_radius(INF,90);throw new RuntimeException('Infinity allowed');}
catch(InvalidArgumentException $e) {}
try {progressive_punch_radius(-1,90);throw new RuntimeException('Negative distance allowed');}
catch(InvalidArgumentException $e) {}
$server=substr($source,strpos($source,'function punch_mysql('),strpos($source,'/**',$start+1000)-strpos($source,'function punch_mysql('));
check(str_contains($source,'$radiusDecision=progressive_punch_radius($measuredDistance,'),
    'Server punch must compute progressive allowance using actual distance');
check(str_contains($source,'if(!$radiusDecision[\'allowed\'])'),
    'Server punch must reject beyond maximum');
check(str_contains($source,"\$accuracy>(float)(\$s['MAX_GPS_ACCURACY_M']??120)"),
    'GPS accuracy limit must remain enforced separately');
check(str_contains($source,'\'usedRadiusM\'=>$radiusDecision[\'usedRadiusM\']'),
    'Response should expose server-selected stage');
check(str_contains($source,"'mode='.("),
    'Audit event must distinguish normal versus progressive allowance');
check(str_contains($source,'SEBAB_WAKTU_DIPERLUKAN'),
    'Time reason OUT requirement must remain in place');
echo "PROGRESSIVE_GPS_RADIUS_SERVER_10M_TO_140M_OK\n";
