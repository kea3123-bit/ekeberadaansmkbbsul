<?php
declare(strict_types=1);
/** Staging-only database schema/concurrency integration. Never use in production. */
if(getenv('EK_AUDIT_STAGING')!=='1'||getenv('MYSQL_DATABASE')!=='eke_audit'||getenv('MYSQL_HOST')!=='127.0.0.1')
    throw new RuntimeException('Refusing to access any non-ephemeral audit database.');
$dsn='mysql:host=127.0.0.1;port=3306;dbname=eke_audit;charset=utf8mb4';
$db=new PDO($dsn,(string)getenv('MYSQL_USER'),(string)getenv('MYSQL_PASSWORD'),
    [PDO::ATTR_ERRMODE=>PDO::ERRMODE_EXCEPTION,PDO::ATTR_EMULATE_PREPARES=>false]);
if(($argv[1]??'')==='seed') {
    $sql=file_get_contents(dirname(__DIR__).'/schema_core.sql');
    foreach(preg_split('/;\s*(?:\r?\n|$)/',$sql) as $chunk) {
        $chunk=preg_replace('/^\s*--[^\n]*\n/m','',$chunk);
        if(trim($chunk)!=='')$db->exec($chunk);
    }
    foreach(['pengguna','kehadiran','tidak_hadir','semakan_waktu','tetapan','audit','cuti_umum',
       'web_auth','web_sessions','web_setup_state','ek_email_outbox','ek_pin_recovery'] as $name) {
        $exists=$db->query("SHOW TABLES LIKE '".$name."'")->fetchColumn();
        if(!$exists)throw new RuntimeException('Missing table '.$name);
    }
    $db->exec("INSERT INTO pengguna (_source_row,nama,emel,kategori,aktif) VALUES (0,'Staf Ujian','user@example.test','PPP',1)");
    echo "PASS staging schema: 12 core tables, no data dump, staff insert\n";
}elseif(($argv[1]??'')==='worker') {
    $id=(int)($argv[2]??0);
    $st=$db->prepare('INSERT INTO kehadiran (_source_row,tarikh,emel,nama,kategori,masuk) VALUES (0,?,?,?,?,?)');
    for($i=0;$i<10;$i++) {
        $email='worker'.$id.'-'.$i.'@example.test';
        $st->execute(['2026-10-31',$email,'Staf '.$id,'AKP','2026-10-31 07:30:00']);
    }
}elseif(($argv[1]??'')==='verify') {
    $r=$db->query('SELECT COUNT(*) AS n,COUNT(DISTINCT _row_id) AS uniqueIds,
      COUNT(DISTINCT _source_row) AS importedKeys FROM kehadiran')->fetch();
    if((int)$r['n']!==200||(int)$r['uniqueIds']!==200)
        throw new RuntimeException('Concurrent writes collided: '.json_encode($r));
    echo "PASS 200 parallel-staged attendance INSERTs: unique auto IDs, no MAX(_source_row)+1 race\n";
}else throw new RuntimeException('Pass seed, worker or verify');
