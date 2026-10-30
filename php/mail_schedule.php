<?php
declare(strict_types=1);
/**
 * MySQL-backed scheduled email events.
 * Called only by the independent cPanel CLI mail worker; never by browser API.
 * Replaces the old Google Sheets-based 09:00 reminder and 07:00 daily report.
 */
function schedule_mysql_mail_events(): void {
    try {
        $settings=settings_raw();
        if(strtoupper((string)($settings['SYSTEM_MODE']??'REAL'))==='TEST')return;
        if(strtoupper((string)($settings['EMAIL_NOTIFICATIONS_ENABLED']??'TRUE'))==='FALSE')return;
        $now=new DateTimeImmutable('now',new DateTimeZone('Asia/Kuala_Lumpur'));
        $date=$now->format('Y-m-d');
        $hhmm=$now->format('H:i');
        if($hhmm>='07:00' && $hhmm<'07:15') {
            queue_previous_day_report_mysql($now->modify('-1 day')->format('Y-m-d'));
        }
        if(strtoupper((string)($settings['PUNCH_REMINDER_ENABLED']??'FALSE'))==='FALSE')return;
        $workDays=array_filter(array_map('trim',explode(',',strtoupper((string)($settings['WORKING_DAYS']??'SUN,MON,TUE,WED,THU')))));
        if(!in_array(strtoupper($now->format('D')),$workDays,true))return;
        $clock=(string)($settings['PUNCH_REMINDER_TIME']??'09:00');
        if(!preg_match('/^([01]\\d|2[0-3]):[0-5]\\d$/',$clock))return;
        $scheduled=DateTimeImmutable::createFromFormat('!Y-m-d H:i',$date.' '.$clock,new DateTimeZone('Asia/Kuala_Lumpur'));
        if(!$scheduled || $now<$scheduled || $now>=$scheduled->modify('+15 minutes'))return;
        queue_punch_reminders_mysql($date);
    }catch(Throwable $e){
        error_log('[eKeberadaan mail] Scheduled event generation unavailable ('.get_class($e).').');
    }
}
function queue_previous_day_report_mysql(string $date): void {
    $totals=one('SELECT COUNT(DISTINCT emel) AS total, COUNT(DISTINCT CASE WHEN masuk IS NOT NULL AND masuk<>\'\' THEN emel END) AS masuk,
      COUNT(DISTINCT CASE WHEN balik IS NOT NULL AND balik<>\'\' THEN emel END) AS balik
      FROM kehadiran WHERE tarikh=?',[$date]);
    $users=one('SELECT COUNT(*) AS total FROM pengguna WHERE aktif=1');
    $recipients=rows("SELECT emel FROM pengguna WHERE aktif=1 AND (pentadbir=1 OR kategori='Pengurusan')");
    $subject='eKeberadaan: Ringkasan kehadiran '.$date;
    $text="Ringkasan kehadiran ".$date." (data MySQL sahaja)\n".
      "Staf aktif: ".(int)($users['total']??0)."\n".
      "Masuk: ".(int)($totals['masuk']??0)."\n".
      "Balik: ".(int)($totals['balik']??0)."\n".
      "Laporan penuh: https://kea3123-bit.github.io/ekeberadaansmkbbsul/";
    foreach($recipients as $entry) {
        enqueue_workspace_email('daily-attendance:'.$date,(string)($entry['emel']??''),$subject,$text);
    }
}
function queue_punch_reminders_mysql(string $date): void {
    $already=[];
    foreach(rows('SELECT emel,masuk,status FROM kehadiran WHERE tarikh=?',[$date]) as $r){
        if(!empty($r['masuk']) || strtoupper((string)($r['status']??''))==='TIDAK HADIR')
            $already[strtolower(trim((string)$r['emel']))]=true;
    }
    // Absence ranges from the imported database may be Excel serial dates
    // or ISO dates. Skip both kinds to avoid false reminder emails.
    $excused=[];
    $serial=excel_number($date);
    foreach(rows("SELECT emel,tarikhmula,tarikhakhir FROM tidak_hadir
        WHERE status NOT IN ('DIBATALKAN','DITOLAK')") as $r) {
        $from=$r['tarikhmula'];$to=$r['tarikhakhir'];
        $a=is_numeric($from)?(float)$from:excel_number((string)$from);
        $b=is_numeric($to)?(float)$to:excel_number((string)$to);
        if($a<=$serial && $b>=$serial)$excused[strtolower(trim((string)$r['emel']))]=true;
    }
    $staff=rows('SELECT u.emel,u.nama FROM pengguna u
        WHERE u.aktif=1');
    foreach($staff as $user) {
        $email=strtolower(trim((string)($user['emel']??'')));
        if(isset($already[$email])||isset($excused[$email]))continue;
        $name=trim((string)($user['nama']??''));
        enqueue_workspace_email('punch-reminder:'.$date,$email,
            'eKeberadaan: Peringatan rekod waktu masuk',
            "Salam ".$name.",\n\nRekod waktu masuk anda pada ".$date.
            " belum dipaparkan dalam MySQL. Jika anda hadir, sila buka eKeberadaan dan semak rekod anda.\n".
            "https://kea3123-bit.github.io/ekeberadaansmkbbsul/");
    }
}
