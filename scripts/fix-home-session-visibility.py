from pathlib import Path


def read(path):
    return Path(path).read_text(encoding="utf-8")


def write(path, text):
    Path(path).write_text(text, encoding="utf-8")


def replace_once(text, old, new, label):
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly 1 match, got {count}")
    return text.replace(old, new, 1)


# Main home screen: render both configured sessions; Sesi 2 stays hidden by default.
path = "Index.html"
src = read(path)
old = '''            <div class="schedule-grid home-schedule-grid">
              <div><span>Waktu Masuk</span><b id="activeInRef">—</b></div>
              <div><span>Waktu Balik</span><b id="activeOutRef">—</b></div>
              <div><span>Radius</span><b id="radiusM">—</b></div>
            </div>
            <div class="location-box">
              <div><b id="locationTitle">Lokasi semasa</b><div id="locationText" class="muted">Lokasi akan diperiksa semasa anda merakam waktu.</div></div>
              <span id="gpsDot" class="gps-dot"></span>
            </div>
            <div class="punch-times home-punch-times">
              <div class="time-card"><span>Rekod Masuk</span><strong id="activeInTime">—</strong></div>
              <div class="time-card"><span>Rekod Balik</span><strong id="activeOutTime">—</strong></div>
            </div>
'''
new = '''            <div id="homeScheduleGrid" class="schedule-grid home-schedule-grid single-session">
              <div class="home-session-summary">
                <span class="home-session-title">Sesi 1</span>
                <div class="home-session-values">
                  <div><span>Waktu Masuk</span><b id="s1InRef">—</b></div>
                  <div><span>Waktu Balik</span><b id="s1OutRef">—</b></div>
                </div>
              </div>
              <div id="homeSession2Schedule" class="home-session-summary hidden">
                <span class="home-session-title">Sesi 2</span>
                <div class="home-session-values">
                  <div><span>Waktu Masuk</span><b id="s2InRef">—</b></div>
                  <div><span>Waktu Balik</span><b id="s2OutRef">—</b></div>
                </div>
              </div>
              <div class="home-radius-card"><span>Radius</span><b id="radiusM">—</b></div>
            </div>
            <div class="location-box">
              <div><b id="locationTitle">Lokasi semasa</b><div id="locationText" class="muted">Lokasi akan diperiksa semasa anda merakam waktu.</div></div>
              <span id="gpsDot" class="gps-dot"></span>
            </div>
            <div id="homePunchTimes" class="punch-times home-punch-times single-session">
              <div class="time-card home-session-time-card">
                <span class="home-session-title">Sesi 1 · Rekod</span>
                <div class="home-record-values">
                  <div><span>Masuk</span><strong id="s1InTime">—</strong></div>
                  <div><span>Balik</span><strong id="s1OutTime">—</strong></div>
                </div>
              </div>
              <div id="homeSession2Times" class="time-card home-session-time-card hidden">
                <span class="home-session-title">Sesi 2 · Rekod</span>
                <div class="home-record-values">
                  <div><span>Masuk</span><strong id="s2InTime">—</strong></div>
                  <div><span>Balik</span><strong id="s2OutTime">—</strong></div>
                </div>
              </div>
            </div>
'''
src = replace_once(src, old, new, "home session markup")
write(path, src)


