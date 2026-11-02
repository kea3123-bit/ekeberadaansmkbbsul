<?php
declare(strict_types=1);
/**
 * Compact four-section monthly report built from MySQL with 2 queries for
 * staff/attendance, not 31 expensive repeated admin dashboard queries.
 * Does not use Google Sheets as a data source.
 */

/**
 * Match the legacy Thursday WBF rule for eligible AKP/Pengetua. In particular,
 * early arrivals before WBF_IN_FROM use the start of the allowed WBF window,
 * not their earlier clock-in time. No Google Sheets dependency.
 */
function mysql_monthly_time_minutes($time):?int {
    if(!preg_match('/^([01]\d|2[0-3]):([0-5]\d)$/',substr(trim((string)$time),0,5),$m))return null;
    return (int)$m[1]*60+(int)$m[2];
}
function mysql_monthly_time_string(int $minutes):string {
    return sprintf('%02d:%02d',intdiv($minutes,60),$minutes%60);
}
function mysql_monthly_wbf_out_reference(array $user,array $settings,string $day,string $in,string $fallback):string {
    if(strtoupper(date('D',strtotime($day)))!=='THU')return $fallback;
    if(strtoupper(trim((string)($settings['THURSDAY_WBF_ENABLED']??'TRUE')))==='FALSE')return $fallback;
    $category=strtoupper(trim((string)($user['kategori']??'')));
    $role=(string)($user['jawatan']??'');
    if($category!=='AKP'&&!preg_match('/\bPENGETUA\b/iu',$role))return $fallback;
    $actual=mysql_monthly_time_minutes($in);
    $from=mysql_monthly_time_minutes($settings['THURSDAY_WBF_IN_FROM']??'07:30');
    $until=mysql_monthly_time_minutes($settings['THURSDAY_WBF_IN_TO']??'09:00');
    $outFrom=mysql_monthly_time_minutes($settings['THURSDAY_WBF_OUT_FROM']??'15:00');
    $outUntil=mysql_monthly_time_minutes($settings['THURSDAY_WBF_OUT_TO']??'16:30');
    if(in_array(null,[$actual,$from,$until,$outFrom,$outUntil],true)
        ||$actual>$until||$from>$until||$outFrom>$outUntil)return $fallback;
    $duration=(int)($settings['THURSDAY_WBF_DURATION_MINUTES']??450);
    if($duration<1)return $fallback;
    $target=max($from,$actual)+$duration;
    return mysql_monthly_time_string(min($outUntil,max($outFrom,$target)));
}
/**
 * A submitted request explains an anomaly only when it relates to that date
 * and, for time-limited Keberadaan, overlaps the actual anomalous time range.
 * Rejected/cancelled requests do not count as an explanation.
 */
function mysql_monthly_exception_explanation(array $requests,string $day,string $type,string $reference,string $actual):string {
    $from=min((string)$reference,(string)$actual);
    $to=max((string)$reference,(string)$actual);
    foreach($requests as $r){
        if(($r['startDate']??'')>$day||($r['endDate']??'')<$day)continue;
        $status=strtoupper(trim((string)($r['status']??'')));
        if(!in_array($status,['DILULUSKAN','MENUNGGU'],true))continue;
        $mode=strtoupper(trim((string)($r['mode']??'')));
        if($mode==='TIDAK_HADIR')return 'Tidak Hadir: '.trim((string)($r['type']??'Permohonan')).($status==='MENUNGGU'?' (Menunggu)':'');
        if($mode!=='KEBERADAAN')continue;
        $start=substr(trim((string)($r['startTime']??'')),0,5);
        $end=substr(trim((string)($r['endTime']??'')),0,5);
        if(mysql_monthly_time_minutes($start)===null||mysql_monthly_time_minutes($end)===null||$start>=$end)continue;
        if($start<=$to&&$end>=$from)
            return 'Keberadaan: '.trim((string)($r['type']??'Permohonan')).' ('.$start.'–'.$end.')'.($status==='MENUNGGU'?' (Menunggu)':'');
    }
    return 'TIADA PENJELASAN';
}

