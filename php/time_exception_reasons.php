<?php
declare(strict_types=1);

/**
 * Self-service explanations for MySQL time exceptions.
 * No Apps Script, e-mail trigger, new cron or third-party service.
 * Keberadaan/leave coverage is checked for the specific incident interval.
 */
function ek_reason_minutes(string $time):?int {
    $time=substr(trim($time),0,5);
    if(!preg_match('/^([01]\d|2[0-3]):([0-5]\d)$/',$time,$m))return null;
    return (int)$m[1]*60+(int)$m[2];
}
function ek_reason_thursday_out(array $user,array $settings,string $date,string $in,string $normal,?bool $historicallyEligible=null):string {
    if((int)date('N',strtotime($date))!==4)return $normal;
    if(strtoupper((string)($settings['THURSDAY_WBF_ENABLED']??'TRUE'))==='FALSE')return $normal;
    $category=strtoupper(trim((string)($user['kategori']??'')));
    if($historicallyEligible===false||($historicallyEligible===null&&$category!=='AKP'&&!preg_match('/\bPENGETUA\b/iu',(string)($user['jawatan']??''))))return $normal;
    $actual=ek_reason_minutes($in);
    $start=ek_reason_minutes((string)($settings['THURSDAY_WBF_IN_FROM']??'07:30'));
    $end=ek_reason_minutes((string)($settings['THURSDAY_WBF_IN_TO']??'09:00'));
    $outStart=ek_reason_minutes((string)($settings['THURSDAY_WBF_OUT_FROM']??'15:00'));
    $outEnd=ek_reason_minutes((string)($settings['THURSDAY_WBF_OUT_TO']??'16:30'));
    if(in_array(null,[$actual,$start,$end,$outStart,$outEnd],true)
       ||$actual>$end||$start>$end||$outStart>$outEnd)return $normal;
    $duration=(int)($settings['THURSDAY_WBF_DURATION_MINUTES']??450);
    if($duration<1)return $normal;
    $target=min($outEnd,max($outStart,max($start,$actual)+$duration));
    return sprintf('%02d:%02d',intdiv($target,60),$target%60);
}
/**
 * Read the per-user dated schedule snapshots once per reason-summary / OUT check.
 * The MySQL import stores dates as Excel serials, including fractional days.
 */
