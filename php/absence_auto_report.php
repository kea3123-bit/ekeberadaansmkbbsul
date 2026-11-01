<?php
declare(strict_types=1);

/**
 * Read-only projection of persisted automatic no-show attendance rows.
 *
 * The tidak_hadir table contains requests; automatic no-shows are recorded in
 * kehadiran. Include them in public absence list / PDF without changing the
 * attendance or leave tables and without inferring a future no-show.
 */
function mysql_auto_unexplained_absence_rows(string $from,string $to,array $activeRequests):array {
    $employees=[];
    foreach(rows('SELECT emel,nama,kategori,jawatan,aktif FROM pengguna WHERE emel IS NOT NULL AND nama IS NOT NULL') as $u) {
        $email=strtolower(trim((string)($u['emel']??'')));
        if($email!==''&&(int)($u['aktif']??0)===1)$employees[$email]=$u;
    }

    // Already visible requests cannot also be labeled as "TIDAK MOHON".
    $covered=[];
    foreach($activeRequests as $r){
        if(!in_array((string)($r['status']??''),['MENUNGGU','DILULUSKAN'],true))continue;
        $email=strtolower(trim((string)($r['email']??'')));
        if($email==='')continue;
        $covered[$email][]=[$r['startDate']??'',$r['endDate']??''];
    }

    // Only persisted auto-trigger records. Never derive auto absence solely
    // from a missing punch because the daily cutoff may not have passed.
    $physical=rows("SELECT tarikh,emel,nama,kategori,sumber,status,masuk,masuk2,_row_id
        FROM kehadiran
        WHERE tarikh BETWEEN ? AND ?
          AND sumber='AUTO_TIDAK_HADIR'
          AND status='TIDAK HADIR'
        ORDER BY _row_id",[$from,$to]);
    $byStaffDate=[];
    foreach($physical as $r){
        $date=date_key($r['tarikh']??'');
        $email=strtolower(trim((string)($r['emel']??'')));
        if(!$date||!isset($employees[$email])||$date<$from||$date>$to)continue;
        if(time_text($r['masuk']??'')!==''||time_text($r['masuk2']??'')!=='')continue;
        $alreadyExplained=false;
        foreach($covered[$email]??[] as [$start,$end]){
            if($start<=$date&&$end>=$date){$alreadyExplained=true;break;}
        }
        if($alreadyExplained)continue;
        $u=$employees[$email];
        $key=$date.'|'.$email;
        $byStaffDate[$key]=[
            'id'=>'AUTO-'.str_replace('-','',$date).'-'.substr(hash('sha256',$email),0,12),
            'email'=>$email,'name'=>(string)($u['nama']??$r['nama']??''),
            'category'=>(string)($u['kategori']??$r['kategori']??''),
            'jobTitle'=>(string)($u['jawatan']??''),
            'type'=>'TIADA PENJELASAN','mode'=>'TIDAK_HADIR',
            'startDate'=>$date,'endDate'=>$date,'startTime'=>'','endTime'=>'',
            'note'=>'Rekod automatik daripada MySQL','status'=>'TIDAK MOHON',
            'source'=>'AUTO_TIDAK_HADIR','reviewedBy'=>'','comment'=>'',
            'submittedAt'=>'','reviewedAt'=>'',
        ];
    }
    return array_values($byStaffDate);
}
