<?php
declare(strict_types=1);
require_once __DIR__.'/workspace_bridge.php';

/** Workspace only handles Drive/Docs/Sheets I/O. Account identities always come from MySQL. */
function workspace_user_photo(array $viewer,string $target=''): array {
    $email=$target!==''?email_key($target):strtolower((string)$viewer['emel']);
    $canManage=(bool)($viewer['pentadbir']??false)||($viewer['kategori']??'')==='Pengurusan';
    if($email!==strtolower((string)$viewer['emel']) && !$canManage)
        throw new RuntimeException('Akses gambar profil tidak dibenarkan.');
    $user=user_by_email($email,false);
    if(!$user)throw new RuntimeException('Pengguna tidak dijumpai.');
    $fileId=trim((string)($user['fotoprofilfileid']??''));
    if($fileId==='') {
        // A user imported from Google Sheets may not have a photo file ID
        // in MySQL yet. Resolve it using only server-trusted user details.
        // The signed Workspace bridge does NOT read the old Sheets database.
        $settings=settings_raw();
        $rootId=trim((string)($settings['PROFILE_ROOT_FOLDER_ID']??''));
        if($rootId==='') {
            return ['ok'=>true,'dataUrl'=>'','message'=>
                'Folder induk Google Drive belum ditetapkan dalam Tetapan Pentadbir. Simpan folder ID dan cuba lagi.'];
        }
        $match=workspace_rpc('findPhoto',[
            'rootFolderId'=>$rootId,
            'name'=>(string)($user['nama']??''),
            'category'=>(string)($user['kategori']??'')
        ]);
        $fileId=trim((string)($match['fileId']??''));
        if($fileId==='') {
            return ['ok'=>true,'dataUrl'=>'','message'=>
                (string)($match['message']??'eoperasi.png belum dijumpai dalam folder nama pegawai.')];
        }
        if(!preg_match('/^[A-Za-z0-9_-]{12,120}$/',$fileId)) {
            throw new RuntimeException('Google Workspace memberikan ID gambar tidak sah.');
        }
        // Only persist the ID after Drive actually returns a valid picture.
        // A matching filename alone does not guarantee permission or format.
        $photo=workspace_rpc('photo',['fileId'=>$fileId]);
        if(!is_string($photo['dataUrl']??null) ||
           strpos($photo['dataUrl'],'data:image/')!==0) {
            throw new RuntimeException('Google Drive tidak memulangkan gambar yang sah.');
        }
        execute_sql(
            'UPDATE pengguna SET fotoprofilfileid=?,fotoprofildikemaskinipada=? WHERE LOWER(emel)=?',
            [$fileId,excel_number(now_myt()),$email]
        );
        return $photo;
    }
    return workspace_rpc('photo',['fileId'=>$fileId]);
}

function workspace_sync_photos(array $admin): array {
    must_admin($admin);
    $s=settings_raw();
    $folderId=trim((string)($s['PROFILE_ROOT_FOLDER_ID']??''));
    if(!$folderId)throw new RuntimeException('PROFILE_ROOT_FOLDER_ID tiada dalam jadual tetapan MySQL.');
    $staff=rows('SELECT nama,emel,kategori FROM pengguna WHERE emel IS NOT NULL AND nama IS NOT NULL AND aktif=1 ORDER BY nama');
    $users=[];
    foreach($staff as $r)$users[]=['email'=>$r['emel'],'name'=>$r['nama'],'category'=>$r['kategori']];
    $result=workspace_rpc('syncPhotos',['rootFolderId'=>$folderId,'users'=>$users]);
    $matched=0;
    foreach($result['updates']??[] as $row){
        $email=strtolower(trim((string)($row['email']??'')));
        $id=trim((string)($row['fileId']??''));
        if(!filter_var($email,FILTER_VALIDATE_EMAIL)||!preg_match('/^[A-Za-z0-9_-]{12,120}$/',$id))continue;
        $matched+=execute_sql('UPDATE pengguna SET fotoprofilfileid=?,fotoprofildikemaskinipada=? WHERE LOWER(emel)=?',
            [$id,excel_number(now_myt()),$email]);
    }
    audit_event($admin['emel'],'SYNC_GAMBAR_DRIVE_KE_MYSQL','PENGGUNA','Dipadankan: '.$matched);
    return ['ok'=>true,'matched'=>$matched,'unmatched'=>$result['unmatched']??[],
        'rootFolderId'=>$folderId];
}

/**
 * Export reports whose data is assembled exclusively from MySQL.
 * Google Workspace creates the final PDF or Google Spreadsheet only.
 */
