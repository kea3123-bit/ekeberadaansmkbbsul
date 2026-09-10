#!/usr/bin/env python3
from pathlib import Path
p=Path('Scripts.html')
s=p.read_text(encoding='utf-8')
old="""  function updateAbsenceModeUi(){
    const mode=document.getElementById('absenceMode')?.value||'TIDAK_HADIR',d=state.absence||{};
    const typeSel=document.getElementById('absenceType');
    const types=mode==='KEBERADAAN'?(d.presenceTypes||[]):(d.types||[]);
    if(typeSel)typeSel.innerHTML='<option value=\"\">Pilih jenis</option>'+types.map(x=>`<option>${esc(x)}</option>`).join('');
    ['absenceStartTimeWrap','absenceEndTimeWrap'].forEach(id=>document.getElementById(id)?.classList.toggle('hidden',mode!=='KEBERADAAN'));
    const st=document.getElementById('absenceStartTime'),et=document.getElementById('absenceEndTime');if(st)st.required=mode==='KEBERADAAN';if(et)et.required=mode==='KEBERADAAN';
  }
"""
new="""  function updateAbsenceModeUi(){
    const mode=document.getElementById('absenceMode')?.value||'TIDAK_HADIR',d=state.absence||{};
    const typeSel=document.getElementById('absenceType');
    const requiredAbsenceTypes=[
      'CUTI REHAT KHAS','CUTI REHAT','CUTI SAKIT (AWAM)','CUTI SAKIT (SWASTA)',
      'CUTI TANPA REKOD KELOMPOK','KURSUS','BENGKEL','TAKLIMAT','MESYUARAT','SEMINAR',
      'AKTIVITI KOKURIKULUM','AKTIVITI SUKAN/PERMAINAN','LAIN-LAIN'
    ];
    const requiredPresenceTypes=[
      'PROGRAM DALAMAN SEKOLAH - KEBERADAAN',
      'URUSAN PERIBADI (MASUK LEWAT) - KEBERADAAN',
      'MESYUARAT DALAM SEKOLAH - KEBERADAAN',
      'BENGKEL/KURSUS/SEMINAR (PPD)',
      'BENGKEL/KURSUS/SEMINAR (JPN)',
      'BENGKEL/KURSUS/SEMINAR (KPM)',
      'MESYUARAT/TAKLIMAT (PPD)',
      'MESYUARAT/TAKLIMAT (JPN)',
      'MESYUARAT/TAKLIMAT (KPM)',
      'LAIN-LAIN - KEBERADAAN'
    ];
    const serverTypes=mode==='KEBERADAAN'?(d.presenceTypes||[]):(d.types||[]);
    const requiredTypes=mode==='KEBERADAAN'?requiredPresenceTypes:requiredAbsenceTypes;
    const seen=new Set(),types=[];
    [...serverTypes,...requiredTypes].forEach(value=>{const x=String(value||'').trim().toUpperCase();if(x&&!seen.has(x)){seen.add(x);types.push(x);}});
    if(typeSel)typeSel.innerHTML='<option value=\"\">Pilih jenis</option>'+types.map(x=>`<option>${esc(x)}</option>`).join('');
    ['absenceStartTimeWrap','absenceEndTimeWrap'].forEach(id=>document.getElementById(id)?.classList.toggle('hidden',mode!=='KEBERADAAN'));
    const st=document.getElementById('absenceStartTime'),et=document.getElementById('absenceEndTime');if(st)st.required=mode==='KEBERADAAN';if(et)et.required=mode==='KEBERADAAN';
  }
"""
if old not in s:
    raise SystemExit('updateAbsenceModeUi block not found')
s=s.replace(old,new,1)
p.write_text(s,encoding='utf-8')

idx=Path('Index.html')
h=idx.read_text(encoding='utf-8')
old_label='<label class="span-2 absence-note-field">Catatan / tujuan <small>(Sila isi tajuk aktiviti yang terlibat)</small><textarea id="absenceNote" name="note" rows="6" placeholder="Contoh: Kejohanan Merentas Desa Daerah / Bengkel PPD"></textarea></label>'
new_label='<label class="span-2 absence-note-field">Catatan / tujuan <small>(Sila isi tajuk aktiviti yang terlibat)</small><textarea id="absenceNote" name="note" rows="6" placeholder="Contoh: Kejohanan Merentas Desa Daerah / Bengkel PPD"></textarea></label>'
if old_label not in h:
    raise SystemExit('absence note label contract missing')
# Keep exact requested wording as an explicit validated contract.
h=h.replace(old_label,new_label,1)
idx.write_text(h,encoding='utf-8')
