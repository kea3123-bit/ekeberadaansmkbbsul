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
function ek_reason_thursday_out(array $user,array $settings,string $date,string $in,string $normal):string {
    if(date('N',strtotime($date))!==4)return $normal;
    if(strtoupper((string)($settings['THURSDAY_WBF_ENABLED']??'TRUE'))==='FALSE')return $normal;
    $category=strtoupper(trim((string)($user['kategori']??'')));
    if($category!=='AKP'&&!preg_match('/\bPENGETUA\b/iu',(string)($user['jawatan']??'')))return $normal;
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
function ek_reason_incidents(array $attendance,array $user,array $settings):array {
    $events=[];$sch=schedule($user,$settings);
    $date=date_key($attendance['tarikh']??'');
    if(!preg_match('/^20\d\d-\d\d-\d\d$/',$date))return [];
    $source=strtoupper(trim((string)($attendance['sumber']??'')));
    if(str_contains($source,'AUTO_')||str_contains($source,'ADMIN'))return [];
    $in=time_text($attendance['masuk']??'');
    $out=time_text($attendance['balik']??'');
    $in2=time_text($attendance['masuk2']??'');
    $out2=time_text($attendance['balik2']??'');
    $refIn=time_text($sch['s1In']??'07:30');
    if(ek_reason_minutes($in)!==null&&ek_reason_minutes($refIn)!==null&&$in>$refIn)
        $events[]=['type'=>'LEWAT','session'=>1,'recordTime'=>$in,'referenceTime'=>$refIn];
    // Once session 2 exists, a session-1 OUT was a break, not final departure.
    $finalOut=$out2?:($in2?'':$out);
    $normalOut=time_text($out2?($sch['s2Out']?:$sch['s1Out']):$sch['s1Out']);
    $effectiveOut=ek_reason_thursday_out($user,$settings,$date,$in,$normalOut);
    if($finalOut!==''&&ek_reason_minutes($effectiveOut)!==null&&$finalOut<$effectiveOut)
        $events[]=['type'=>'BALIK AWAL','session'=>$out2?2:1,'recordTime'=>$finalOut,'referenceTime'=>$effectiveOut];
    $refIn2=time_text($sch['s2In']??'');
    if($in2!==''&&$refIn2!==''&&$in2>$refIn2)
        $events[]=['type'=>'LEWAT','session'=>2,'recordTime'=>$in2,'referenceTime'=>$refIn2];
    return $events;
}
function ek_reason_my_pending(array $user):array {
    $today=today();$from=date('Y-m-d',strtotime($today.' -7 days'));
    $settings=settings_raw();
    if(strtoupper((string)($settings['SYSTEM_MODE']??'REAL'))==='TEST')return [];
    $email=strtolower(trim((string)($user['emel']??'')));
    // Date-limited query prevents repeated historical prompts on every login.
    $records=rows('SELECT * FROM kehadiran WHERE LOWER(emel)=? AND tarikh BETWEEN ? AND ? ORDER BY tarikh DESC,_row_id DESC',[$email,$from,$today]);
    $applications=array_values(array_filter(all_absence_rows(),static fn($r)=>
        strtolower(trim((string)($r['email']??'')))===$email));
    $results=[];$seen=[];
    foreach($records as $record) {
        $date=date_key($record['tarikh']??'');
        foreach(ek_reason_incidents($record,$user,$settings) as $event) {
            $type=$event['type'];$session=$event['session'];
            $key=$date.'|'.$type.'|'.$session;
            if(isset($seen[$key]))continue;
            $seen[$key]=true;
            if(ek_reason_request_covers($applications,$date,$event['referenceTime'],$event['recordTime']))continue;
            $found=one('SELECT * FROM semakan_waktu WHERE LOWER(emel)=? AND tarikh=? AND jenis=? AND sesi=? ORDER BY _row_id DESC LIMIT 1',
                [$email,$date,$type,$session]);
            if(!$found) {
                $id='SW-MYSQL-'.str_replace('-','',$date).'-'.substr(hash('sha256',$email.'|'.$date.'|'.$type.'|'.$session),0,18);
                // The existing cron might insert at the same time; the scoped GET_LOCK
                // ensures the reader and cron do not create duplicate user records.
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
    return array_slice($results,0,10);
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
    $current=[];
    if($records)foreach(ek_reason_incidents($records,$user,settings_raw()) as $event)
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