function workspace_report(array $user,string $method,$arg) {
    $admin=(bool)($user['pentadbir']??false);
    $public=$method==='generatePublicAbsencePresencePdf';
    if(!$public && !$admin)throw new RuntimeException('Akses pentadbir diperlukan untuk eksport ini.');
    $type=($method==='generateAttendancePresenceReportSheet'||$method==='generateReportSheet')?'exportSheet':'exportPdf';
    $filter=is_array($arg)?$arg:[];
    $title='Laporan eKeberadaan';
    $subtitle='';
    $headers=[];$data=[];$sections=[];

    if($method==='generatePublicAbsencePresencePdf' || $method==='generateAbsencePresencePdf'){
        $from=valid_day((string)($filter['fromDate']??today()));
        $to=valid_day((string)($filter['toDate']??$from));
        if($from>$to || (strtotime($to)-strtotime($from))>31*86400)
            throw new InvalidArgumentException('Eksport PDF: pilih julat maksimum 31 hari.');
        $info=$public?public_absences($from,$to):management_absences($user,$from,$to);
        $list=$public?($info['rows']??[]):($info['requests']??[]);
        $title='Laporan Tidak Hadir dan Keberadaan';
        $headers=['Nama','Kategori','Mod','Jenis','Tarikh mula','Tarikh akhir','Masa mula','Masa akhir','Status'];
        foreach($list as $x){
            if(($filter['mode']??'')!=='' && ($filter['mode']??'')!==($x['mode']??''))continue;
            if(($filter['category']??'')!=='' && ($filter['category']??'')!==($x['category']??''))continue;
            if(($filter['status']??'')!=='' && ($filter['status']??'')!==($x['status']??''))continue;
            $data[]=[$x['name']??'',$x['category']??'',$x['mode']??'',$x['type']??'',
                $x['startDate']??'',$x['endDate']??'',$x['startTime']??'',$x['endTime']??'',$x['status']??''];
        }
        $subtitle=$from.' hingga '.$to;
    } elseif($method==='generateTimeReviewPdf'){
        $from=valid_day((string)($filter['fromDate']??today()));
        $to=valid_day((string)($filter['toDate']??$from));
        if($from>$to || (strtotime($to)-strtotime($from))>31*86400)throw new InvalidArgumentException('Julat melebihi 31 hari.');
        $info=time_reviews($from,$to);
        $title='Laporan Semakan Waktu';
        $headers=['Tarikh','Nama','Jenis','Sesi','Waktu rekod','Waktu rujukan','Status semakan'];
        foreach($info['rows']??[] as $x)$data[]=[$x['date']??'',$x['name']??'',$x['type']??'',
            $x['session']??'',$x['recordTime']??'',$x['referenceTime']??'',$x['reviewStatus']??''];
        $subtitle=$from.' hingga '.$to;
    } elseif($method==='generateAttendancePresenceReportPdf'||$method==='generateAttendancePresenceReportSheet') {
        $from=valid_day((string)($filter['fromDate']??today()));
        $to=valid_day((string)($filter['toDate']??$from));
        if($from>$to || (strtotime($to)-strtotime($from))>31*86400)
            throw new InvalidArgumentException('Julat laporan melebihi 31 hari.');
        require_once __DIR__.'/monthly_reports.php';
        $sections=mysql_monthly_report_sections($user,$from,$to);
        $title='Laporan Kehadiran Bulanan';
        $subtitle=$from.' hingga '.$to.' · Data MySQL · Ringkasan / Lewat / Perakam / Individu';
    } elseif($method==='generateReportSheet'){
        $date=valid_day(is_string($arg)?$arg:(string)($filter['date']??today()));
        $report=admin_data($user,$date);
        $title='Kehadiran Harian '.$date;
        $subtitle=$date;
        $headers=['Nama','Emel','Kategori','Jawatan','Status','Masuk','Keluar','Masuk 2','Keluar 2','Sumber'];
        foreach($report['report']??[] as $x)$data[]=[$x['name']??'',$x['email']??'',
            $x['category']??'',$x['jobTitle']??'',$x['status']??'',$x['inTime']??'',
            $x['outTime']??'',$x['inTime2']??'',$x['outTime2']??'',$x['source']??''];
    } else throw new RuntimeException('Jenis laporan Google Workspace tidak disokong.');
    if(!$sections && count($data)>250)
        throw new RuntimeException('Laporan melebihi 250 baris. Kecilkan penapis/julat tarikh.');
    $payload=['title'=>$title,'subtitle'=>$subtitle,'headers'=>$headers,'rows'=>$data];
    if($sections)$payload['sections']=$sections;
    // The Apps Script HMAC transport rejects payloads above 175 KB. Fail
    // explicitly instead of truncating staff data or silently dropping rows.
    $bytes=strlen(json_encode($payload,JSON_UNESCAPED_UNICODE|JSON_INVALID_UTF8_SUBSTITUTE));
    if($bytes>165000)
        throw new RuntimeException('Data laporan terlalu besar untuk satu eksport. Pilih julat tarikh lebih pendek.');
    $out=workspace_rpc($type,$payload);
    audit_event($user['emel'],'EKSPORT_GOOGLE_WORKSPACE',$method,$subtitle);
    return $out;
}