function mysql_monthly_report_sections(array $admin,string $from,string $to):array {
    $staff=rows('SELECT * FROM pengguna WHERE aktif=1 AND emel IS NOT NULL ORDER BY nama');
    $attendance=rows('SELECT * FROM kehadiran WHERE tarikh BETWEEN ? AND ? ORDER BY _row_id',[$from,$to]);
    $byDay=[];
    foreach($attendance as $item) {
        $day=date_key($item['tarikh']??'');
        $email=strtolower(trim((string)($item['emel']??'')));
        $byDay[$day][$email]=$item; // last physical record wins on duplicate import
    }
    $absence=all_absence_rows();
    $absentByUser=[];
    $requestsByUser=[];
    foreach($absence as $entry) {
        $requestEmail=strtolower(trim((string)($entry['email']??'')));
        if($requestEmail!=='')$requestsByUser[$requestEmail][]=$entry;
        if($entry['status']==='DILULUSKAN' && $entry['mode']==='TIDAK_HADIR')
            $absentByUser[$entry['email']][]=$entry;
    }
    $s=settings_raw();$days=[];
    for($d=$from;$d<=$to;$d=date('Y-m-d',strtotime($d.' +1 day')))$days[]=$d;
    $summary=[];$exceptions=[];
    $stats=[];$cardByUser=[];
    $workDays=array_filter(array_map('trim',explode(',',strtoupper((string)($s['WORKING_DAYS']??'SUN,MON,TUE,WED,THU')))));
    $holidayDates=[];
    if(function_exists('public_holidays_safe')){
        foreach(public_holidays_safe($from,$to) as $holiday)$holidayDates[date_key($holiday['tarikh']??'')]=true;
    }
    $workingDays=0;
    foreach($days as $day) {
        if(in_array(strtoupper(date('D',strtotime($day))),$workDays,true)&&!isset($holidayDates[$day]))$workingDays++;
    }
    foreach($staff as $user){
        $email=strtolower(trim((string)$user['emel']));
        if(!$email)continue;
        $sch=schedule($user,$s);
        $stats[$email]=['nama'=>$user['nama'],'email'=>$email,'kategori'=>$user['kategori'],
          'hadir'=>0,'lewat'=>0,'awal'=>0,'tidakHadir'=>0,'belum'=>0,
          'lewatMin'=>0,'awalMin'=>0,'keberadaan'=>0,'jawatan'=>(string)($user['jawatan']??'')];
        foreach($days as $day) {
            $r=$byDay[$day][$email]??null;
            $rec=attendance_public($r,$sch);
            $in=$rec['inTime']??'';$out=$rec['outTime']??'';
            $in2=$rec['inTime2']??'';$out2=$rec['outTime2']??'';
            $absent=false;$absenceReason='';
            if(!$in && !$in2){
                foreach($absentByUser[$email]??[] as $a)
                    if($a['startDate']<=$day && $a['endDate']>=$day){
                        $absent=true;
                        $absenceReason=trim((string)($a['type']??''));
                        $note=trim((string)($a['note']??''));
                        if($note!=='')$absenceReason.=' — '.substr($note,0,75);
                        break;
                    }
            }
            $status=trim((string)($rec['status']??''));
            if(!$in && !$in2) $status=$absent?'TIDAK HADIR':'BELUM HADIR';
            $inReference=(string)($sch['s1In']??'07:30');
            // Only the FINAL actual departure is compared, including optional
            // second-session punch. Thursday WBF overrides the ordinary OUT.
            $finalOut=$out2!==''?$out2:$out;
            $ordinaryOut=(string)($out2!==''?(($sch['s2Out']??'')?:($sch['s1Out']??'16:30')):($sch['s1Out']??'16:30'));
            $outReference=mysql_monthly_wbf_out_reference($user,$s,$day,$in,$ordinaryOut);
            $late=$in!=='' && $in>$inReference;
            $early=$finalOut!=='' && $finalOut<$outReference;
            if($in!==''||$in2!=='')$stats[$email]['hadir']++;
            if($late){
                $stats[$email]['lewat']++;
                $stats[$email]['lewatMin']+=max(0,(int)floor((strtotime('2000-01-01 '.$in)-strtotime('2000-01-01 '.$inReference))/60));
            }
            if($early){
                $stats[$email]['awal']++;
                $stats[$email]['awalMin']+=max(0,(int)floor((strtotime('2000-01-01 '.$outReference)-strtotime('2000-01-01 '.$finalOut))/60));
            }
            if($absent)$stats[$email]['tidakHadir']++;
            if(!$absent && !$in && !$in2)$stats[$email]['belum']++;
            if($late||$early){
                $requests=$requestsByUser[$email]??[];
                $lateExplanation=$late?mysql_monthly_exception_explanation($requests,$day,'LEWAT',$inReference,$in):'';
                $earlyExplanation=$early?mysql_monthly_exception_explanation($requests,$day,'BALIK AWAL',$finalOut,$outReference):'';
                $exceptions[]=[$day,(string)$user['nama'],$email,$late?'LEWAT':'',
                  $early?'BALIK AWAL':'',$in,$out,$in2,$out2,$lateExplanation,$earlyExplanation];
            }
            $cell=($in?:'--').'/'.($out?:'--');
            if($in2!==''||$out2!=='')$cell.=';'.($in2?:'--').'/'.($out2?:'--');
            if(!$in && !$in2){
                $dayOfWeek=strtoupper(date('D',strtotime($day)));
                $cell=$absent?('TIDAK HADIR'.($absenceReason!==''?'|'.$absenceReason:'')):(isset($holidayDates[$day])?'CUTI UMUM':
                    (!in_array($dayOfWeek,$workDays,true)?'HUJUNG MINGGU':'BELUM HADIR'));
            }elseif($late||$early) {
                $cell.=($late&&$early?'|LEWAT / BALIK AWAL':($late?'|LEWAT':'|BALIK AWAL'));
            }
            $cardByUser[$email][$day]=$cell;
        }
    }
    $presence=[];
    foreach($absence as $item) {
        if(($item['mode']??'')==='KEBERADAAN' &&
           ($item['startDate']??'')<=$to && ($item['endDate']??'')>=$from)
            $presence[strtolower(trim((string)($item['email']??'')))]=
                ($presence[strtolower(trim((string)($item['email']??'')))]??0)+1;
    }
    $bil=0;
    foreach($stats as $email=>$e) {
        $summary[]=[++$bil,$e['nama'],trim($e['jawatan'].' / '.$e['kategori'],' /'),
          $workingDays,$e['hadir'],$e['lewat'],$e['lewatMin'],$e['awal'],$e['awalMin'],
          $e['tidakHadir'],$presence[$email]??0,''];
    }
    $sections=[
      ['name'=>'RINGKASAN','headers'=>['Bil.','Nama','Jawatan / Kategori','Hari Kerja','Hari Hadir','Lewat Bil.','Lewat Min.','Balik Awal Bil.','Balik Awal Min.','Tidak Hadir','Keberadaan','Catatan'],'rows'=>$summary],
      ['name'=>'LEWAT BALIK AWAL','headers'=>['Tarikh','Nama','Emel','Lewat','Balik awal','Masuk','Balik','Masuk 2','Balik 2','Penjelasan Lewat','Penjelasan Balik Awal'],'rows'=>$exceptions]
    ];
    // Five weekly worksheets keep mobile and printed columns legible.
    foreach(array_chunk($days,7) as $chunk){
        $title='PERAKAM '.substr($chunk[0],8,2).'-'.substr(end($chunk),8,2);
        $head=array_merge(['Nama','Emel'],$chunk);
        $vals=[];
        foreach($staff as $user){
            $email=strtolower(trim((string)$user['emel']));
            $row=[(string)$user['nama'],$email];
            foreach($chunk as $day)$row[]=$cardByUser[$email][$day]??'--';
            $vals[]=$row;
        }
        $sections[]=['name'=>$title,'headers'=>$head,'rows'=>$vals];
    }
    $individual=[];
    foreach($stats as $e)$individual[]=[$e['nama'],$e['email'],$e['kategori'],$e['hadir'],
      $e['lewat'],$e['awal'],$e['tidakHadir'],$e['belum']];
    $sections[]=['name'=>'INDIVIDU','headers'=>['Nama','Emel','Kategori','Hari hadir','Lewat','Balik awal','Tidak hadir','Belum hadir'],'rows'=>$individual];
    return $sections;
}