function ek_reason_schedule_history(array $user):array {
    $email=strtolower(trim((string)($user['emel']??'')));
    if($email==='')return [];
    try {
        return rows('SELECT * FROM sejarah_jadual WHERE LOWER(emel)=? AND berkuatkuasapada IS NOT NULL ORDER BY berkuatkuasapada ASC,_row_id ASC',[$email]);
    } catch(PDOException $e) {
        if((int)($e->errorInfo[1]??0)===1146)return [];
        throw $e;
    }
}
function ek_reason_historic_time($raw,string $fallback):string {
    if($raw===null||trim((string)$raw)==='')return $fallback;
    if(is_numeric($raw)) {
        $minutes=((int)round((float)$raw*1440))%1440;
        if($minutes<0)$minutes+=1440;
        return sprintf('%02d:%02d',intdiv($minutes,60),$minutes%60);
    }
    $text=time_text($raw);
    return ek_reason_minutes($text)!==null?$text:$fallback;
}
/** Choose the latest historical entry effective on or before the incident day. */
function ek_reason_schedule_on_date(array $user,array $settings,string $date,array $history):array {
    $schedule=schedule($user,$settings);
    $effective=null;
    foreach($history as $entry) {
        $serial=$entry['berkuatkuasapada']??null;
        if(!is_numeric($serial)||!is_finite((float)$serial)||(float)$serial<=0)continue;
        $day=gmdate('Y-m-d',((int)floor((float)$serial)-25569)*86400);
        if($day>$date)break;
        $effective=$entry;
    }
    if(!$effective)return [$schedule,$settings,null];
    $snapshot=json_decode((string)($effective['snapshotjson']??''),true);
    if(!is_array($snapshot))$snapshot=[];
    $original=is_array($snapshot['schedule']??null)?$snapshot['schedule']:[];
    $historicalSettings=is_array($snapshot['timingSettings']??null)?$snapshot['timingSettings']:[];
    $schedule['s1In']=ek_reason_historic_time($effective['sesi1masuk']??($original['s1In']??null),(string)$schedule['s1In']);
    $schedule['s1Out']=ek_reason_historic_time($effective['sesi1keluar']??($original['s1Out']??null),(string)$schedule['s1Out']);
    $schedule['s2In']=ek_reason_historic_time($effective['sesi2masuk']??($original['s2In']??null),'');
    $schedule['s2Out']=ek_reason_historic_time($effective['sesi2keluar']??($original['s2Out']??null),'');
    $historicSettings=array_replace($settings,$historicalSettings);
    if(($effective['wbfenabled']??null)!==null)
        $historicSettings['THURSDAY_WBF_ENABLED']=(int)$effective['wbfenabled']===1?'TRUE':'FALSE';
    foreach(['THURSDAY_WBF_IN_FROM'=>'wbfmasukmula','THURSDAY_WBF_IN_TO'=>'wbfmasukakhir',
       'THURSDAY_WBF_OUT_FROM'=>'wbfkeluarmula','THURSDAY_WBF_OUT_TO'=>'wbfkeluarakhir'] as $key=>$column) {
        if(($effective[$column]??null)!==null)
            $historicSettings[$key]=ek_reason_historic_time($effective[$column],(string)($historicSettings[$key]??''));
    }
    if(($effective['wbfminit']??null)!==null)
        $historicSettings['THURSDAY_WBF_DURATION_MINUTES']=(int)$effective['wbfminit'];
    $eligible=($effective['layakwbfkhamis']??null)!==null
       ?(int)$effective['layakwbfkhamis']===1
       :(array_key_exists('wbfEligible',$snapshot)?(bool)$snapshot['wbfEligible']:null);
    return [$schedule,$historicSettings,$eligible];
}
function ek_reason_request_covers(array $requests,string $day,string $reference,string $recorded):bool {
    $from=min($reference,$recorded);$to=max($reference,$recorded);
    foreach($requests as $r) {
        if(strtolower(trim((string)($r['status']??'')))==='ditolak')continue;
        if(!in_array(strtoupper(trim((string)($r['status']??''))),['MENUNGGU','DILULUSKAN'],true))continue;
        if((string)($r['startDate']??'')>$day||(string)($r['endDate']??'')<$day)continue;
        $mode=strtoupper(trim((string)($r['mode']??'')));
        if($mode==='TIDAK_HADIR')return true;
        if($mode!=='KEBERADAAN')continue;
        $start=substr(trim((string)($r['startTime']??'')),0,5);
        $end=substr(trim((string)($r['endTime']??'')),0,5);
        if(ek_reason_minutes($start)===null||ek_reason_minutes($end)===null||$start>=$end)continue;
        if($start<=$to&&$end>=$from)return true;
    }
    return false;
}
function ek_reason_incidents(array $attendance,array $user,array $settings,array $history=[]):array {
    $events=[];
    $date=date_key($attendance['tarikh']??'');
    if(!preg_match('/^20\\d\\d-\\d\\d-\\d\\d$/',$date))return [];
    [$sch,$effectiveSettings,$wbfEligible]=ek_reason_schedule_on_date($user,$settings,$date,$history);
    // Source/status (including AUTO_TIDAK_HADIR) must never suppress a real
    // late/early time. Only actual punch timestamps determine an incident.
    $in=time_text($attendance['masuk']??'');
    $out=time_text($attendance['balik']??'');
    $in2=time_text($attendance['masuk2']??'');
    $out2=time_text($attendance['balik2']??'');
    $refIn=time_text($sch['s1In']??'07:30');
    if(ek_reason_minutes($in)!==null&&ek_reason_minutes($refIn)!==null&&$in>$refIn)
        $events[]=['type'=>'LEWAT','session'=>1,'recordTime'=>$in,'referenceTime'=>$refIn];
    // Once session 2 exists, a session-1 OUT was a break, not final departure.
    $secondConfigured=trim((string)($sch['s2In']??''))!==''||trim((string)($sch['s2Out']??''))!=='';
    $finalOut=$out2?:($in2||$secondConfigured?'':$out);
    $normalOut=time_text($out2?(($sch['s2Out']??'')?:($sch['s1Out']??'16:30')):($sch['s1Out']??'16:30'));
    $effectiveOut=ek_reason_thursday_out($user,$effectiveSettings,$date,$in,$normalOut,$wbfEligible);
    if($finalOut!==''&&ek_reason_minutes($effectiveOut)!==null&&$finalOut<$effectiveOut)
        $events[]=['type'=>'BALIK AWAL','session'=>$out2?2:1,'recordTime'=>$finalOut,'referenceTime'=>$effectiveOut];
    $refIn2=time_text($sch['s2In']??'');
    if($in2!==''&&$refIn2!==''&&$in2>$refIn2)
        $events[]=['type'=>'LEWAT','session'=>2,'recordTime'=>$in2,'referenceTime'=>$refIn2];
    return $events;
}
/**
 * Only the exact button click which just saved a punch can initiate a
 * user-reason modal. No login, navigation, refresh or historical scan.
 */
