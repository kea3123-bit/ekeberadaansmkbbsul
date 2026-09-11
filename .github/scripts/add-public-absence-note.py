from pathlib import Path

# apps-script public DTO + server-side search
p = Path('apps-script/61_Absence.gs')
s = p.read_text()
s = s.replace("    type:String(r.type||'TIDAK HADIR'),\n    startDate,", "    type:String(r.type||'TIDAK HADIR'),\n    note:String(r.note||''),\n    startDate,", 1)
s = s.replace("const hay = [r.name,r.jobTitle,r.category,r.mode,r.type,r.startDate,r.endDate,r.startTime,r.endTime,r.status].join(' ').toLowerCase();", "const hay = [r.name,r.jobTitle,r.category,r.mode,r.type,r.note,r.startDate,r.endDate,r.startTime,r.endTime,r.status].join(' ').toLowerCase();", 1)
p.write_text(s)

# frontend renderer + client-side search
p = Path('Scripts.html')
s = p.read_text()
s = s.replace("const hay=norm([r.name,r.jobTitle,r.category,r.mode,r.type,r.startDate,r.endDate,r.startTime,r.endTime,r.status].join(' '));", "const hay=norm([r.name,r.jobTitle,r.category,r.mode,r.type,r.note,r.startDate,r.endDate,r.startTime,r.endTime,r.status].join(' '));", 1)
s = s.replace("<td>${esc(r.type||'—')}</td><td>${esc(formatDateRange(r.startDate,r.endDate))}", "<td>${esc(r.type||'—')}${String(r.note||'').trim()?`<small class=\"table-sub\">${esc(r.note)}</small>`:''}</td><td>${esc(formatDateRange(r.startDate,r.endDate))}", 1)
p.write_text(s)

# public privacy note: note is now intentionally visible
p = Path('Index.html')
s = p.read_text()
s = s.replace("Paparan umum tidak memaparkan emel, catatan peribadi, ulasan semakan atau identiti penyemak.", "Paparan umum tidak memaparkan emel, ulasan semakan atau identiti penyemak.", 1)
p.write_text(s)
