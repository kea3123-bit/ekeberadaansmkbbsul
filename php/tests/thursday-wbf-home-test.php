<?php
declare(strict_types=1);
/**
 * No network or database: verify WBF from PHP used for live boot and punch.
 */
require dirname(__DIR__).'/_lib.php';
function testWbf(bool $value,string $label):void {
    if(!$value)throw new RuntimeException($label);
}
$settings=[
 'DEFAULT_S1_IN'=>'07:30','DEFAULT_S1_OUT'=>'16:30','THURSDAY_WBF_ENABLED'=>'TRUE',
 'THURSDAY_WBF_IN_FROM'=>'07:30','THURSDAY_WBF_IN_TO'=>'09:00',
 'THURSDAY_WBF_OUT_FROM'=>'15:00','THURSDAY_WBF_OUT_TO'=>'16:30',
 'THURSDAY_WBF_DURATION_MINUTES'=>'450'
];
$akp=['emel'=>'akp@example.test','nama'=>'AKP','kategori'=>'AKP','jawatan'=>'Pembantu Khidmat Am',
 'sesi1masuk'=>'','sesi1keluar'=>'','waktulewat'=>'','waktubalik'=>'','sesi2masuk'=>'','sesi2keluar'=>'','maksmasuk'=>''];
$pengetua=$akp;$pengetua['kategori']='Pengurusan';$pengetua['jawatan']='Pengetua';
$teacher=$akp;$teacher['kategori']='PPP';$teacher['jawatan']='Guru';
testWbf(wbf_thursday_out_reference($akp,$settings,'2026-11-05','08:54')==='16:24',
 '08:54 + 450min should return 16:24 on Thursday (MYT)');
testWbf(wbf_thursday_out_reference($akp,$settings,'2026-11-05','07:18')==='15:00',
 'Arrival before WBF 07:30 must use earliest 15:00 out');
testWbf(wbf_thursday_out_reference($pengetua,$settings,'2026-11-05','08:15')==='15:45',
 'Pengetua should be eligible for WBF');
testWbf(wbf_thursday_out_reference($teacher,$settings,'2026-11-05','08:15')==='',
 'PPP must not inherit AKP WBF rule');
testWbf(wbf_thursday_out_reference($akp,$settings,'2026-11-06','08:15')==='',
 'WBF must not apply on Friday');
testWbf(wbf_thursday_out_reference($akp,$settings,'2026-11-05','09:10')==='',
 'Arrival after permitted window uses regular schedule');
testWbf(wbf_thursday_out_reference($akp,$settings,'2026-11-05','')==='',
 'No punch means no invented WBF departure');
$pending=schedule_for_attendance($akp,$settings,'2026-11-05',null);
testWbf($pending['wbfActive']&&$pending['wbfPending']&&!$pending['wbfApplied'],
 'Thursday eligible user needs an explicit pending badge before punching');
testWbf($pending['wbfOutWindow']==='15:00–16:30',
 'Show configured WBF window while waiting for first punch');
$record=['tarikh'=>'2026-11-05','masuk'=>'2026-11-05 08:54:00'];
$active=schedule_for_attendance($akp,$settings,'2026-11-05',$record);
testWbf($active['wbfApplied']&&$active['s1Out']==='16:24'&&$active['punchOutFrom']==='16:24',
 'Bootstrap/Punch must expose exact WBF effective out reference');
testWbf(!('BALIK AWAL'===($record['status']??'')),'Do not assign status in read-only schedule helper');
$settings['THURSDAY_WBF_ENABLED']='FALSE';
$off=schedule_for_attendance($akp,$settings,'2026-11-05',$record);
testWbf(!$off['wbfActive']&&$off['s1Out']==='16:30','Disabled WBF must stay normal');
$settings['THURSDAY_WBF_ENABLED']='TRUE';
$lateArrival=schedule_for_attendance($akp,$settings,'2026-11-05',['masuk'=>'2026-11-05 09:10:00']);
testWbf($lateArrival['wbfActive']&&!$lateArrival['wbfApplied']&&!$lateArrival['wbfPending']
  &&$lateArrival['s1Out']==='16:30','Invalid WBF window must not silently grant flex time');
$numeric=schedule_for_attendance($akp,$settings,'2026-11-05',['masuk'=>excel_number('2026-11-05 08:54:30')]);
testWbf($numeric['s1Out']==='16:24','Excel numeric times must be handled');
echo "THURSDAY_WBF_HOME_SCHEDULE_TESTS_OK\n";