function ek_reason_current_punch_event(array $attendance,array $user,array $settings,string $type,int $session):?array {
    $history=ek_reason_schedule_history($user);
    // A configured second shift makes first-session OUT an intermediate break.
    if($type==='OUT'&&$session===1){
        [$sch]=ek_reason_schedule_on_date($user,$settings,date_key($attendance['tarikh']??''),$history);
        if(trim((string)($sch['s2In']??''))!=='')return null;
    }
    $wanted=$type==='IN'?'LEWAT':'BALIK AWAL';
    foreach(ek_reason_incidents($attendance,$user,$settings,$history) as $event){
        if($event['type']!==$wanted||(int)$event['session']!==$session)continue;
        return ['date'=>date_key($attendance['tarikh']??''),
          'type'=>$wanted,'session'=>$session,'recordTime'=>$event['recordTime'],
          'referenceTime'=>$event['referenceTime']];
    }
    return null;
}
/**
 * Read-only owner-scoped unresolved events. No automatic creation of a
 * semakan_waktu row while checking the home notification or before punch.
 * Supports historic records since SYSTEM_START_DATE, including records whose
 * source/status was AUTO_TIDAK_HADIR but later received a real punch.
 */
function ek_reason_unresolved_for_user(array $user,string $from,string $to,?array $onlyAttendance=null):array {
    $email=strtolower(trim((string)($user['emel']??'')));
    if($email===''||$from>$to)return [];
    $settings=settings_raw();
    $history=ek_reason_schedule_history($user);
    $attendanceRows=$onlyAttendance!==null?[$onlyAttendance]:
        rows('SELECT * FROM kehadiran WHERE LOWER(emel)=? AND tarikh BETWEEN ? AND ? ORDER BY tarikh DESC,_row_id DESC',
            [$email,$from,$to]);
    $reviews=rows('SELECT * FROM semakan_waktu WHERE LOWER(emel)=? AND tarikh BETWEEN ? AND ? ORDER BY _row_id DESC',
        [$email,$from,$to]);
    $reviewByEvent=[];
    foreach($reviews as $review){
        $day=date_key($review['tarikh']??'');
        $key=$day.'|'.strtoupper(trim((string)($review['jenis']??''))).'|'.(int)($review['sesi']??1);
        if(!isset($reviewByEvent[$key]))$reviewByEvent[$key]=['id'=>(string)($review['id']??''),'reason'=>''];
        if(trim((string)($review['sebabpengguna']??''))!=='')$reviewByEvent[$key]['reason']='SUBMITTED';
    }
    $applications=array_values(array_filter(all_absence_rows(),static fn($r)=>
        strtolower(trim((string)($r['email']??'')))===$email));
    $result=[];$seen=[];
    foreach($attendanceRows as $attendance){
        $day=date_key($attendance['tarikh']??'');
        if($day<$from||$day>$to)continue;
        foreach(ek_reason_incidents($attendance,$user,$settings,$history) as $event){
            $key=$day.'|'.$event['type'].'|'.$event['session'];
            if(isset($seen[$key]))continue;
            $seen[$key]=true;
            if(ek_reason_request_covers($applications,$day,$event['referenceTime'],$event['recordTime']))continue;
            $existing=$reviewByEvent[$key]??null;
            if(($existing['reason']??'')==='SUBMITTED')continue;
            $result[]=[
                'id'=>(string)($existing['id']??''),
                'date'=>$day,'type'=>$event['type'],'session'=>(int)$event['session'],
                'recordTime'=>$event['recordTime'],'referenceTime'=>$event['referenceTime']
            ];
        }
    }
    usort($result,static fn($a,$b)=>strcmp($b['date'].'|'.$b['recordTime'],$a['date'].'|'.$a['recordTime']));
    return $result;
}
function ek_reason_my_summary(array $user):array {
    $today=today();$settings=settings_raw();
    if(strtoupper((string)($settings['SYSTEM_MODE']??'REAL'))==='TEST')
        return ['rows'=>[],'pendingCount'=>0,'pendingDays'=>0,'pastDays'=>0,'todayCount'=>0];
    $from=date_key($settings['SYSTEM_START_DATE']??'2026-01-01');
    if(!preg_match('/^20\d\d-\d\d-\d\d$/',$from)||$from>$today)$from=$today;
    $events=ek_reason_unresolved_for_user($user,$from,$today);
    $distinct=[];$oldDates=[];$todayCount=0;
    foreach($events as $e){
        $distinct[$e['date']]=true;
        if($e['date']<$today)$oldDates[$e['date']]=true;
        else $todayCount++;
    }
    return [
        'rows'=>$events,
        'pendingCount'=>count($events),
        'pendingDays'=>count($distinct),
        'pastDays'=>count($oldDates),
        'todayCount'=>$todayCount,
        'today'=>$today
    ];
}
/** Server-side guard: force an explanation of today's open incidents before OUT. */
function ek_reason_requires_before_out(array $user,string $date,?array $attendance):array {
    if(!$attendance)return [];
    $settings=settings_raw();
    if(strtoupper((string)($settings['SYSTEM_MODE']??'REAL'))==='TEST')return [];
    return ek_reason_unresolved_for_user($user,$date,$date,$attendance);
}

