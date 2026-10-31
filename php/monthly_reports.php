<?php
declare(strict_types=1);
/**
 * Compact four-section monthly report built from MySQL with 2 queries for
 * staff/attendance, not 31 expensive repeated admin dashboard queries.
 * Does not use Google Sheets as a data source.
 */
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
    foreach($absence as $entry) {
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
            $absent=false;
            if(!$in && !$in2){
                foreach($absentByUser[$email]??[] as $a)
                    if($a['startDate']<=$day && $a['endDate']>=$day){$absent=true;break;}
            }
            $status=trim((string)($rec['status']??''));
            if(!$in && !$in2) $status=$absent?'TIDAK HADIR':'BELUM HADIR';
            $late=$in!=='' && $in>($sch['s1In']??'07:30');
            $early=$out!=='' && $out<($sch['s1Out']??'16:30');
            if($in!==''||$in2!=='')$stats[$email]['hadir']++;
            if($late){
                $stats[$email]['lewat']++;
                $stats[$email]['lewatMin']+=max(0,(int)floor((strtotime('2000-01-01 '.$in)-strtotime('2000-01-01 '.($sch['s1In']??'07:30')))/60));
            }
            if($early){
                $stats[$email]['awal']++;
                $stats[$email]['awalMin']+=max(0,(int)floor((strtotime('2000-01-01 '.($sch['s1Out']??'16:30'))-strtotime('2000-01-01 '.$out))/60));
            }
            if($absent)$stats[$email]['tidakHadir']++;
            if(!$absent && !$in && !$in2)$stats[$email]['belum']++;
            if($late||$early)$exceptions[]=[$day,(string)$user['nama'],$email,$late?'LEWAT':'',
              $early?'BALIK AWAL':'',$in,$out,$in2,$out2];
            $cell=($in?:'--').'/'.($out?:'--');
            if($in2!==''||$out2!=='')$cell.=';'.($in2?:'--').'/'.($out2?:'--');
            if(!$in && !$in2){
                $dayOfWeek=strtoupper(date('D',strtotime($day)));
                $cell=$absent?'TIDAK HADIR':(isset($holidayDates[$day])?'CUTI UMUM':
                    (!in_array($dayOfWeek,$workDays,true)?'HUJUNG MINGGU':'BELUM HADIR'));
            }elseif($late||$early) {
                $cell.=($late&&$early?'|LEWAT / BALIK AWAL':($late?'|LEWAT':'|BALIK AWAL'));
            }
            $cardByUser[$email][$day]=$cell;
        }
    }
    foreach($days as $day) {
        $t=['hadir'=>0,'lewat'=>0,'balikAwal'=>0,'tidakHadir'=>0,'belumHadir'=>0];
        foreach($staff as $user) {
            $email=strtolower(trim((string)$user['emel']));
            $r=$byDay[$day][$email]??null;
            $sch=schedule($user,$s);$rec=attendance_public($r,$sch);
            $in=$rec['inTime']??'';$out=$rec['outTime']??'';$in2=$rec['inTime2']??'';
            $absent=false;
            if(!$in && !$in2)foreach($absentByUser[$email]??[] as $a)
                if($a['startDate']<=$day && $a['endDate']>=$day){$absent=true;break;}
            if($in!==''||$in2!=='')$t['hadir']++;
            elseif($absent)$t['tidakHadir']++;
            else $t['belumHadir']++;
            if($in!=='' && $in>($sch['s1In']??'07:30'))$t['lewat']++;
            if($out!=='' && $out<($sch['s1Out']??'16:30'))$t['balikAwal']++;
        }
        $summary[]=[$day,count($staff),$t['hadir'],$t['lewat'],$t['balikAwal'],$t['tidakHadir'],$t['belumHadir']];
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
      ['name'=>'LEWAT BALIK AWAL','headers'=>['Tarikh','Nama','Emel','Lewat','Balik awal','Masuk','Balik','Masuk 2','Balik 2'],'rows'=>$exceptions]
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
