from pathlib import Path

# Harden public DTO so synthetic TIDAK MOHON rows always resolve current user identity.
p = Path('apps-script/61_Absence.gs')
s = p.read_text()
old = "function publicAbsenceListItem_(r, fromDate, toDate) {\n  let startDate = r.startDate || '';\n  let endDate = r.endDate || startDate;"
new = "function publicAbsenceListItem_(r, fromDate, toDate) {\n  const email = normalizeEmail_(r && r.email || '');\n  const user = email ? getUserByEmail_(email, false) : null;\n  let startDate = r.startDate || '';\n  let endDate = r.endDate || startDate;"
if old not in s:
    raise SystemExit('publicAbsenceListItem_ anchor not found')
s = s.replace(old, new, 1)
s = s.replace("    name:String(r.name||''),\n    jobTitle:String(r.jobTitle||''),\n    category:String(r.category||''),", "    name:String(r.name||(user&&user.name)||''),\n    jobTitle:String(r.jobTitle||(user&&user.jobTitle)||''),\n    category:String(r.category||(user&&user.category)||''),", 1)
p.write_text(s)

# Restore employee name in the management override renderer.
p = Path('web/config.js')
s = p.read_text()
old = "return `<tr><td><small class=\"table-sub\">${esc(r.jobTitle || '—')} · ${esc(r.category)}</small></td><td><b>${esc(r.mode === 'KEBERADAAN' ? 'Keberadaan' : 'Tidak Hadir')}</b></td>"
new = "return `<tr><td><b>${esc(r.name || '—')}</b><small class=\"table-sub\">${esc(r.jobTitle || '—')} · ${esc(r.category || '—')}</small></td><td><b>${esc(r.mode === 'KEBERADAAN' ? 'Keberadaan' : 'Tidak Hadir')}</b></td>"
if old not in s:
    raise SystemExit('patchedAbsenceManageFilters renderer anchor not found')
s = s.replace(old, new, 1)
p.write_text(s)

# Public renderer should never leave the Pegawai cell visually blank.
p = Path('Scripts.html')
s = p.read_text()
s = s.replace("<td><b>${esc(r.name)}</b><small class=\"table-sub\">${esc(r.jobTitle||'—')} · ${esc(r.category||'—')}</small></td>", "<td><b>${esc(r.name||'—')}</b><small class=\"table-sub\">${esc(r.jobTitle||'—')} · ${esc(r.category||'—')}</small></td>", 1)
p.write_text(s)
