from pathlib import Path

root = Path('.')

# --- Scripts.html: build two dedicated print pages ---
p = root / 'Scripts.html'
s = p.read_text(encoding='utf-8')
old = "  function printMyPunchCard(){window.print();}"
new = r'''  function clearPunchCardPrintPages(){document.getElementById('punchCardPrintPages')?.remove();}
  function buildPunchCardPrintPages(){
    const d=state.myCardData,source=document.getElementById('physicalPunchCard');
    if(!d||!source)return null;
    clearPunchCardPrintPages();
    const host=document.createElement('div');host.id='punchCardPrintPages';host.className='punch-card-print-pages';
    [1,2].forEach(half=>{
      const page=document.createElement('section');page.className='punch-card-print-page';page.dataset.half=String(half);
      const card=source.cloneNode(true);card.classList.add('physical-card-print');card.removeAttribute('id');
      const rows=card.querySelector('#myCardRows');if(rows){rows.innerHTML=cardRowsHtml(d,half);rows.removeAttribute('id');}
      const loading=card.querySelector('#pcLoading');if(loading)loading.remove();
      card.querySelectorAll('[id]').forEach(el=>el.removeAttribute('id'));
      page.appendChild(card);host.appendChild(page);
    });
    document.body.appendChild(host);return host;
  }
  function printMyPunchCard(){
    if(!state.myCardData)return toast('Kad Perakam Waktu belum dimuatkan.');
    if(!buildPunchCardPrintPages())return toast('Kad Perakam Waktu tidak dapat disediakan untuk cetakan.');
    window.addEventListener('afterprint',clearPunchCardPrintPages,{once:true});
    requestAnimationFrame(()=>requestAnimationFrame(()=>window.print()));
  }'''
if old not in s:
    raise SystemExit('printMyPunchCard anchor not found')
s = s.replace(old, new, 1)
p.write_text(s, encoding='utf-8')

# --- Styles.html: A4, two pages, full-height card ---
p = root / 'Styles.html'
s = p.read_text(encoding='utf-8')
anchor = "\n\n  /* =========================================================\n     v5 — Visual refresh berinspirasikan warna logo sekolah"
css = r'''

  /* Dedicated two-page punch-card print document. Hidden on screen. */
  .punch-card-print-pages{display:none}

  @page{size:A4 portrait;margin:0}
  @media print{
    html,body{width:210mm!important;margin:0!important;padding:0!important;background:#fff!important}
    body>*:not(#punchCardPrintPages){display:none!important}
    #punchCardPrintPages{display:block!important;width:210mm!important;margin:0!important;padding:0!important}
    .punch-card-print-page{
      width:210mm!important;
      height:297mm!important;
      margin:0!important;
      padding:7mm 8mm!important;
      display:flex!important;
      align-items:stretch!important;
      justify-content:stretch!important;
      overflow:hidden!important;
      break-after:page;
      page-break-after:always;
      box-sizing:border-box!important;
    }
    .punch-card-print-page:last-child{break-after:auto;page-break-after:auto}
    .punch-card-print-page .physical-card{
      width:194mm!important;
      height:283mm!important;
      min-height:283mm!important;
      max-width:none!important;
      margin:0!important;
      border:1px solid #89927b!important;
      border-radius:0!important;
      box-shadow:none!important;
      display:flex!important;
      flex-direction:column!important;
      overflow:hidden!important;
      -webkit-print-color-adjust:exact!important;
      print-color-adjust:exact!important;
    }
    .punch-card-print-page .pc-topline{flex:0 0 24mm!important;height:24mm!important;padding:4mm 7mm 0!important}
    .punch-card-print-page .pc-emblem-wrap{flex:0 0 14mm!important;height:14mm!important;margin-top:-10mm!important}
    .punch-card-print-page .pc-emblem{width:20mm!important;height:16mm!important;filter:grayscale(.25) contrast(.85)!important}
    .punch-card-print-page .pc-info-row{flex:0 0 12mm!important;min-height:12mm!important;padding:1.5mm 6mm 2mm!important;grid-template-columns:28mm 1fr!important}
    .punch-card-print-page .pc-title-row{flex:0 0 21mm!important;min-height:21mm!important;padding:3mm 6mm 2mm!important}
    .punch-card-print-page .pc-table-wrap{flex:1 1 auto!important;min-height:0!important;overflow:visible!important;display:flex!important}
    .punch-card-print-page .pc-table{width:100%!important;min-width:0!important;height:100%!important;table-layout:fixed!important}
    .punch-card-print-page .pc-table thead tr:first-child th{height:7mm!important}
    .punch-card-print-page .pc-table thead th{height:8mm!important}
    .punch-card-print-page .pc-table tbody{height:auto!important}
    .punch-card-print-page .pc-table tbody tr{height:auto!important}
    .punch-card-print-page .pc-table tbody td,
    .punch-card-print-page .pc-weekend-full,
    .punch-card-print-page .pc-absence-full{height:auto!important;min-height:0!important}
    .punch-card-print-page .pc-warning{flex:0 0 16mm!important;padding:3mm 7mm 3mm!important;margin:0!important}
    .punch-card-print-page .pc-warning p{margin-top:1mm!important}
  }
'''
if anchor not in s:
    raise SystemExit('Styles print insertion anchor not found')
s = s.replace(anchor, css + anchor, 1)
p.write_text(s, encoding='utf-8')
