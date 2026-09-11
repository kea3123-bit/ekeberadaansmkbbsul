from pathlib import Path

bridge = Path('apps-script/Bridges.gs')
text = bridge.read_text()

marker = "function pagesBridgeMethodAllowed_(method) {"
helper = """// Normal browser RPC keeps the HtmlService/postMessage transport. The burst\n// harness is server-to-server and gets direct JSON so its metrics are not\n// coupled to HtmlService serialization details.\nfunction renderPagesBridgeTransport_(responsePayload, targetOrigin, channel) {\n  if (String(channel || '') === 'perf-burst') {\n    return ContentService\n      .createTextOutput(JSON.stringify(responsePayload || null))\n      .setMimeType(ContentService.MimeType.JSON);\n  }\n  return renderPagesBridge_(responsePayload, targetOrigin);\n}\n\n"""
if helper not in text:
    if marker not in text:
        raise SystemExit('Bridges marker missing')
    text = text.replace(marker, helper + marker, 1)

count = text.count("return renderPagesBridge_({")
if count != 2:
    raise SystemExit(f'Expected 2 bridge response returns, got {count}')
text = text.replace("return renderPagesBridge_({", "return renderPagesBridgeTransport_({")
count = text.count("    }, origin);")
if count != 2:
    raise SystemExit(f'Expected 2 origin return suffixes, got {count}')
text = text.replace("    }, origin);", "    }, origin, channel);")
bridge.write_text(text)

perf = Path('apps-script/96_PerformanceBurstTest.gs')
text = perf.read_text()
old = r"""function parsePerformanceBurstBridgeResponse_(body) {
  const text = String(body || '');
  const match = text.match(/const RESPONSE = ([\s\S]*?);\s*\n\s*function deliver/);
  if (!match) throw new Error('Respons bridge ujian tidak dapat dibaca.');
  return JSON.parse(match[1]);
}
"""
new = r"""function parsePerformanceBurstBridgeResponse_(body) {
  const text = String(body || '').trim();
  if (!text) throw new Error('Respons bridge ujian kosong.');

  // Current perf-burst transport returns JSON directly. Retain the HtmlService
  // parser as a compatibility fallback for an older deployment during rollout.
  try {
    const direct = JSON.parse(text);
    if (direct && direct.type === 'EK_BRIDGE_RESULT') return direct;
  } catch (e) {}

  const match = text.match(/const RESPONSE = ([\s\S]*?);\s*\n\s*function deliver/);
  if (match) return JSON.parse(match[1]);

  const prefix = text.slice(0, 160).replace(/\s+/g, ' ');
  throw new Error(`Respons bridge ujian tidak dapat dibaca. Prefix=${prefix}`);
}
"""
if old not in text:
    raise SystemExit('Performance parser block missing')
text = text.replace(old, new, 1)
perf.write_text(text)
print('PERF_JSON_PATCH_OK')
