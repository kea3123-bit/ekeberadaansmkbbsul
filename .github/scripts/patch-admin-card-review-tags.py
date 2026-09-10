#!/usr/bin/env python3
from pathlib import Path

p = Path('web/config.js')
s = p.read_text(encoding='utf-8')

old = "    const allReviews = d?._reviewMeta?.rows || [];"
new = """    const metaReviews = Array.isArray(d?._reviewMeta?.rows) ? d._reviewMeta.rows : [];
    const recordReviews = (d.records || []).flatMap(record =>
      (Array.isArray(record?.reviewItems) ? record.reviewItems : []).map(item => Object.assign({}, item, {
        date: item?.date || record.date || '',
        email: item?.email || d?.user?.email || ''
      }))
    );
    // Own cards normally use _reviewMeta. Admin/employee cards may already carry
    // reviewItems from adminGetPunchCardMonth, so never discard those tags.
    const allReviews = metaReviews.length ? metaReviews : recordReviews;"""
if old not in s:
    raise SystemExit('allReviews anchor not found')
s = s.replace(old, new, 1)

marker = "      // Review screens: resolve the reviewer job title internally, then"
insert = r'''      // Kad Perakam Waktu Pegawai: the legacy admin loader renders the same
      // cardRowsHtml but never populated _reviewMeta, leaving TT KETUA blank.
      // Hydrate that metadata for the selected employee and re-render the card.
      if (typeof loadAdminCard === 'function') {
        const originalLoadAdminCard = loadAdminCard;
        loadAdminCard = async function(force = false) {
          await originalLoadAdminCard(force);
          const data = state.adminCardData;
          if (!data?.month || !state.token || !state.adminCardEmail) return;

          const targetEmail = String(data.user?.email || state.adminCardEmail || '').trim().toLowerCase();
          let rows = (data.records || []).flatMap(record =>
            (Array.isArray(record?.reviewItems) ? record.reviewItems : []).map(item => Object.assign({}, item, {
              date: item?.date || record.date || '',
              email: item?.email || targetEmail
            }))
          );

          // During staggered backend deployments older adminGetPunchCardMonth
          // responses may not yet contain reviewItems. Admins can already call
          // getTimeReviewData, so use it as the compatibility source.
          const decidedWithoutRole = rows.some(item => {
            const status = String(item?.reviewStatus || '').toUpperCase();
            return status && status !== 'BELUM DIAMBIL MAKLUM' && !String(item?.reviewerJobTitle || '').trim();
          });
          if (!rows.length || decidedWithoutRole) {
            try {
              const from = `${data.month}-01`;
              const to = `${data.month}-${String(data.daysInMonth || 31).padStart(2, '0')}`;
              const meta = await runServer('getTimeReviewData', state.token, from, to);
              const remoteRows = (meta?.rows || []).filter(item =>
                String(item?.email || '').trim().toLowerCase() === targetEmail
              );
              if (remoteRows.length) rows = remoteRows;
            } catch (_e) {
              // Embedded reviewItems remain the fallback when the remote metadata
              // request is unavailable.
            }
          }

          await fetchReviewerProfiles(rows);
          data._reviewMeta = {month: data.month, rows};
          renderAdminCard();
        };
      }

'''
if marker not in s:
    raise SystemExit('DOMContentLoaded review marker not found')
s = s.replace(marker, insert + marker, 1)

p.write_text(s, encoding='utf-8')
print('patched web/config.js')
