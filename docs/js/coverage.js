const COVERAGE_SECTIONS = ['top', 'trending', 'reader_favorites'];
const COLLECTION_INTERVAL_MS = 20 * 60 * 1000;

const COVERAGE_COL_LABELS = {
  date:             'Date / Time',
  top:              'Top',
  trending:         'Trending',
  reader_favorites: 'Favorites',
};

const COVERAGE_COL_ORDER = ['date', 'top', 'trending', 'reader_favorites'];

let cvSortDir = 1;  // 1 = descending (newest first), -1 = ascending
let cvJumpDate = '';
let cvJumpMonth = '';
let cvFilterSection = '';

function buildCoverageRows() {
  const runSection = {};
  stories.forEach(s => {
    s.appearances.forEach(a => {
      if (!a.run_time) return;
      if (!runSection[a.run_time]) runSection[a.run_time] = {};
      runSection[a.run_time][a.section] = (runSection[a.run_time][a.section] || 0) + 1;
    });
  });
  return Object.keys(runSection).map(run => {
    const row = { run };
    COVERAGE_SECTIONS.forEach(sec => { row[sec] = runSection[run][sec] || 0; });
    return row;
  });
}

function sortedCoverageRows(rows) {
  return rows.slice().sort((a, b) =>
    a.run < b.run ? cvSortDir : a.run > b.run ? -cvSortDir : 0
  );
}

function fmtCvDate(run) {
  const d = new Date(run.replace(' ', 'T'));
  return d.toLocaleString('en-US', { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' });
}

function fmtGapDuration(ms) {
  if (ms < 3600000) {
    const mins = Math.round(ms / (30 * 60000)) * 30;  // nearest 30 min
    return `${mins} min`;
  }
  const hrs = ms / 3600000;
  const rounded = Math.round(hrs * 2) / 2;  // nearest half-hour
  return `${rounded} hr${rounded !== 1 ? 's' : ''}`;
}

function interleaveGaps(rows) {
  const result = [];
  for (let i = 0; i < rows.length; i++) {
    result.push({ type: 'data', row: rows[i] });
    if (i < rows.length - 1) {
      const a = new Date(rows[i].run.replace(' ', 'T'));
      const b = new Date(rows[i + 1].run.replace(' ', 'T'));
      const gapMs = Math.abs(b - a);
      const missed = Math.round(gapMs / COLLECTION_INTERVAL_MS) - 1;
      if (missed >= 1) {
        result.push({ type: 'gap', missed, gapMs });
      }
    }
  }
  return result;
}

function renderCoverageInner(sorted) {
  let rows = cvJumpDate  ? sorted.filter(r => r.run.slice(0, 10) === cvJumpDate)
           : cvJumpMonth ? sorted.filter(r => r.run.slice(0, 7) === cvJumpMonth)
           : sorted;
  if (cvFilterSection) rows = rows.filter(r => r[cvFilterSection] > 0);

  const hdrs = COVERAGE_COL_ORDER.map(col => {
    if (col === 'date') {
      const arrow = cvSortDir === 1 ? ' ↓' : ' ↑';
      return `<th class="cv2-th cv2-sorted" data-col="date">${COVERAGE_COL_LABELS.date}${arrow}</th>`;
    }
    const active = cvFilterSection === col;
    return `<th class="cv2-th${active ? ' cv2-sorted' : ''}" data-col="${col}">${COVERAGE_COL_LABELS[col]}${active ? ' ✕' : ''}</th>`;
  }).join('');

  const colCount = COVERAGE_COL_ORDER.length;
  const interleaved = interleaveGaps(rows);

  const trs = interleaved.map(item => {
    if (item.type === 'gap') {
      const { gapMs } = item;
      return `<tr class="cv2-gap-row"><td colspan="${colCount}" class="cv2-gap-cell">⚠ Gap of ${fmtGapDuration(gapMs)}</td></tr>`;
    }
    const { row } = item;
    const cells = COVERAGE_COL_ORDER.map(col => {
      if (col === 'date') return `<td class="cv2-date">${fmtCvDate(row.run)}</td>`;
      const n = row[col];
      if (n > 0) {
        const tip = `Click to view ${COVERAGE_COL_LABELS[col]} stories from this run in the Data Table`;
        return `<td class="cv2-check"><button class="cv2-pill cv2-${col}" data-section="${col}" data-run="${row.run}" title="${tip}">✓</button></td>`;
      }
      return `<td class="cv2-check"></td>`;
    }).join('');
    return `<tr>${cells}</tr>`;
  }).join('');

  return `<table class="cv2-table"><thead><tr>${hdrs}</tr></thead><tbody>${trs}</tbody></table>`;
}

function renderCoverage() {
  const container = document.getElementById('coverage');
  if (!stories || !stories.length) {
    container.innerHTML = '<p class="cv-empty">No data loaded.</p>';
    return;
  }

  const allRows = buildCoverageRows();
  const sorted  = sortedCoverageRows(allRows);
  const dates   = [...new Set(allRows.map(r => r.run.slice(0, 10)))].sort().reverse();
  const months  = [...new Set(allRows.map(r => r.run.slice(0, 7)))].sort().reverse();

  function fmtMonth(ym) {
    const [y, m] = ym.split('-');
    return new Date(+y, +m - 1, 1).toLocaleString('en-US', { month: 'long', year: 'numeric' });
  }

  const monthOpts = months.map(m =>
    `<option value="${m}"${cvJumpMonth === m ? ' selected' : ''}>${fmtMonth(m)}</option>`
  ).join('');

  container.innerHTML =
    `<div class="cv2-wrap">` +
    `<div class="cv2-controls">` +
      `<span class="cv2-meta">${allRows.length} runs</span>` +
      `<label class="cv2-jump-label">Jump to month&nbsp;` +
        `<select id="cv2-jump-month"><option value="">— All —</option>${monthOpts}</select>` +
      `</label>` +
      `<label class="cv2-jump-label">Jump to date&nbsp;` +
        `<input type="date" id="cv2-jump" value="${cvJumpDate}" />` +
        `<datalist id="cv2-datelist">${dates.map(d => `<option value="${d}">`).join('')}</datalist>` +
      `</label>` +
      (cvJumpDate || cvJumpMonth || cvFilterSection ? `<button class="cv2-clear-btn" id="cv2-clear">Clear</button>` : '') +
    `</div>` +
    `<div class="cv2-scroll" id="cv2-scroll">${renderCoverageInner(sorted)}</div>` +
    `</div>`;

  container.querySelectorAll('.cv2-th').forEach(th => {
    th.addEventListener('click', () => {
      const col = th.dataset.col;
      if (col === 'date') {
        cvSortDir *= -1;
      } else {
        cvFilterSection = cvFilterSection === col ? '' : col;
      }
      renderCoverage();
    });
  });

  document.getElementById('cv2-scroll').addEventListener('click', e => {
    const cell = e.target.closest('.cv2-pill');
    if (cell) jumpFromCoverage(cell.dataset.section, cell.dataset.run);
  });

  const jumpEl = document.getElementById('cv2-jump');
  jumpEl.addEventListener('change', () => { cvJumpDate = jumpEl.value; cvJumpMonth = ''; renderCoverage(); });

  const monthEl = document.getElementById('cv2-jump-month');
  monthEl.addEventListener('change', () => { cvJumpMonth = monthEl.value; cvJumpDate = ''; renderCoverage(); });

  const clearEl = document.getElementById('cv2-clear');
  if (clearEl) clearEl.addEventListener('click', () => { cvJumpDate = ''; cvJumpMonth = ''; cvFilterSection = ''; renderCoverage(); });
}