function ek_reason_my_pending(array $user,array $trigger=[]):array {
    $today=today();
    $settings=settings_raw();
    if(strtoupper((string)($settings['SYSTEM_MODE']??'REAL'))==='TEST')return [];
    // A button press is required. Ignore requests without an exact
    // same-day event supplied by the punch response.
    $targetDate=(string)($trigger['date']??'');
    $targetType=(string)($trigger['type']??'');
    $targetSession=(int)($trigger['session']??0);
    $targetTime=(string)($trigger['recordTime']??'');
    $systemStart=date_key($settings['SYSTEM_START_DATE']??'2026-01-01');
    if(!preg_match('/^20\d\d-\d\d-\d\d$/',$targetDate)||$targetDate>$today||
      $targetDate<$systemStart||
      !in_array($targetType,['LEWAT','BALIK AWAL'],true)||
      !in_array($targetSession,[1,2],true)||ek_reason_minutes($targetTime)===null)return [];
    $email=strtolower(trim((string)($user['emel']??'')));
    $latest=attendance_row($email,$targetDate);
    $records=$latest?[$latest]:[];
    $history=ek_reason_schedule_history($user);
    $applications=array_values(array_filter(all_absence_rows(),static fn($r)=>
        strtolower(trim((string)($r['email']??'')))===$email));
    $results=[];$seen=[];
    foreach($records as $record) {
        $date=date_key($record['tarikh']??'');
        foreach(ek_reason_incidents($record,$user,$settings,$history) as $event) {
            $type=$event['type'];$session=$event['session'];
            if($date!==$targetDate||$type!==$targetType||
               (int)$session!==$targetSession||$event['recordTime']!==$targetTime)continue;
            $key=$date.'|'.$type.'|'.$session;
            if(isset($seen[$key]))continue;
            $seen[$key]=true;
            if(ek_reason_request_covers($applications,$date,$event['referenceTime'],$event['recordTime']))continue;
            $found=one('SELECT * FROM semakan_waktu WHERE LOWER(emel)=? AND tarikh=? AND jenis=? AND sesi=? ORDER BY _row_id DESC LIMIT 1',
                [$email,$date,$type,$session]);
            if(!$found) {
                $id='SW-MYSQL-'.str_replace('-','',$date).'-'.substr(hash('sha256',$email.'|'.$date.'|'.$type.'|'.$session),0,18);
                // Guard duplicate requests from multiple simultaneous user sessions.
                // The existing cron can also create a matching event; recheck
                // under the lock and reuse any matching row.
                $lock='eke_reason_'.substr(hash('sha256',$key.'|'.$email),0,40);
                $locked=one('SELECT GET_LOCK(?,3) AS locked',[$lock]);
                if((int)($locked['locked']??0)!==1)continue;
                try {
                    $found=one('SELECT * FROM semakan_waktu WHERE LOWER(emel)=? AND tarikh=? AND jenis=? AND sesi=? ORDER BY _row_id DESC LIMIT 1',
                        [$email,$date,$type,$session]);
                    if(!$found) {
                        execute_sql('INSERT INTO semakan_waktu (_source_row,id,diciptapada,tarikh,emel,nama,jawatan,kategori,jenis,sesi,wakturekod,wakturujukan,statussemakan) VALUES (0,?,?,?,?,?,?,?,?,?,?,?,?)',
                          [$id,excel_number(now_myt()),$date,$email,(string)($user['nama']??''),(string)($user['jawatan']??''),(string)($user['kategori']??''),$type,$session,excel_number($date.' '.$event['recordTime'].':00'),excel_number($date.' '.$event['referenceTime'].':00'),'BELUM DIAMBIL MAKLUM']);
                        $found=['id'=>$id,'sebabpengguna'=>''];
                    }
                } finally {one('SELECT RELEASE_LOCK(?) AS released',[$lock]);}
            }
            if(trim((string)($found['sebabpengguna']??''))!=='')continue;
            $results[]=['id'=>(string)$found['id'],'date'=>$date,'type'=>$type,'session'=>$session,
                'recordTime'=>$event['recordTime'],'referenceTime'=>$event['referenceTime']];
        }
    }
    return array_slice($results,0,1);
}
function ek_reason_save(array $user,string $id,string $reason):array {
    $id=trim($id);$reason=trim(preg_replace('/\s+/u',' ',$reason)??'');
    $length=function_exists('mb_strlen')?mb_strlen($reason,'UTF-8'):strlen($reason);
    if($length<10||$length>800)throw new InvalidArgumentException('Nyatakan sebab antara 10 hingga 800 aksara.');
    $email=strtolower(trim((string)($user['emel']??'')));
    $item=one('SELECT * FROM semakan_waktu WHERE id=? AND LOWER(emel)=? ORDER BY _row_id DESC LIMIT 1',[$id,$email]);
    if(!$item)throw new InvalidArgumentException('Rekod semakan bukan milik akaun anda.');
    if(trim((string)($item['sebabpengguna']??''))!=='')
        throw new InvalidArgumentException('Sebab telah dihantar. Rekod tidak boleh dihantar dua kali.');
    // Use the current coverage rules at submission time too: leave may have
    // been created/approved after the popup was opened.
    $day=date_key($item['tarikh']??'');
    $records=attendance_row($email,$day);
    $history=ek_reason_schedule_history($user);
    $current=[];
    if($records)foreach(ek_reason_incidents($records,$user,settings_raw(),$history) as $event)
        if($event['type']===(string)$item['jenis']&&(int)$event['session']===(int)$item['sesi'])$current[]=$event;
    if(!$current)throw new InvalidArgumentException('Rekod waktu telah berubah. Sila segar semula.');
    $requests=array_values(array_filter(all_absence_rows(),static fn($r)=>
       strtolower(trim((string)($r['email']??'')))===$email));
    if(ek_reason_request_covers($requests,$day,$current[0]['referenceTime'],$current[0]['recordTime']))
       throw new InvalidArgumentException('Permohonan Keberadaan/Tidak Hadir sudah meliputi waktu ini.');
    $n=execute_sql("UPDATE semakan_waktu SET sebabpengguna=?,sebabdihantarpada=NOW() WHERE id=? AND LOWER(emel)=? AND (sebabpengguna IS NULL OR sebabpengguna='')",
        [$reason,$id,$email]);
    if($n<1)throw new RuntimeException('Sebab telah dihantar pada peranti lain. Sila segar semula.');
    audit_event($email,'HANTAR_SEBAB_WAKTU',$id,'Alasan sendiri dihantar untuk semakan '.$item['jenis']);
    return ['ok'=>true,'id'=>$id,'message'=>'Sebab berjaya dihantar untuk semakan pentadbir.'];
}
