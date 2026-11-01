<?php
declare(strict_types=1);
/** MySQL-only scheduled mail generation; invoked by the existing cPanel CLI worker. */
require_once __DIR__.'/email_templates.php';
function mysql_school_day(string $date,array $s,?array $holidays=null):bool {
    $date=valid_day($date);
    if($date<date_key($s['SYSTEM_START_DATE']??'2026-01-01'))return false;
    $days=array_filter(array_map('trim',explode(',',strtoupper((string)($s['WORKING_DAYS']??'SUN,MON,TUE,WED,THU')))));
    if(!in_array(strtoupper(date('D',strtotime($date))),$days,true))return false;
    if($holidays===null)$holidays=public_holidays_safe($date,$date);
    foreach($holidays as $h)if(date_key($h['tarikh']??'')===$date)return false;
    return true;
}
function mysql_active_requests_on(string $date):array {
    $items=[];
    foreach(rows("SELECT * FROM tidak_hadir WHERE status IN ('MENUNGGU','DILULUSKAN')") as $r){
        if(date_key($r['tarikhmula']??'')>$date||date_key($r['tarikhakhir']??'')<$date)continue;
        $items[strtolower(trim((string)$r['emel']))][]=$r;
    }
    return $items;
}
function mysql_request_exempts_punch(array $r,string $clock):bool {
    $mode=strtoupper(trim((string)($r['mod']??'TIDAK_HADIR')));
    $status=strtoupper(trim((string)($r['status']??'')));
    if(!in_array($status,['MENUNGGU','DILULUSKAN'],true))return false;
    if($mode!=='KEBERADAAN')return true; // Avoid false reminders during pending leave.
    $start=time_text($r['masamula']??'');
    $end=time_text($r['masaakhir']??'');
    return !$start||!$end||($clock>=$start&&$clock<=$end);
}
function schedule_mysql_mail_events():void {
    try{
        $s=settings_raw();
        if(strtoupper((string)($s['SYSTEM_MODE']??'REAL'))==='TEST')return;
        if(strtoupper((string)($s['EMAIL_NOTIFICATIONS_ENABLED']??'TRUE'))==='FALSE')return;
        $now=new DateTimeImmutable('now',new DateTimeZone('Asia/Kuala_Lumpur'));
        $today=$now->format('Y-m-d');$clock=$now->format('H:i');
        // Idempotent event keys tolerate missed 07:00-07:15 cron runs.
        if($clock>='07:00'){
            $previous=$now->modify('-1 day')->format('Y-m-d');
            if(mysql_school_day($previous,$s))queue_previous_day_report_mysql($previous);
        }
        if(strtoupper((string)($s['PUNCH_REMINDER_ENABLED']??'FALSE'))==='FALSE')return;
        if(!mysql_school_day($today,$s))return;
        $reminder=time_text($s['PUNCH_REMINDER_TIME']??'09:00');
        if(!preg_match('/^([01]\d|2[0-3]):[0-5]\d$/',$reminder))return;
        // Late cron is tolerated, but never sends a stale evening reminder.
        $start=DateTimeImmutable::createFromFormat('!Y-m-d H:i',$today.' '.$reminder,new DateTimeZone('Asia/Kuala_Lumpur'));
        if(!$start||$now<$start||$now>=$start->modify('+2 hours'))return;
        queue_punch_reminders_mysql($today,$reminder);
    }catch(Throwable $e){
        error_log('[eKeberadaan mail] MySQL scheduler failed ('.get_class($e).').');
    }
}
function queue_previous_day_report_mysql(string $date):void {
    $s=settings_raw();
    if(!mysql_school_day($date,$s))return;
    $totals=one("SELECT COUNT(DISTINCT emel) AS total,
      COUNT(DISTINCT CASE WHEN masuk IS NOT NULL AND CAST(masuk AS CHAR)<>'' THEN emel END) AS masuk,
      COUNT(DISTINCT CASE WHEN balik IS NOT NULL AND CAST(balik AS CHAR)<>'' THEN emel END) AS balik
      FROM kehadiran WHERE tarikh=?",[$date]);
    $users=one('SELECT COUNT(*) AS total FROM pengguna WHERE aktif=1');
    $recipients=rows("SELECT emel FROM pengguna WHERE aktif=1 AND (pentadbir=1 OR kategori='Pengurusan')");
    $body="Ringkasan kehadiran ".$date." (MySQL)\nStaf aktif: ".(int)($users['total']??0).
      "\nMasuk: ".(int)($totals['masuk']??0)."\nBalik: ".(int)($totals['balik']??0).
      "\nLaporan penuh: https://kea3123-bit.github.io/ekeberadaansmkbbsul/";
    foreach($recipients as $r)enqueue_workspace_email('daily-attendance:'.$date,(string)($r['emel']??''),
        'eKeberadaan: Ringkasan kehadiran '.$date,$body);
}
function queue_punch_reminders_mysql(string $date,string $clock='09:00'):void {
    $s=settings_raw();
    if(!mysql_school_day($date,$s))return;
    $clock=time_text($clock)?:'09:00';
    $recorded=[];
    foreach(rows('SELECT emel,masuk,masuk2,status FROM kehadiran WHERE tarikh=?',[$date]) as $r) {
        if(!empty($r['masuk'])||!empty($r['masuk2'])||
          strtoupper((string)($r['status']??''))==='TIDAK HADIR')
            $recorded[strtolower(trim((string)$r['emel']))]=true;
    }
    $requests=mysql_active_requests_on($date);
    foreach(rows('SELECT * FROM pengguna WHERE aktif=1') as $u) {
        $email=strtolower(trim((string)($u['emel']??'')));
        if(isset($recorded[$email]))continue;
        $exempt=false;
        foreach($requests[$email]??[] as $req)if(mysql_request_exempts_punch($req,$clock)){$exempt=true;break;}
        if($exempt)continue;
        // Rows normally carry these MySQL columns; defaults also keep test
        // fixtures and older user rows compatible without undefined-key notices.
        $schedule=schedule($u+['sesi1masuk'=>'','waktulewat'=>'','sesi1keluar'=>'',
            'waktubalik'=>'','sesi2masuk'=>'','sesi2keluar'=>'','maksmasuk'=>''],$s);
        $reference=time_text($schedule['s1In']??($s['DEFAULT_S1_IN']??'07:30'))?:'07:30';
        $plain="Assalamualaikum / Salam sejahtera ".trim((string)($u['nama']??'')).",\n".
            "Sistem masih belum mengesan rekod waktu masuk anda untuk ".ek_mail_date_malay($date).".\n".
            "Akaun: ".$email."\n".
            "Waktu peringatan: ".$clock."\n".
            "Waktu rujukan masuk (Sesi 1): ".$reference."\n".
            "Jika sedang bertugas, sila rekod waktu masuk. Jika tidak hadir, gunakan menu Tidak Hadir.\n".
            "https://kea3123-bit.github.io/ekeberadaansmkbbsul/";
        enqueue_workspace_email('punch-reminder:'.$date,$email,
            'eKeberadaan: Peringatan rekod waktu masuk',
            $plain,ek_mail_punch_reminder_html($u,$date,$clock,$reference));
    }
}
