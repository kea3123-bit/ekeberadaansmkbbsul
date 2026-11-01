<?php
declare(strict_types=1);
/**
 * Conservative MySQL-only attendance finalization.
 * The existing mail cron calls this; no extra cPanel cron is necessary.
 * Called AFTER the normal scheduler and BEFORE sending queued mail.
 * Never reads or writes historical Google Sheets.
 */
function run_mysql_attendance_jobs():array {
    $result=['marked'=>0,'presenceAlerts'=>0,'waiting'=>0,'skipped'=>0];
    try {
        $s=settings_raw();
        if(strtoupper((string)($s['SYSTEM_MODE']??'REAL'))==='TEST')return $result;
        $date=today();$clock=substr(now_myt(),11,5);
        if(!mysql_school_day($date,$s))return $result;
        $deadline=time_text($s['ABSENT_AFTER']??'10:00')?:'10:00';
        $requests=mysql_active_requests_on($date);
        $existing=[];
        foreach(rows('SELECT emel,masuk,masuk2,status FROM kehadiran WHERE tarikh=? ORDER BY _row_id',[$date]) as $r)
            $existing[strtolower(trim((string)$r['emel']))]=$r;
        $adminEmails=[];
        foreach(rows("SELECT emel FROM pengguna WHERE aktif=1 AND (pentadbir=1 OR kategori='Pengurusan')") as $a){
            $email=strtolower(trim((string)($a['emel']??'')));
            if(filter_var($email,FILTER_VALIDATE_EMAIL))$adminEmails[$email]=true;
        }
        foreach(rows('SELECT emel,nama,kategori FROM pengguna WHERE aktif=1') as $u){
            $email=strtolower(trim((string)($u['emel']??'')));
            if(!filter_var($email,FILTER_VALIDATE_EMAIL))continue;
            $r=$existing[$email]??null;
            if($r&&(!empty($r['masuk'])||!empty($r['masuk2'])||
                    strtoupper((string)($r['status']??''))==='TIDAK HADIR'))continue;
            $absent=false;$presence=[];
            foreach($requests[$email]??[] as $req){
                $mode=strtoupper(trim((string)($req['mod']??'TIDAK_HADIR')));
                if($mode!=='KEBERADAAN'){$absent=true;break;}
                $presence[]=$req;
            }
            if($absent){$result['skipped']++;continue;}
            if($presence){
                // Pending and approved presence must not be mislabeled before the
                // specified end time, even if ABSENT_AFTER has passed.
                $end='';$allApproved=true;
                foreach($presence as $req){
                    if(strtoupper((string)($req['status']??''))!=='DILULUSKAN')$allApproved=false;
                    $time=time_text($req['masaakhir']??'');
                    if($time==='')$allApproved=false;
                    if($time>$end)$end=$time;
                }
                if(!$allApproved||$clock<$end){$result['waiting']++;continue;}
                if(!$adminEmails){$result['waiting']++;continue;}
                $event='presence-no-punch:'.$date.':'.$email;
                $complete=true;
                foreach(array_keys($adminEmails) as $recipient){
                    $body="Keberadaan tamat tanpa Punch Masuk\nNama: ".(string)$u['nama'].
                        "\nTarikh: ".$date."\nWaktu tamat Keberadaan: ".$end.
                        "\nSemak dalam eKeberadaan: https://kea3123-bit.github.io/ekeberadaansmkbbsul/";
                    enqueue_workspace_email($event,$recipient,'eKeberadaan: Tamat Keberadaan tanpa Punch Masuk',$body);
                    $key=hash('sha256',$event.'|'.$recipient);
                    $sent=one('SELECT status FROM ek_email_outbox WHERE dedupe_key=? LIMIT 1',[$key]);
                    if(strtolower((string)($sent['status']??''))!=='sent')$complete=false;
                    $result['presenceAlerts']++;
                }
                if(!$complete){$result['waiting']++;continue;}
            }elseif($clock<$deadline){continue;}
            // Same per-user/date advisory lock as punch_mysql(): prevents
            // insertion racing a real punch. Punch later overwrites auto status.
            $lock='ek_punch_'.hash('sha256',$email.'|'.$date);
            $granted=one('SELECT GET_LOCK(?,1) AS locked',[$lock]);
            if((int)($granted['locked']??0)!==1)continue;
            try {
                db()->beginTransaction();
                $current=attendance_row($email,$date);
                if($current && (!empty($current['masuk'])||!empty($current['masuk2'])
                    || strtoupper((string)($current['status']??''))==='TIDAK HADIR')){
                    db()->commit();continue;
                }
                if($current){
                    execute_sql("UPDATE kehadiran SET status='TIDAK HADIR',sumber='AUTO_TIDAK_HADIR',
                         dikemaskinipada=? WHERE _row_id=?",
                         [excel_number(now_myt()),$current['_row_id']]);
                }else{
                    execute_sql("INSERT INTO kehadiran (_source_row,tarikh,emel,nama,kategori,status,sumber,dikemaskinipada)
                         VALUES (0,?,?,?,?,?,?,?)",[
                         $date,$email,(string)$u['nama'],(string)$u['kategori'],
                         'TIDAK HADIR','AUTO_TIDAK_HADIR',excel_number(now_myt())
                    ]);
                }
                db()->commit();$result['marked']++;
            }catch(Throwable $e){
                if(db()->inTransaction())db()->rollBack();
                error_log('[eKeberadaan attendance] Auto absence failed ('.get_class($e).').');
            }finally{
                one('SELECT RELEASE_LOCK(?) AS released',[$lock]);
            }
        }
    }catch(Throwable $e){
        error_log('[eKeberadaan attendance] Scheduled attendance unavailable ('.get_class($e).').');
    }
    return $result;
}