# Client rendering: determine Sesi 2 from actual configured times / actual Sesi 2 records.
path = "Scripts.html"
src = read(path)
old = '''    const hasSecondSession=!!(b.schedule.allowSecondSession||b.schedule.s2In||b.schedule.s2Out);
    const visibleSession=step.complete?(hasSecondSession?2:1):(Number(step.session)||1);
    const activeInRef=visibleSession===2?b.schedule.s2In:b.schedule.s1In, activeOutRef=visibleSession===2?b.schedule.s2Out:b.schedule.s1Out;
    const activeInTime=visibleSession===2?a.inTime2:a.inTime, activeOutTime=visibleSession===2?a.outTime2:a.outTime;
    text('activeInRef',activeInRef||'—'); text('activeOutRef',activeOutRef||'—'); text('radiusM',test?'DIABAIKAN':`${b.settings.radiusM} m`);
    text('activeInTime',activeInTime||'—'); text('activeOutTime',activeOutTime||'—');
'''
new = '''    // Paparan sesi adalah automatik dan tiada toggle manual.
    // Sesi 2 hanya dianggap wujud jika masa Sesi 2 dikonfigurasi atau rekod
    // Sesi 2 memang sudah tercatat; ALLOW_OPTIONAL_SECOND_SESSION sahaja tidak
    // memaksa kad Sesi 2 muncul untuk pengguna satu sesi.
    const hasSecondSession=!!(b.schedule.s2In||b.schedule.s2Out||a.inTime2||a.outTime2);
    text('s1InRef',b.schedule.s1In||'—'); text('s1OutRef',b.schedule.s1Out||'—');
    text('s2InRef',b.schedule.s2In||'—'); text('s2OutRef',b.schedule.s2Out||'—');
    text('s1InTime',a.inTime||'—'); text('s1OutTime',a.outTime||'—');
    text('s2InTime',a.inTime2||'—'); text('s2OutTime',a.outTime2||'—');
    text('radiusM',test?'DIABAIKAN':`${b.settings.radiusM} m`);
    document.getElementById('homeSession2Schedule')?.classList.toggle('hidden',!hasSecondSession);
    document.getElementById('homeSession2Times')?.classList.toggle('hidden',!hasSecondSession);
    document.getElementById('homeScheduleGrid')?.classList.toggle('single-session',!hasSecondSession);
    document.getElementById('homePunchTimes')?.classList.toggle('single-session',!hasSecondSession);
'''
src = replace_once(src, old, new, "renderBoot automatic session visibility")
write(path, src)


# Responsive presentation for one/two-session home cards.
path = "Styles.html"
src = read(path)
css = r'''

  /* Home session visibility — automatic, no user toggle */
  .home-schedule-grid{grid-template-columns:minmax(0,1fr) minmax(0,1fr) minmax(150px,.65fr)}
  .home-schedule-grid.single-session{grid-template-columns:minmax(0,1fr) minmax(150px,.65fr)}
  .home-session-summary{border-top:4px solid var(--blue)!important}
  .home-session-summary#homeSession2Schedule{border-top-color:var(--green)!important}
  .home-session-title{display:block!important;color:var(--ink)!important;font-size:12px!important;font-weight:900;letter-spacing:.04em;text-transform:uppercase;margin-bottom:9px}
  .home-session-values,.home-record-values{display:grid;grid-template-columns:1fr 1fr;gap:12px}
  .home-session-values>div+div,.home-record-values>div+div{border-left:1px solid var(--line);padding-left:12px}
  .home-session-values span,.home-record-values span{display:block;color:var(--muted);font-size:11px}
  .home-session-values b{display:block;margin-top:2px;font-size:19px}
  .home-radius-card{display:flex;flex-direction:column;justify-content:center}
  .home-punch-times{grid-template-columns:1fr 1fr}
  .home-punch-times.single-session{grid-template-columns:1fr}
  .home-session-time-card:first-child{border-top:4px solid var(--blue)}
  .home-session-time-card#homeSession2Times{border-top:4px solid var(--green)}
  .home-record-values strong{display:block;margin-top:2px;font-size:25px}
  @media(max-width:760px){
    .home-schedule-grid,.home-schedule-grid.single-session{grid-template-columns:1fr}
    .home-punch-times,.home-punch-times.single-session{grid-template-columns:1fr}
  }
  @media(max-width:380px){
    .home-session-values,.home-record-values{gap:8px}
    .home-session-values>div+div,.home-record-values>div+div{padding-left:8px}
    .home-record-values strong{font-size:22px}
  }
'''
src = replace_once(src, "</style>", css + "\n</style>", "append home session styles")
write(path, src)

print("Automatic home session visibility fix applied.")
