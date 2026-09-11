from pathlib import Path

index_path = Path('Index.html')
scripts_path = Path('Scripts.html')

index = index_path.read_text(encoding='utf-8')
scripts = scripts_path.read_text(encoding='utf-8')

replacements = {
    '<div class="preset-row"><button class="btn ghost small" onclick="setAbsencePublicPreset(\'today\')">Hari ini</button><button class="btn ghost small" onclick="setAbsencePublicPreset(\'week\')">Minggu ini</button><button class="btn ghost small" onclick="setAbsencePublicPreset(\'month\')">Bulan ini</button></div>':
    '<div class="preset-row"><button class="btn ghost small" onclick="setAbsencePublicPreset(\'yesterday\')">Semalam</button><button class="btn ghost small" onclick="setAbsencePublicPreset(\'today\')">Hari ini</button><button class="btn ghost small" onclick="setAbsencePublicPreset(\'tomorrow\')">Esok</button><button class="btn ghost small" onclick="setAbsencePublicPreset(\'week\')">Minggu ini</button><button class="btn ghost small" onclick="setAbsencePublicPreset(\'month\')">Bulan ini</button></div>',
    '<div class="preset-row"><button class="btn ghost small" onclick="setAbsenceManagePreset(\'today\')">Hari ini</button><button class="btn ghost small" onclick="setAbsenceManagePreset(\'week\')">Minggu ini</button><button class="btn ghost small" onclick="setAbsenceManagePreset(\'month\')">Bulan ini</button></div>':
    '<div class="preset-row"><button class="btn ghost small" onclick="setAbsenceManagePreset(\'yesterday\')">Semalam</button><button class="btn ghost small" onclick="setAbsenceManagePreset(\'today\')">Hari ini</button><button class="btn ghost small" onclick="setAbsenceManagePreset(\'tomorrow\')">Esok</button><button class="btn ghost small" onclick="setAbsenceManagePreset(\'week\')">Minggu ini</button><button class="btn ghost small" onclick="setAbsenceManagePreset(\'month\')">Bulan ini</button></div>',
    '<div class="preset-row"><button class="btn ghost small" onclick="setTimeReviewPreset(\'today\')">Hari ini</button><button class="btn ghost small" onclick="setTimeReviewPreset(\'week\')">Minggu ini</button><button class="btn ghost small" onclick="setTimeReviewPreset(\'month\')">Bulan ini</button></div>':
    '<div class="preset-row"><button class="btn ghost small" onclick="setTimeReviewPreset(\'yesterday\')">Semalam</button><button class="btn ghost small" onclick="setTimeReviewPreset(\'today\')">Hari ini</button><button class="btn ghost small" onclick="setTimeReviewPreset(\'tomorrow\')">Esok</button><button class="btn ghost small" onclick="setTimeReviewPreset(\'week\')">Minggu ini</button><button class="btn ghost small" onclick="setTimeReviewPreset(\'month\')">Bulan ini</button></div>',
}

for old, new in replacements.items():
    if old not in index:
        raise SystemExit('Expected preset row not found: ' + old[:80])
    index = index.replace(old, new, 1)

old_range = "function presetRange(kind){const today=state.boot?.today||localDateKey(new Date()),systemStart=getSystemStartDateClient(),d=new Date(today+'T12:00:00');if(kind==='today')return[today<systemStart?systemStart:today,today];if(kind==='month'){const start=`${today.slice(0,7)}-01`;return[start<systemStart?systemStart:start,today];}const start=addClientDays(today,-d.getDay());return[start<systemStart?systemStart:start,today];}"
new_range = "function presetRange(kind){const today=state.boot?.today||localDateKey(new Date()),systemStart=getSystemStartDateClient(),d=new Date(today+'T12:00:00'),single=key=>{const safe=key<systemStart?systemStart:key;return[safe,safe];};if(kind==='yesterday')return single(addClientDays(today,-1));if(kind==='tomorrow')return single(addClientDays(today,1));if(kind==='today')return single(today);if(kind==='month'){const start=`${today.slice(0,7)}-01`;return[start<systemStart?systemStart:start,today];}const start=addClientDays(today,-d.getDay());return[start<systemStart?systemStart:start,today];}"

if old_range not in scripts:
    raise SystemExit('presetRange function not found')
scripts = scripts.replace(old_range, new_range, 1)

index_path.write_text(index, encoding='utf-8')
scripts_path.write_text(scripts, encoding='utf-8')
