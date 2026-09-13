from pathlib import Path

p = Path('apps-script/61_Absence.gs')
s = p.read_text(encoding='utf-8')

old1 = """  let startDate = r.startDate || '';
  let endDate = r.endDate || startDate;
  if (fromDate && startDate < fromDate) startDate = fromDate;
  if (toDate && endDate > toDate) endDate = toDate;
"""
new1 = """  // Keep the original request period intact. The date filter decides whether
  // a record overlaps the requested window; it must not rewrite the period
  // shown in the table/PDF (e.g. 13-16 Sep filtered on 14 Sep stays 13-16 Sep).
  const startDate = r.startDate || '';
  const endDate = r.endDate || startDate;
"""
if old1 not in s:
    raise SystemExit('publicAbsenceListItem_ clipping block not found')
s = s.replace(old1, new1, 1)

old2 = """  const requests = rawRequests.filter(r=>r.endDate>=from&&r.startDate<=to).map(r=>{
    const x=publicAbsenceManagement_(r);
    if(x.startDate<from)x.startDate=from;
    if(x.endDate>to)x.endDate=to;
    return x;
  });
"""
new2 = """  // Filter by overlap only; preserve the original request start/end dates for display.
  const requests = rawRequests
    .filter(r=>r.endDate>=from&&r.startDate<=to)
    .map(r=>publicAbsenceManagement_(r));
"""
if old2 not in s:
    raise SystemExit('getAbsenceManagementData clipping block not found')
s = s.replace(old2, new2, 1)

p.write_text(s, encoding='utf-8')
