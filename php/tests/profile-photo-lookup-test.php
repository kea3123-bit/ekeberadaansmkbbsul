<?php
declare(strict_types=1);

/** Database-free regression: users without migrated Drive IDs still get photos. */
$source=(string)file_get_contents(dirname(__DIR__).'/workspace_services.php');
$start=strpos($source,'function workspace_user_photo(');
$end=$start===false?false:strpos($source,"\nfunction workspace_sync_photos(",$start);
if($start===false||$end===false)throw new RuntimeException('Photo handler unavailable');
eval(substr($source,$start,$end-$start));

$staff=['emel'=>'staff@example.test','nama'=>'Pegawai Ujian','kategori'=>'AKP','fotoprofilfileid'=>''];
$root='abcdefghijklmno1234567890';
$lookup=['fileId'=>'fileId123456789012345'];
$calls=[];$updates=[];
function email_key($email):string{return strtolower(trim((string)$email));}
function user_by_email($email,bool $active=true):?array{global $staff;return $email===$staff['emel']?$staff:null;}
function settings_raw():array{global $root;return ['PROFILE_ROOT_FOLDER_ID'=>$root];}
function workspace_rpc(string $action,array $data=[]):array{
    global $lookup,$calls;
    $calls[]=['action'=>$action,'data'=>$data];
    if($action==='findPhoto')return $lookup;
    if($action==='photo')return ['ok'=>true,'dataUrl'=>'data:image/png;base64,ZmFrZQ=='];
    throw new RuntimeException('Unexpected RPC action: '.$action);
}
function execute_sql(string $sql,array $params=[]):int{
    global $updates;
    if(strpos($sql,'UPDATE pengguna SET fotoprofilfileid')===false)throw new RuntimeException('Unexpected SQL');
    $updates[]=$params;return 1;
}
function excel_number($value):float{return 46324.5;}
function now_myt():string{return '2026-10-29 10:00:00';}

$viewer=['emel'=>'staff@example.test','pentadbir'=>false,'kategori'=>'AKP'];
$r=workspace_user_photo($viewer);
if(!str_starts_with($r['dataUrl']??'','data:image/png;base64,'))throw new RuntimeException('Photo lookup did not return image data');
if(array_column($calls,'action')!==['findPhoto','photo'])throw new RuntimeException('Expected findPhoto then photo');
if(($calls[0]['data']['name']??'')!=='Pegawai Ujian')throw new RuntimeException('Lookup used wrong staff name');
if(($calls[0]['data']['rootFolderId']??'')!==$root)throw new RuntimeException('Lookup used wrong Drive folder');
if(count($updates)!==1||($updates[0][0]??'')!==$lookup['fileId'])throw new RuntimeException('Drive ID not saved in MySQL');

$staff['fotoprofilfileid']='existingStoredFileId123';
$calls=[];$updates=[];
workspace_user_photo($viewer);
if(array_column($calls,'action')!==['photo']||count($updates)!==0)throw new RuntimeException('Existing photo ID should bypass lookup');

$staff['fotoprofilfileid']='';$lookup=['fileId'=>'','message'=>'No matching eoperasi.png'];
$calls=[];$updates=[];
$r=workspace_user_photo($viewer);
if(($r['message']??'')!=='No matching eoperasi.png'||count($updates)!==0)throw new RuntimeException('Missing photo should return useful diagnostic');

$root='';$calls=[];
$r=workspace_user_photo($viewer);
if(!str_contains($r['message']??'','Folder induk Google Drive')||count($calls)!==0)throw new RuntimeException('Missing root should be diagnosed before RPC');

try{
    workspace_user_photo(['emel'=>'other@example.test','pentadbir'=>false,'kategori'=>'AKP']);
    throw new RuntimeException('Unauthorized access unexpectedly allowed');
}catch(RuntimeException $e){
    if($e->getMessage()==='Unauthorized access unexpectedly allowed')throw $e;
}

echo "PASS: photo auto-lookup, MySQL persistence, cached photo ID, diagnostics and viewer authorization\n";
