from pathlib import Path

p = Path('web/mobile-bootstrap.css')
s = p.read_text(encoding='utf-8')
marker = '/* Auth visibility contract: mobile layout must never override .hidden. */'
block = '''\n\n/* Auth visibility contract: mobile layout must never override .hidden.\n * The mobile .shell rule uses display:grid!important; without these more\n * specific selectors, Safari/iPhone can render the app shell below login. */\n.shell.hidden,\n.login-page.hidden {\n  display:none!important;\n}\n'''
if marker not in s:
    s = s.rstrip() + block + '\n'
p.write_text(s, encoding='utf-8')
