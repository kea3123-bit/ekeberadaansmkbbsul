#!/usr/bin/env python3
from pathlib import Path
import re

LABEL = 'URUSAN PEPERIKSAAN'

core_path = Path('apps-script/00_Core.gs')
core = core_path.read_text(encoding='utf-8')

old_abs = "'AKTIVITI SUKAN/PERMAINAN', 'LAIN-LAIN']"
new_abs = "'AKTIVITI SUKAN/PERMAINAN', 'URUSAN PEPERIKSAAN', 'LAIN-LAIN']"
old_pre = "'MESYUARAT/TAKLIMAT (KPM)', 'LAIN-LAIN - KEBERADAAN']"
new_pre = "'MESYUARAT/TAKLIMAT (KPM)', 'URUSAN PEPERIKSAAN', 'LAIN-LAIN - KEBERADAAN']"

if new_abs not in core:
    if old_abs not in core:
        raise SystemExit('ABSENCE_TYPES target not found')
    core = core.replace(old_abs, new_abs, 1)
if new_pre not in core:
    if old_pre not in core:
        raise SystemExit('PRESENCE_TYPES target not found')
    core = core.replace(old_pre, new_pre, 1)
core_path.write_text(core, encoding='utf-8')

scripts_path = Path('Scripts.html')
scripts = scripts_path.read_text(encoding='utf-8')

def add_to_required_array(src, var_name, before_label):
    pattern = re.compile(r'(const\s+' + re.escape(var_name) + r'\s*=\s*\[)(.*?)(\];)', re.S)
    m = pattern.search(src)
    if not m:
        raise SystemExit(f'{var_name} block not found')
    body = m.group(2)
    if f"'{LABEL}'" in body:
        return src
    needle = f"'{before_label}'"
    if needle not in body:
        raise SystemExit(f'{var_name} insertion target not found')
    body = body.replace(needle, f"'{LABEL}',{needle}", 1)
    return src[:m.start(2)] + body + src[m.end(2):]

scripts = add_to_required_array(scripts, 'requiredAbsenceTypes', 'LAIN-LAIN')
scripts = add_to_required_array(scripts, 'requiredPresenceTypes', 'LAIN-LAIN - KEBERADAAN')
scripts_path.write_text(scripts, encoding='utf-8')

# Contract checks: the label must exist exactly once in each backend list and
# exactly once in each frontend compatibility list.
core_now = core_path.read_text(encoding='utf-8')
scripts_now = scripts_path.read_text(encoding='utf-8')
if core_now.count("'URUSAN PEPERIKSAAN'") != 2:
    raise SystemExit('Backend exam label count must be exactly 2')
for var_name in ('requiredAbsenceTypes', 'requiredPresenceTypes'):
    m = re.search(r'const\s+' + re.escape(var_name) + r'\s*=\s*\[(.*?)\];', scripts_now, re.S)
    if not m or m.group(1).count("'URUSAN PEPERIKSAAN'") != 1:
        raise SystemExit(f'{var_name} must contain exam label exactly once')

print('Added URUSAN PEPERIKSAAN to Tidak Hadir and Keberadaan dropdowns.')
