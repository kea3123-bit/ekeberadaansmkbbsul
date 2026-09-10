from pathlib import Path

p = Path('web/config.js')
s = p.read_text(encoding='utf-8')

old_absence = '''      const reviewerName = r.reviewerName || r.reviewedBy || '—';
      const reviewerEmail = r.reviewerName && r.reviewedBy ? `<small class=\"table-sub\">${esc(r.reviewedBy)}</small>` : '';
      const reviewDone = `<b>${esc(reviewerName)}</b>${tagHtml(r.reviewerJobTitle)}${reviewerEmail}<small class=\"table-sub\">${esc(r.reviewedAt || '')}</small><small class=\"table-sub\">${esc(r.comment || '')}</small>`;'''
new_absence = '''      const reviewerRole = String(r.reviewerJobTitle || r.reviewerCategory || (r.reviewerIsAdmin ? 'Pentadbir Sistem' : 'Pengurusan')).trim() || 'Pengurusan';
      const reviewVerb = r.status === 'DILULUSKAN' ? 'Diluluskan' : r.status === 'DITOLAK' ? 'Ditolak' : 'Disemak';
      const reviewDone = `<div class=\"review-by-role\"><b>${esc(reviewVerb)} oleh</b>${tagHtml(reviewerRole)}</div><small class=\"table-sub\">Tarikh/Masa: ${esc(r.reviewedAt || '—')}</small><small class=\"table-sub\">Catatan: ${esc(r.comment || '—')}</small>`;'''
if old_absence not in s:
    raise SystemExit('absence reviewer block not found')
s = s.replace(old_absence, new_absence, 1)

old_time = '''      const reviewCell = reviewed
        ? `<b>${esc(r.reviewStatus)} oleh ${esc(r.reviewerName || r.reviewedBy || '—')}</b>${tagHtml(r.reviewerJobTitle)}${r.reviewerName && r.reviewedBy ? `<small class=\"table-sub\">${esc(r.reviewedBy)}</small>` : ''}<small class=\"table-sub\">${esc(r.reviewedAt || '')}</small><small class=\"table-sub\">${esc(r.comment || '')}</small>`
        : `<div class=\"row-actions\"><button class=\"action-link approve-link\" onclick='openTimeReview(${JSON.stringify(r.id)},\"DIAMBIL MAKLUM\")'>Diambil Maklum</button><button class=\"action-link warn-link\" onclick='openTimeReview(${JSON.stringify(r.id)},\"DITOLAK\")'>Ditolak</button></div>`;'''
new_time = '''      const reviewerRole = String(r.reviewerJobTitle || r.reviewerCategory || (r.reviewerIsAdmin ? 'Pentadbir Sistem' : 'Pentadbir Sistem')).trim() || 'Pentadbir Sistem';
      const reviewVerb = r.reviewStatus === 'DIAMBIL MAKLUM' ? 'Diambil maklum' : r.reviewStatus === 'DITOLAK' ? 'Ditolak' : String(r.reviewStatus || 'Disemak');
      const reviewCell = reviewed
        ? `<div class=\"review-by-role\"><b>${esc(reviewVerb)} oleh</b>${tagHtml(reviewerRole)}</div><small class=\"table-sub\">Tarikh/Masa: ${esc(r.reviewedAt || '—')}</small><small class=\"table-sub\">Catatan: ${esc(r.comment || '—')}</small>`
        : `<div class=\"row-actions\"><button class=\"action-link approve-link\" onclick='openTimeReview(${JSON.stringify(r.id)},\"DIAMBIL MAKLUM\")'>Diambil Maklum</button><button class=\"action-link warn-link\" onclick='openTimeReview(${JSON.stringify(r.id)},\"DITOLAK\")'>Ditolak</button></div>`;'''
if old_time not in s:
    raise SystemExit('time reviewer block not found')
s = s.replace(old_time, new_time, 1)

old_css = '''    .reviewer-role-tag{display:inline-flex;align-items:center;max-width:100%;margin-top:4px;padding:2px 7px;border-radius:999px;background:rgba(7,83,185,.1);border:1px solid rgba(7,83,185,.22);color:#0753b9;font-size:11px;font-weight:800;line-height:1.25;white-space:normal;text-align:center}
    .pc-sign .reviewer-role-tag{margin-top:0;padding:2px 5px;font-size:8px;line-height:1.15}'''
new_css = '''    .reviewer-role-tag{display:inline-flex;align-items:center;max-width:100%;margin-top:4px;padding:2px 7px;border-radius:999px;background:rgba(7,83,185,.1);border:1px solid rgba(7,83,185,.22);color:#0753b9;font-size:11px;font-weight:800;line-height:1.25;white-space:normal;text-align:center}
    .review-by-role{display:flex;flex-wrap:wrap;align-items:center;gap:5px;margin-bottom:3px}
    .review-by-role .reviewer-role-tag{margin-top:0}
    .pc-sign .reviewer-role-tag{margin-top:0;padding:2px 5px;font-size:8px;line-height:1.15}'''
if old_css not in s:
    raise SystemExit('reviewer css anchor not found')
s = s.replace(old_css, new_css, 1)

# The reviewer profile lookup may still use the internal reviewer email to resolve
# the current job title, but do not copy/display the reviewer name in this layer.
s = s.replace("      if (!r.reviewerName) r.reviewerName = profile.name || '';\n", '', 1)
s = s.replace('// Review screens: enrich reviewer email with current name/job title, then\n      // render a compact role tag below the approver.', '// Review screens: resolve the reviewer job title internally, then\n      // render only the role tag, decision time and comment (never reviewer name/email).', 1)

p.write_text(s, encoding='utf-8')
print('patched web/config.js')
