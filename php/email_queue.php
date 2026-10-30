<?php
declare(strict_types=1);
/**
 * MySQL outbox only: enqueue events without making a Google network request.
 * The separate PHP CLI worker delivers emails through the signed Apps Script
 * Workspace bridge. Never import the legacy Apps Script Sheets database.
 */
function enqueue_workspace_email(string $eventKey,string $recipient,string $subject,string $text): bool {
    $recipient=strtolower(trim($recipient));
    $subject=trim($subject);
    if(!filter_var($recipient,FILTER_VALIDATE_EMAIL) || strlen($recipient)>254) return false;
    if($subject==='' || strlen($subject)>180 || $text==='' || strlen($text)>12000) return false;
    if(strpbrk($subject,"\r\n")!==false) return false;
    try {
        // Both the data operation and the notification remain MySQL-only.
        // The actual MailApp call happens in an independent scheduled worker.
        execute_sql('INSERT IGNORE INTO ek_email_outbox (dedupe_key,recipient,subject,body_text) VALUES (?,?,?,?)',[
            hash('sha256',$eventKey.'|'.$recipient),$recipient,$subject,$text
        ]);
        return true;
    }catch(Throwable $e){
        // Notification/queue failure must not undo an attendance or absence write.
        error_log('[eKeberadaan mail] Outbox unavailable ('.get_class($e).'). Install mail migration.');
        return false;
    }
}
function notify_absence_submitted_mysql(array $user,string $id,string $type): void {
    try {
        $admins=rows("SELECT emel FROM pengguna WHERE aktif=1 AND (pentadbir=1 OR kategori='Pengurusan')");
        $message="Permohonan Tidak Hadir/Keberadaan baharu.\nNama: ".(string)$user['nama'].
          "\nJenis: ".mb_substr($type,0,100)."\nRujukan: ".$id.
          "\nSemak melalui eKeberadaan: https://kea3123-bit.github.io/ekeberadaansmkbbsul/";
        foreach($admins as $admin) {
            $email=strtolower(trim((string)($admin['emel']??'')));
            if($email!==strtolower((string)$user['emel']))
                enqueue_workspace_email("absence-submitted:".$id,$email,'eKeberadaan: Permohonan baharu',$message);
        }
    }catch(Throwable $e){
        error_log('[eKeberadaan mail] Could not queue absence submitted notification.');
    }
}
function notify_absence_reviewed_mysql(string $id,string $status): void {
    try {
        $r=one('SELECT emel,nama,jenis FROM tidak_hadir WHERE id=? LIMIT 1',[$id]);
        if(!$r)return;
        $text="Permohonan eKeberadaan anda telah disemak.\nStatus: ".$status.
            "\nJenis: ".(string)$r['jenis']."\nRujukan: ".$id.
            "\nLihat keputusan: https://kea3123-bit.github.io/ekeberadaansmkbbsul/";
        enqueue_workspace_email('absence-reviewed:'.$id.':'.$status,(string)$r['emel'],
            'eKeberadaan: Keputusan permohonan',$text);
    }catch(Throwable $e){
        error_log('[eKeberadaan mail] Could not queue absence reviewed notification.');
    }
}
function notify_absence_cancelled_mysql(string $id,array $user): void {
    try {
        $admins=rows("SELECT emel FROM pengguna WHERE aktif=1 AND (pentadbir=1 OR kategori='Pengurusan')");
        foreach($admins as $admin) {
            $email=strtolower(trim((string)($admin['emel']??'')));
            if($email!==strtolower((string)$user['emel']))
                enqueue_workspace_email('absence-cancelled:'.$id,$email,
                    'eKeberadaan: Permohonan dibatalkan',
                    'Permohonan oleh '.(string)$user['nama'].' telah dibatalkan. Rujukan: '.$id);
        }
    }catch(Throwable $e){
        error_log('[eKeberadaan mail] Could not queue cancellation notification.');
    }
}
