from pathlib import Path

p = Path('Styles.html')
s = p.read_text(encoding='utf-8')
old = '.pc-row-hadir td:nth-child(2){font-weight:800}'
new = '.pc-row-hadir td:nth-child(2){font-weight:400}'
if old not in s:
    raise SystemExit('expected punch-card bold rule not found')
s = s.replace(old, new, 1)
p.write_text(s, encoding='utf-8')
