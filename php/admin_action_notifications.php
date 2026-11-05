<?php
declare(strict_types=1);

/**
 * Read-only overview of outstanding administration actions.
 * Called only after require_user($token, true) in the API dispatcher.
 * Uses existing MySQL records; no new table, cron or external notifications.
 */
function ek_admin_pending_actions(array $admin):array {
    must_admin($admin);

    $absenceRows=rows("SELECT id,emel,nama,jenis,`mod`,tarikhmula,tarikhakhir,dihantarpada
        FROM tidak_hadir
        WHERE status='MENUNGGU' AND id IS NOT NULL AND id<>''
        ORDER BY dihantarpada DESC,_row_id DESC");
    $timeRows=rows("SELECT id,emel,nama,jenis,sesi,tarikh,wakturekod,wakturujukan
        FROM semakan_waktu
        WHERE (statussemakan='BELUM DIAMBIL MAKLUM' OR statussemakan IS NULL OR statussemakan='')
          AND id IS NOT NULL AND id<>''
        ORDER BY tarikh DESC,_row_id DESC");

    $requests=[];
    foreach($absenceRows as $r) {
        $requests[]=[
            'kind'=>'ABSENCE',
            'id'=>(string)$r['id'],
            'name'=>(string)($r['nama']??''),
            'email'=>(string)($r['emel']??''),
            'mode'=>(string)($r['mod']??'TIDAK_HADIR'),
            'type'=>(string)($r['jenis']??''),
            'startDate'=>date_key($r['tarikhmula']??''),
            'endDate'=>date_key($r['tarikhakhir']??''),
            'submittedAt'=>isset($r['dihantarpada'])&&is_numeric($r['dihantarpada'])
                ?gmdate('Y-m-d H:i',(int)round(((float)$r['dihantarpada']-25569)*86400)):'',
        ];
    }
    $timeReviews=[];
    foreach($timeRows as $r) {
        $timeReviews[]=[
            'kind'=>'TIME_REVIEW',
            'id'=>(string)$r['id'],
            'name'=>(string)($r['nama']??''),
            'email'=>(string)($r['emel']??''),
            'date'=>date_key($r['tarikh']??''),
            'type'=>(string)($r['jenis']??''),
            'session'=>(int)($r['sesi']??1),
            'recordTime'=>time_text($r['wakturekod']??''),
            'referenceTime'=>time_text($r['wakturujukan']??''),
        ];
    }
    return [
        'absenceCount'=>count($requests),
        'timeReviewCount'=>count($timeReviews),
        'total'=>count($requests)+count($timeReviews),
        'requests'=>$requests,
        'timeReviews'=>$timeReviews,
    ];
}
