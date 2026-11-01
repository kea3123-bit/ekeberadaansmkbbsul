<?php
declare(strict_types=1);

/**
 * Branded HTML email for the MySQL outbox. The source of truth remains MySQL;
 * this file only transforms already-approved notification content for email.
 * Inline styles and table layout are compatible with Gmail/mobile mail clients.
 */
function ek_mail_escape($value): string {
    return htmlspecialchars((string)($value??''),ENT_QUOTES|ENT_SUBSTITUTE,'UTF-8');
}
function ek_mail_date_malay(string $date): string {
    $months=[1=>'Januari','Februari','Mac','April','Mei','Jun','Julai','Ogos',
        'September','Oktober','November','Disember'];
    $stamp=strtotime($date.' 12:00:00');
    if($stamp===false)return $date;
    $m=(int)date('n',$stamp);
    return (int)date('j',$stamp).' '.$months[$m].' '.date('Y',$stamp);
}
function ek_mail_details(array $pairs): string {
    if(!$pairs)return '';
    $out='<table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="border-collapse:collapse;margin:18px 0 24px">';
    foreach($pairs as $pair) {
        $label=ek_mail_escape($pair[0]??'');
        $value=ek_mail_escape($pair[1]??'');
        $out.='<tr><td valign="top" width="42%" style="width:42%;padding:12px 8px;border-bottom:1px solid #404040;color:#aeb9cd;font-size:14px;line-height:1.45">'.$label.'</td>'.
              '<td valign="top" style="padding:12px 8px;border-bottom:1px solid #404040;color:#ffffff;font-weight:700;font-size:15px;line-height:1.45;overflow-wrap:anywhere">'.$value.'</td></tr>';
    }
    return $out.'</table>';
}
function ek_mail_action(string $label,string $href): string {
    if(!preg_match('~^https://[a-z0-9.-]+(?:/[^"<>]*)?$~i',$href))return '';
    return '<table role="presentation" cellspacing="0" cellpadding="0" border="0" style="margin:24px 0"><tr><td bgcolor="#0b57d0" style="border-radius:9px;background:#0b57d0">'.
       '<a href="'.ek_mail_escape($href).'" style="display:inline-block;color:#ffffff;text-decoration:none;font-size:14px;font-weight:700;padding:12px 18px;border-radius:9px">'.
       ek_mail_escape($label).'</a></td></tr></table>';
}
function ek_mail_frame(string $title,string $content): string {
    $title=ek_mail_escape($title);
    return '<!doctype html><html lang="ms"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>'.
    '<body style="margin:0;padding:0;background:#262626;color:#f5f6f8;font-family:Arial,Helvetica,sans-serif;-webkit-text-size-adjust:100%">'.
    '<table role="presentation" border="0" cellpadding="0" cellspacing="0" width="100%" style="background:#262626;border-collapse:collapse"><tr><td align="center" style="padding:22px 12px">'.
    '<table role="presentation" border="0" cellpadding="0" cellspacing="0" width="600" style="width:100%;max-width:600px;border-collapse:separate;border-spacing:0">'.
    '<tr><td bgcolor="#0b57d0" style="padding:26px 28px;background:#0b57d0;border-radius:18px 18px 0 0;color:#ffffff">'.
    '<div style="font-size:13px;line-height:1.4;letter-spacing:1.1px;font-weight:700">E-KEBERADAAN</div>'.
    '<div style="font-size:26px;line-height:1.25;font-weight:800;margin-top:10px;color:#ffffff">'.$title.'</div>'.
    '</td></tr>'.
    '<tr><td bgcolor="#121212" style="padding:30px 28px;background:#121212;color:#f5f6f8;border-radius:0 0 18px 18px;font-size:16px;line-height:1.55">'.
    $content.
    '<div style="border-top:1px solid #404040;margin-top:26px;padding-top:17px;color:#aeb9cd;font-size:12px;line-height:1.6">'.
    'SMK Bandar Baru Sungai Lalang · e-Keberadaan<br>'.
    'Emel automatik daripada sistem. Jangan balas emel ini.'.
    '</div></td></tr></table></td></tr></table></body></html>';
}
function ek_mail_punch_reminder_html(array $user,string $date,string $reminderTime,string $referenceTime): string {
    $name=ek_mail_escape(trim((string)($user['nama']??''))?:($user['emel']??'pengguna'));
    $dateLabel=ek_mail_escape(ek_mail_date_malay($date));
    $content='<p style="margin:0 0 22px;font-size:17px">Assalamualaikum / Salam sejahtera<br><strong style="color:#ffffff">'.$name.'</strong>,</p>'.
        '<p style="margin:0 0 22px">Sistem masih belum mengesan <strong style="color:#ffffff">rekod waktu masuk</strong> anda untuk hari ini, <strong style="color:#ffffff">'.$dateLabel.'</strong>.</p>'.
        ek_mail_details([
            ['Akaun',$user['emel']??''],
            ['Waktu peringatan',$reminderTime],
            ['Waktu rujukan masuk (Sesi 1)',$referenceTime],
        ]).
        '<p style="margin:0 0 8px">Jika anda sedang bertugas, sila buka <strong>e-Keberadaan</strong> dan rakam waktu masuk. Jika anda tidak hadir dan belum membuat permohonan, gunakan menu <strong>Tidak Hadir</strong>.</p>'.
        ek_mail_action('Buka e-Keberadaan','https://kea3123-bit.github.io/ekeberadaansmkbbsul/').
        '<p style="font-size:12px;color:#aeb9cd">Peringatan dihantar sekali setiap hari bekerja jika tiada rekod masuk. Semakan dibuat berdasarkan data MySQL.</p>';
    return ek_mail_frame('Peringatan Rekod Waktu Masuk',$content);
}
/**
 * Format all other existing MySQL notifications (leave, PIN, time reviews,
 * daily report, dead-mail warning) without changing senders or their content.
 * Preserve the text fallback for devices that block HTML.
 */
function ek_mail_html_from_text(string $subject,string $text):string {
    $title=trim((string)preg_replace('/^e-?keberadaan\s*:\s*/iu','',$subject));
    if($title==='')$title='Makluman e-Keberadaan';
    $bodyLines=preg_split('/\r\n|\n|\r/',$text)?:[];
    $intro=[];$details=[];$notes=[];$links=[];
    foreach($bodyLines as $line) {
        $line=trim((string)$line);
        if($line==='')continue;
        if(preg_match('~^https://[^\s<>]+$~i',$line)){$links[]=$line;continue;}
        if(preg_match('/^([^:]{2,70}):\s*(.+)$/u',$line,$m) && !str_contains($m[1],'/')) {
            $details[]=[$m[1],$m[2]];
            continue;
        }
        if(count($intro)<2)$intro[]=$line;
        else $notes[]=$line;
    }
    $content='';
    foreach($intro as $line)
        $content.='<p style="margin:0 0 18px;color:#ffffff;font-size:16px">'.ek_mail_escape($line).'</p>';
    $content.=ek_mail_details($details);
    foreach($notes as $line)
        $content.='<p style="margin:0 0 12px;color:#f5f6f8">'.ek_mail_escape($line).'</p>';
    foreach(array_unique($links) as $url)$content.=ek_mail_action('Buka e-Keberadaan',$url);
    if($content==='')$content='<p>'.ek_mail_escape($text).'</p>';
    return ek_mail_frame($title,$content);
}
