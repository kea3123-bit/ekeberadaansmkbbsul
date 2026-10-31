<?php
declare(strict_types=1);
/** Admin-only MySQL maintenance. Does not read Google Sheets. */
function public_holidays_mysql(): array {
    return rows('SELECT tarikh AS date,nama AS name,jenis AS type,sumber AS source FROM cuti_umum WHERE (aktif=1 OR aktif IS NULL) ORDER BY tarikh DESC LIMIT 500');
}
function admin_add_public_holiday(array $admin,array $entry): array {
    $date=valid_day((string)($entry['date']??''));
    $name=trim((string)($entry['name']??''));
    if($name==='' || strlen($name)>160) throw new InvalidArgumentException('Nama cuti umum mesti 1 hingga 160 aksara.');
    $type=trim((string)($entry['type']??'MANUAL'));
    if(!in_array($type,['MANUAL','NEGERI','KEBANGSAAN'],true))$type='MANUAL';
    execute_sql('INSERT INTO cuti_umum(tarikh,nama,jenis,sumber,aktif) VALUES (?,?,?,?,1)
       ON DUPLICATE KEY UPDATE nama=VALUES(nama),jenis=VALUES(jenis),sumber=VALUES(sumber),aktif=1',
       [$date,$name,$type,'ADMIN']);
    audit_event($admin['emel'],'TAMBAH_CUTI_UMUM',$date,$name);
    return ['ok'=>true,'holidays'=>public_holidays_mysql()];
}
function admin_delete_public_holiday(array $admin,string $rawDate):array {
    $date=valid_day($rawDate);
    // Soft delete preserves the record and auditability.
    $updated=execute_sql('UPDATE cuti_umum SET aktif=0 WHERE tarikh=? AND (aktif=1 OR aktif IS NULL)',[$date]);
    if(!$updated)throw new RuntimeException('Cuti umum tidak dijumpai atau sudah dibuang.');
    audit_event($admin['emel'],'BUANG_CUTI_UMUM',$date);
    return ['ok'=>true,'holidays'=>public_holidays_mysql()];
}
/**
 * Conservative duplicate cleanup: delete only byte-for-byte identical
 * logical entries. Conflicting punches MUST NOT be discarded automatically.
 * Lock each date/email with the same lock name as the punch endpoint.
 */
function admin_repair_attendance_duplicates(array $admin):array {
    $groups=rows('SELECT LOWER(emel) AS email,tarikh,COUNT(*) AS n FROM kehadiran
       WHERE emel IS NOT NULL AND tarikh IS NOT NULL GROUP BY LOWER(emel),tarikh
       HAVING COUNT(*)>1 ORDER BY tarikh DESC LIMIT 100');
    $merged=0;$deleted=0;$conflicted=0;$busy=0;
    foreach($groups as $group) {
        $email=(string)$group['email'];$date=(string)$group['tarikh'];
        $lock='ek_punch_'.hash('sha256',$email.'|'.$date);
        $got=one('SELECT GET_LOCK(?,2) AS locked',[$lock]);
        if((int)($got['locked']??0)!==1){$busy++;continue;}
        try {
            db()->beginTransaction();
            $items=rows('SELECT * FROM kehadiran WHERE LOWER(emel)=? AND tarikh=? ORDER BY _row_id DESC FOR UPDATE',[$email,$date]);
            if(count($items)<2){db()->commit();continue;}
            $first=$items[0];
            $safe=true;
            foreach(array_slice($items,1) as $candidate){
                foreach($first as $column=>$value){
                    if(in_array($column,['_row_id','_source_row','dikemaskinipada'],true))continue;
                    if((string)($candidate[$column]??'')!==(string)($value??'')){$safe=false;break;}
                }
                if(!$safe)break;
            }
            if(!$safe){$conflicted++;db()->commit();continue;}
            $ids=array_map(static fn($x)=>(int)$x['_row_id'],array_slice($items,1));
            $params=implode(',',array_fill(0,count($ids),'?'));
            $deleted+=execute_sql('DELETE FROM kehadiran WHERE _row_id IN ('.$params.')',$ids);
            $merged++;
            db()->commit();
        }catch(Throwable $e){if(db()->inTransaction())db()->rollBack();throw $e;}
        finally{one('SELECT RELEASE_LOCK(?) AS released',[$lock]);}
    }
    audit_event($admin['emel'],'REPAIR_DUPLICATE_ATTENDANCE','KEHADIRAN',
        'merged='.$merged.' deleted='.$deleted.' conflict='.$conflicted.' busy='.$busy);
    return ['ok'=>true,'groupsMerged'=>$merged,'rowsRemoved'=>$deleted,
      'conflictedGroups'=>$conflicted,'busyGroups'=>$busy,
      'message'=>'Rekod serupa digabung. Rekod dengan masa/nilai berbeza sengaja tidak dipadam.'];
}
