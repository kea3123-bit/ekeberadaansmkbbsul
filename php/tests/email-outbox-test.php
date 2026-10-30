<?php
declare(strict_types=1);
// No MySQL, Workspace, mail, Google credentials or network required.
require_once dirname(__DIR__).'/email_queue.php';
$items=[];$fail=false;
function execute_sql(string $query,array $params=[]): int {
  global $items,$fail;
  if($fail)throw new RuntimeException('DB unavailable');
  if(strpos($query,'INSERT IGNORE INTO ek_email_outbox')===false)throw new RuntimeException('Expected queued insert only');
  $items[$params[0]]=$params;
  return 1;
}
function rows(string $query,array $params=[]):array {
  return [['emel'=>'admin@example.test'],['emel'=>'staff@example.test']];
}
function one(string $query,array $params=[]):?array {
  return ['emel'=>'staff@example.test','nama'=>'Staff','jenis'=>'URUSAN'];
}
if(!enqueue_workspace_email('event-1','staff@example.test','Notis','Body'))throw new RuntimeException('Queue failed');
if(!enqueue_workspace_email('event-1','staff@example.test','Notis','Body'))throw new RuntimeException('Dedupe repeat rejected');
if(count($items)!==1)throw new RuntimeException('Deterministic dedupe failed');
if(enqueue_workspace_email('event-2','invalid','Notis','Body'))throw new RuntimeException('Invalid recipient accepted');
notify_absence_submitted_mysql(['emel'=>'staff@example.test','nama'=>'Staff'], 'TH-123','URUSAN');
if(count($items)!==2)throw new RuntimeException('Admin notification not queued');
notify_absence_reviewed_mysql('TH-123','DILULUSKAN');
if(count($items)!==3)throw new RuntimeException('Review notification not queued');
$fail=true;
if(enqueue_workspace_email('event-3','staff@example.test','Notis','Body'))throw new RuntimeException('DB failure falsely succeeded');
echo "PASS: MySQL outbox queues asynchronously, deduplicates and never calls Workspace on request path\n";
