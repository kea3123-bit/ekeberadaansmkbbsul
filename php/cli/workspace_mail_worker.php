<?php
declare(strict_types=1);
/**
 * cPanel Cron only. Example (every minute):
 * /usr/local/bin/php /home/ACCOUNT/public_html/ekeberadaansmkbbsul/php/cli/workspace_mail_worker.php
 * This process is not required for any user request or database operation.
 */
if(PHP_SAPI!=='cli'){http_response_code(404);exit;}
require_once dirname(__DIR__).'/_lib.php';
require_once dirname(__DIR__).'/workspace_bridge.php';
$sent=0;$failed=0;$limit=10;
// Recover crashed workers after 10 minutes. Delivery is at-least-once;
// the Workspace adapter caches successful delivery keys for six hours.
execute_sql("UPDATE ek_email_outbox SET status='retry',next_attempt_at=UTC_TIMESTAMP(),
  claimed_at=NULL WHERE status='sending' AND claimed_at < DATE_SUB(UTC_TIMESTAMP(),INTERVAL 10 MINUTE)");
for($i=0;$i<$limit;$i++){
    $item=one("SELECT id,dedupe_key,recipient,subject,body_text,attempts FROM ek_email_outbox
        WHERE status IN ('pending','retry') AND next_attempt_at<=UTC_TIMESTAMP()
        ORDER BY id LIMIT 1");
    if(!$item)break;
    $id=(int)$item['id'];
    $claimed=execute_sql("UPDATE ek_email_outbox SET status='sending',claimed_at=UTC_TIMESTAMP(),attempts=attempts+1
        WHERE id=? AND status IN ('pending','retry') AND next_attempt_at<=UTC_TIMESTAMP()",[$id]);
    if($claimed!==1)continue; // Another worker has claimed this row.
    try {
        $result=workspace_rpc('sendEmail',[
          'to'=>(string)$item['recipient'],'subject'=>(string)$item['subject'],
          'body'=>(string)$item['body_text'],'deliveryKey'=>(string)$item['dedupe_key']
        ]);
        if(empty($result['sent']))throw new RuntimeException('Mail adapter returned no confirmation.');
        execute_sql("UPDATE ek_email_outbox SET status='sent',sent_at=UTC_TIMESTAMP(),
          claimed_at=NULL,last_error=NULL WHERE id=? AND status='sending'",[$id]);
        $sent++;
    }catch(Throwable $e){
        $attempts=(int)$item['attempts']+1;
        $state=$attempts>=6?'dead':'retry';
        $delay=min(3600,60*(2**min(5,$attempts)));
        execute_sql("UPDATE ek_email_outbox SET status=?,claimed_at=NULL,
          next_attempt_at=DATE_ADD(UTC_TIMESTAMP(),INTERVAL $delay SECOND),
          last_error=? WHERE id=? AND status='sending'",
          [$state,'Workspace mail delivery failed ('.get_class($e).')',$id]);
        $failed++;
    }
}
echo "eKeberadaan MySQL outbox: sent=$sent failed=$failed\n";
