<?php
declare(strict_types=1);
require dirname(__DIR__).'/email_templates.php';
function ck(bool $cond,string $msg):void {if(!$cond)throw new RuntimeException($msg);}
$html=ek_mail_punch_reminder_html([
    'nama'=>'AMIRAH BINTI MOHD YUSOF','emel'=>'amirah@example.test'
],'2026-11-01','07:38','07:40');
foreach(['#0b57d0','#121212','Peringatan Rekod Waktu Masuk','AMIRAH BINTI MOHD YUSOF',
  '1 November 2026','07:38','07:40','amirah@example.test',
  'Buka e-Keberadaan','Waktu rujukan masuk (Sesi 1)'] as $term)
    ck(str_contains($html,$term),'Missing reminder detail: '.$term);
ck(str_contains($html,'<!doctype html>'),'HTML document missing');
ck(strlen($html)<45000,'Reminder exceeds workspace HTML limit');
ck(!str_contains($html,'<script'),'HTML includes executable script');
$attack=ek_mail_punch_reminder_html(['nama'=>'<img src=x onerror=alert(1)>',
  'emel'=>'danger@example.test'],'2026-11-01','09:00','07:30');
ck(!str_contains($attack,'<img'),'User HTML injection was not escaped');
ck(str_contains($attack,'&lt;img'),'User HTML injection not encoded');
$normal=ek_mail_html_from_text('eKeberadaan: Keputusan permohonan',
 "Permohonan anda telah disemak.\nStatus: DILULUSKAN\nJenis: CUTI REHAT KHAS\n".
 "Rujukan: A-123\nhttps://kea3123-bit.github.io/ekeberadaansmkbbsul/");
foreach(['#0b57d0','Keputusan permohonan','DILULUSKAN','A-123','Buka e-Keberadaan'] as $term)
    ck(str_contains($normal,$term),'Missing generic mail detail: '.$term);
$pin=ek_mail_html_from_text('eKeberadaan: PIN', "PIN anda: <test>&\nSila semak.");
ck(str_contains($pin,'&lt;test&gt;&amp;'),'PIN body not escaped');
ck(!str_contains($pin,'<test>'),'Unescaped PIN body markup');
// Existing outbox table already has body_html; preserve stable event dedupe
// and allow old code paths to enqueue text without a fifth argument.
require dirname(__DIR__).'/email_queue.php';
$GLOBALS['queueCalls']=[];
function execute_sql(string $query,array $args=[]):int {
    $GLOBALS['queueCalls'][]=[$query,$args];
    return 1;
}
ck(enqueue_workspace_email('event-html','person@example.test','Reminder','Plain text',$html),'HTML enqueue failed');
$entry=$GLOBALS['queueCalls'][0];
ck(str_contains($entry[0],'body_html'),'Outbox SQL omitted body_html');
ck($entry[1][4]===$html,'Outbox did not store HTML content');
ck($entry[1][0]===hash('sha256','event-html|person@example.test'),'Dedupe event changed');
ck(enqueue_workspace_email('event-text','person@example.test','Report','Plain text'),'Text-only path should still work');
ck($GLOBALS['queueCalls'][1][1][4]===null,'Text-only legacy queue did not retain null HTML fallback');
ck(!enqueue_workspace_email('event-bad','person@example.test','Report','Text',str_repeat('x',45001)),
    'Oversized HTML must be rejected');
echo "BRANDED_EMAIL_HTML_TESTS_OK\n";
