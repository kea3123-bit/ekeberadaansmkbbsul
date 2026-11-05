<?php
declare(strict_types=1);
/**
 * Rebuild time-review notifications only from MySQL punches.
 * Runs in existing cPanel mail cron; never accesses Google Sheets.
 * IDs and outbox dedupe keys are deterministic across retries.
 */
function mysql_review_event_id(string $email,string $day,string $type,int $session):string {
    return 'SW-MYSQL-'.str_replace('-','',$day).'-'.substr(hash('sha256',strtolower($email).'|'.$day.'|'.$type.'|'.$session),0,18);
}
function mysql_time_review_jobs():array {
    $result=['created'=>0,'queued'=>0,'skipped'=>0];
    $s=settings_raw();
    if(strtoupper((string)($s['SYSTEM_MODE']??'REAL'))==='TEST')return $result;
    $lockName='eke_mysql_time_review_cron';
    $lock=one('SELECT GET_LOCK(?,0) AS locked',[$lockName]);
    if((int)($lock['locked']??0)!==1)return $result;
    try {
        $today=today();
        $dates=[$today,date('Y-m-d',strtotime($today.' -1 day'))];
        $start=date_key($s['SYSTEM_START_DATE']??'2026-01-01');
        $employees=[];
        $adminEmails=[];
        foreach(rows('SELECT * FROM pengguna WHERE aktif=1') as $u) {
            $email=strtolower(trim((string)($u['emel']??'')));
            if(!filter_var($email,FILTER_VALIDATE_EMAIL))continue;
            $employees[$email]=$u;
            if((int)($u['pentadbir']??0)===1)$adminEmails[$email]=true;
        }
        // Use the same dated schedule + WBF rules as the user's reason popup.
        // A row with source AUTO_TIDAK_HADIR may later receive a real punch.
        require_once __DIR__.'/time_exception_reasons.php';
        $histories=[];
        // Keep exemptions aligned with the user's reason notification; a
        // matching pending/approved absence/presence must not generate a review.
        $requestsByEmail=[];
        foreach(rows("SELECT emel,status,`mod`,tarikhmula,tarikhakhir,masamula,masaakhir
            FROM tidak_hadir WHERE status IN ('MENUNGGU','DILULUSKAN')") as $request){
            $requestEmail=strtolower(trim((string)($request['emel']??'')));
            if($requestEmail==='')continue;
            $requestsByEmail[$requestEmail][]=[
                'status'=>(string)($request['status']??''),
                'mode'=>(string)($request['mod']??'TIDAK_HADIR'),
                'startDate'=>date_key($request['tarikhmula']??''),
                'endDate'=>date_key($request['tarikhakhir']??''),
                'startTime'=>time_text($request['masamula']??''),
                'endTime'=>time_text($request['masaakhir']??'')
            ];
        }
        foreach($dates as $day){
            if($day<$start)continue;
            $latest=[];
            foreach(rows('SELECT * FROM kehadiran WHERE tarikh=? ORDER BY _row_id',[$day]) as $r){
                $email=strtolower(trim((string)($r['emel']??'')));
                if(isset($employees[$email]))$latest[$email]=$r;
            }
            foreach($latest as $email=>$r){
                $source=strtoupper(trim((string)($r['sumber']??'')));
                // Manual admin corrections are intentionally not new punches.
                // AUTO_TIDAK_HADIR is only a source label, not proof of absence:
                // accept it when an actual punch timestamp exists.
                if(str_contains($source,'ADMIN'))continue;
                $hasPunch=false;
                foreach(['masuk','balik','masuk2','balik2'] as $field){
                    if(time_text($r[$field]??'')!==''){$hasPunch=true;break;}
                }
                if(!$hasPunch)continue;
                $person=$employees[$email];
                if(!array_key_exists($email,$histories))
                    $histories[$email]=ek_reason_schedule_history($person);
                foreach(ek_reason_incidents($r,$person,$s,$histories[$email]) as $incident){
                    $type=$incident['type'];
                    $session=(int)$incident['session'];
                    $clock=$incident['recordTime'];
                    $reference=$incident['referenceTime'];
                    if(ek_reason_request_covers($requestsByEmail[$email]??[],$day,$reference,$clock))
                        continue;
                    $id=mysql_review_event_id($email,$day,$type,$session);
                    $found=one('SELECT id,statussemakan FROM semakan_waktu WHERE emel=? AND tarikh=? AND jenis=? AND sesi=? ORDER BY _row_id DESC LIMIT 1',
                        [$email,$day,$type,$session]);
                    if(!$found) {
                        // GET_LOCK serializes this job with parallel cron instances.
                        execute_sql('INSERT INTO semakan_waktu (_source_row,id,diciptapada,tarikh,emel,nama,jawatan,kategori,jenis,sesi,wakturekod,wakturujukan,statussemakan)
                            VALUES (0,?,?,?,?,?,?,?,?,?,?,?,?)',
                            [$id,excel_number(now_myt()),$day,$email,(string)$person['nama'],(string)($person['jawatan']??''),
                             (string)($person['kategori']??''),$type,$session,
                             excel_number($day.' '.$clock.':00'),excel_number($day.' '.$reference.':00'),
                             'BELUM DIAMBIL MAKLUM']);
                        $result['created']++;
                    }else{
                        $id=(string)$found['id'];
                        // Don't resend imported historical or completed reviews.
                        if(!str_starts_with($id,'SW-MYSQL-')||
                            strtoupper((string)($found['statussemakan']??''))!=='BELUM DIAMBIL MAKLUM'){
                            $result['skipped']++;continue;
                        }
                    }
                    foreach(array_keys($adminEmails) as $recipient) {
                        if(enqueue_workspace_email('time-review:'.$id,$recipient,
                            'eKeberadaan: Semakan '.$type.' — '.$day,
                            'Rekod masa memerlukan perhatian Pentadbir Sistem.'."\n".
                            'Nama: '.(string)$person['nama']."\n".
                            'Tarikh: '.$day."\n".
                            'Jenis: '.$type."\n".
                            'Sesi: '.$session."\n".
                            'Masa direkod: '.$clock."\n".
                            'Masa rujukan: '.$reference."\n".
                            'Semak di https://kea3123-bit.github.io/ekeberadaansmkbbsul/'))
                            $result['queued']++;
                    }
                }
            }
        }
    }catch(Throwable $e){
        error_log('[eKeberadaan cron] MySQL semakan waktu failed ('.get_class($e).').');
    }finally{
        one('SELECT RELEASE_LOCK(?) AS released',[$lockName]);
    }
    return $result;
}
/**
 * One aggregate alert per day to admins. Does NOT automatically resend dead mail;
 * avoids copying recipients/body or leaking sensitive error details.
 */
function mysql_dead_mail_monitor():array {
    $s=settings_raw();
    $r=['dead'=>0,'queued'=>0,'backlog'=>0];
    try{
        $dead=one("SELECT COUNT(*) AS n FROM ek_email_outbox WHERE status='dead'
            AND subject NOT LIKE 'eKeberadaan: Amaran queue emel%'");
        $backlog=one("SELECT COUNT(*) AS n FROM ek_email_outbox WHERE status IN ('pending','retry')");
        $r['dead']=(int)($dead['n']??0);$r['backlog']=(int)($backlog['n']??0);
        if(!$r['dead']&&$r['backlog']<100)return $r;
        // Independent server-side signal even if the email bridge is unavailable.
        if((int)date('i')===0)
            error_log('[eKeberadaan cron] Outbox health: dead='.$r['dead'].' backlog='.$r['backlog']);
        // Monitoring respects the same notification off switch as the mail worker.
        if(strtoupper((string)($s['EMAIL_NOTIFICATIONS_ENABLED']??'TRUE'))==='FALSE')return $r;
        $today=today();
        $body='Amaran queue emel eKeberadaan MySQL.'."\n".
            'Emel gagal kekal (dead): '.$r['dead']."\n".
            'Emel menunggu/retry: '.$r['backlog']."\n".
            'Semak phpMyAdmin jadual ek_email_outbox dan log cron cPanel.'."\n".
            'Status dead tidak dihantar semula secara automatik.';
        foreach(rows("SELECT emel FROM pengguna WHERE aktif=1 AND pentadbir=1") as $admin) {
            $email=strtolower(trim((string)($admin['emel']??'')));
            if(enqueue_workspace_email('mail-health:'.$today,$email,
                'eKeberadaan: Amaran queue emel '.$today,$body))$r['queued']++;
        }
    }catch(Throwable $e){
        error_log('[eKeberadaan cron] Outbox monitor unavailable ('.get_class($e).').');
    }
    return $r;
}
