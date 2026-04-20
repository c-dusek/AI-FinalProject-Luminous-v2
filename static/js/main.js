/* ── State ─────────────────────────────────────────────────────── */
const state = {
  students: [],
  projects: [],
  lastResult: null,
  selectedTechnique: 'linear_programming',
};

/* ── DOM refs ──────────────────────────────────────────────────── */
const dropZone          = document.getElementById('dropZone');
const fileInput         = document.getElementById('fileInput');
const parsingSpinner    = document.getElementById('parsingSpinner');
const optimizingSpinner = document.getElementById('optimizingSpinner');

const secUpload    = document.getElementById('section-upload');
const secConfigure = document.getElementById('section-configure');
const secResults   = document.getElementById('section-results');

let prefChart = null;

/* ── Toast ─────────────────────────────────────────────────────── */
function showToast(message, type = 'danger') {
  const el   = document.getElementById('appToast');
  const body = document.getElementById('toastBody');
  el.className = `toast align-items-center text-white border-0 bg-${type}`;
  body.textContent = message;
  bootstrap.Toast.getOrCreateInstance(el, { delay: 4000 }).show();
}

/* ── Step indicator ────────────────────────────────────────────── */
function setStep(n) {
  [1, 2, 3].forEach(i => {
    const el = document.getElementById(`step-${i}`);
    el.classList.remove('active', 'done');
    if (i < n)  el.classList.add('done');
    if (i === n) el.classList.add('active');
  });
}

/* ── Section navigation ────────────────────────────────────────── */
function showSection(name) {
  secUpload.classList.add('d-none');
  secConfigure.classList.add('d-none');
  secResults.classList.add('d-none');

  if (name === 'upload')    { secUpload.classList.remove('d-none');    setStep(1); }
  if (name === 'configure') { secConfigure.classList.remove('d-none'); setStep(2); }
  if (name === 'results')   { secResults.classList.remove('d-none');   setStep(3); }
}

/* ══════════════════════════════════════════════════════════════════
   SECTION 1 — FILE UPLOAD
══════════════════════════════════════════════════════════════════ */

/* Drag & drop */
dropZone.addEventListener('dragover', e => {
  e.preventDefault();
  dropZone.classList.add('drag-over');
});

['dragleave', 'dragend'].forEach(ev =>
  dropZone.addEventListener(ev, () => dropZone.classList.remove('drag-over'))
);

dropZone.addEventListener('drop', e => {
  e.preventDefault();
  dropZone.classList.remove('drag-over');
  const file = e.dataTransfer.files[0];
  if (file) uploadFile(file);
});

dropZone.addEventListener('click', () => fileInput.click());

fileInput.addEventListener('change', () => {
  if (fileInput.files[0]) uploadFile(fileInput.files[0]);
});

async function uploadFile(file) {
  const ext = file.name.split('.').pop().toLowerCase();
  if (!['csv', 'txt'].includes(ext)) {
    showToast('Only .csv and .txt files are supported.');
    return;
  }

  dropZone.classList.add('file-accepted');
  parsingSpinner.classList.remove('d-none');

  const form = new FormData();
  form.append('file', file);

  try {
    const res  = await fetch('/upload', { method: 'POST', body: form });
    const data = await res.json();

    if (!res.ok || data.error) {
      showToast(data.error || 'Upload failed.');
      dropZone.classList.remove('file-accepted');
      return;
    }

    state.students = data.students;
    state.projects = data.projects;
    buildConfigureSection();
    showSection('configure');
  } catch {
    showToast('Network error. Is the server running?');
    dropZone.classList.remove('file-accepted');
  } finally {
    parsingSpinner.classList.add('d-none');
    fileInput.value = '';
  }
}

/* Download template CSV */
document.getElementById('downloadTemplateBtn').addEventListener('click', e => {
  e.stopPropagation();
  const rows = [
    ['Name', 'Choice1', 'Choice2', 'Choice3', 'Choice4', 'Choice5', 'Choice6'],
    ['Alice Johnson', 'Autonomous Vehicles', 'Robotics', 'AI Research', 'Cybersecurity', 'IoT Systems', 'Data Analytics'],
    ['Bob Smith', 'Robotics', 'AI Research', 'Autonomous Vehicles', 'Data Analytics', 'IoT Systems', 'Cybersecurity'],
    ['Carol White', 'AI Research', 'Machine Learning', 'Robotics', 'Computer Vision', 'NLP', 'Autonomous Vehicles'],
  ];
  const csv  = rows.map(r => r.join(',')).join('\n');
  const blob = new Blob([csv], { type: 'text/csv' });
  const url  = URL.createObjectURL(blob);
  const a    = document.createElement('a');
  a.href = url; a.download = 'capstone_template.csv'; a.click();
  URL.revokeObjectURL(url);
});

/* ══════════════════════════════════════════════════════════════════
   SECTION 2 — CONFIGURE
══════════════════════════════════════════════════════════════════ */

function buildConfigureSection() {
  /* Student count badge */
  document.getElementById('studentCountBadge').textContent = state.students.length;

  /* Student preview table */
  const maxChoices = Math.max(...state.students.map(s => s.choices.length));
  const header = document.getElementById('studentPreviewHeader');
  header.innerHTML = '<th>Name</th>' +
    Array.from({ length: maxChoices }, (_, i) => `<th>Choice ${i + 1}</th>`).join('');

  const body    = document.getElementById('studentPreviewBody');
  const preview = state.students.slice(0, 8);
  body.innerHTML = preview.map(s => `
    <tr>
      <td>${esc(s.name)}</td>
      ${Array.from({ length: maxChoices }, (_, i) =>
        `<td>${s.choices[i] ? esc(s.choices[i]) : '<span class="text-muted">—</span>'}</td>`
      ).join('')}
    </tr>
  `).join('');

  const footer = document.getElementById('studentPreviewFooter');
  footer.textContent = state.students.length > 8
    ? `Showing 8 of ${state.students.length} students`
    : `${state.students.length} student${state.students.length !== 1 ? 's' : ''} loaded`;

  /* Interest counts (how many students ranked each project) */
  const interest = {};
  state.projects.forEach(p => { interest[p] = 0; });
  state.students.forEach(s => s.choices.forEach(p => { if (interest[p] !== undefined) interest[p]++; }));
  const maxInterest = Math.max(...Object.values(interest), 1);

  /* Project constraints table */
  const tbody = document.getElementById('constraintsBody');
  tbody.innerHTML = state.projects.map(proj => `
    <tr data-project="${esc(proj)}">
      <td>${esc(proj)}</td>
      <td class="text-center">
        <input type="number" class="form-control form-control-sm d-inline-block min-input"
               value="1" min="0" max="99" aria-label="Min for ${esc(proj)}" />
      </td>
      <td class="text-center">
        <input type="number" class="form-control form-control-sm d-inline-block max-input"
               value="5" min="1" max="99" aria-label="Max for ${esc(proj)}" />
      </td>
      <td class="text-center">
        <div class="d-flex align-items-center gap-1">
          <div class="interest-bar flex-grow-1">
            <div class="interest-fill" style="width:${Math.round(interest[proj] / maxInterest * 100)}%"></div>
          </div>
          <small class="text-muted" style="width:24px;text-align:right;">${interest[proj]}</small>
        </div>
      </td>
    </tr>
  `).join('');
}

/* Apply global max */
document.getElementById('applyGlobalBtn').addEventListener('click', () => {
  const val = parseInt(document.getElementById('globalMax').value, 10);
  if (isNaN(val) || val < 1) { showToast('Enter a valid max value.'); return; }
  document.querySelectorAll('#constraintsBody .max-input').forEach(inp => { inp.value = val; });
});

/* Back to upload */
document.getElementById('backToUploadBtn').addEventListener('click', () => {
  dropZone.classList.remove('file-accepted');
  showSection('upload');
});

/* ── Run optimization ─────────────────────────────────────────── */
document.getElementById('runOptBtn').addEventListener('click', async () => {
  const constraints = gatherConstraints();
  if (!constraints) return;
  state.selectedTechnique = document.getElementById('techniqueSelect').value;

  document.getElementById('runOptBtn').disabled = true;
  optimizingSpinner.classList.remove('d-none');

  try {
    const res  = await fetch('/optimize', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({
        students: state.students,
        constraints,
        technique: state.selectedTechnique,
      }),
    });
    const data = await res.json();

    if (!res.ok || data.error) {
      showToast(data.error || 'Optimization failed.');
      return;
    }

    state.lastResult = data;
    renderResults(data);
    showSection('results');
  } catch {
    showToast('Network error during optimization.');
  } finally {
    document.getElementById('runOptBtn').disabled = false;
    optimizingSpinner.classList.add('d-none');
  }
});

function gatherConstraints() {
  const rows = document.querySelectorAll('#constraintsBody tr');
  const constraints = {};
  let valid = true;

  rows.forEach(row => {
    const proj = row.dataset.project;
    const min  = parseInt(row.querySelector('.min-input').value, 10);
    const max  = parseInt(row.querySelector('.max-input').value, 10);

    if (isNaN(min) || isNaN(max) || min < 0 || max < 1 || min > max) {
      showToast(`Invalid min/max for "${proj}". Ensure min ≥ 0, max ≥ 1, and min ≤ max.`);
      valid = false;
    }
    constraints[proj] = { min, max };
  });

  return valid ? constraints : null;
}

/* ══════════════════════════════════════════════════════════════════
   SECTION 3 — RESULTS
══════════════════════════════════════════════════════════════════ */

function renderResults(data) {
  const { assignments, project_groups, stats } = data;
  const total = stats.total_students;
  const techniqueLabel = stats.technique_label || humanizeTechnique(stats.technique || state.selectedTechnique);

  /* Subtitle */
  document.getElementById('resultsSubtitle').textContent =
    `${total} student${total !== 1 ? 's' : ''} assigned across ${Object.keys(project_groups).length} projects.`;
  document.getElementById('techniqueBanner').textContent =
    `${techniqueLabel} was used to produce these assignments. Objective score: ${stats.objective_value}.`;

  /* ── Stat cards ── */
  const rc = stats.rank_counts || {};
  const got1   = rc['1'] || 0;
  const top3   = (rc['1'] || 0) + (rc['2'] || 0) + (rc['3'] || 0);
  const ranked = total - (stats.unranked_count || 0);

  const statDefs = [
    { value: total,                           label: 'Total Students',       color: '#1a237e' },
    { value: pct(got1, total) + '%',          label: 'Got First Choice',     color: '#27ae60' },
    { value: pct(top3, total) + '%',          label: 'Got Top-3 Choice',     color: '#1565c0' },
    { value: stats.unranked_count || 0,       label: 'Assigned Outside Prefs', color: '#e53935' },
  ];

  document.getElementById('statCards').innerHTML = statDefs.map(s => `
    <div class="col-6 col-md-3">
      <div class="stat-card">
        <div class="stat-value" style="color:${s.color};">${s.value}</div>
        <div class="stat-label">${s.label}</div>
      </div>
    </div>
  `).join('');

  /* ── Chart ── */
  const labels  = [];
  const values  = [];
  const colors  = ['#f9a825','#43a047','#1e88e5','#8e24aa','#00acc1','#e53935','#546e7a'];

  const maxRank = Math.max(...Object.keys(rc).map(Number), 6);
  for (let r = 1; r <= maxRank; r++) {
    if (rc[String(r)]) { labels.push(`Choice ${r}`); values.push(rc[String(r)]); }
  }
  if (stats.unranked_count) { labels.push('Outside Prefs'); values.push(stats.unranked_count); }

  if (prefChart) prefChart.destroy();
  prefChart = new Chart(document.getElementById('prefChart'), {
    type: 'doughnut',
    data: {
      labels,
      datasets: [{ data: values, backgroundColor: colors.slice(0, values.length), borderWidth: 2 }],
    },
    options: {
      plugins: {
        legend: { position: 'bottom', labels: { font: { size: 11 } } },
        tooltip: {
          callbacks: {
            label: ctx => ` ${ctx.parsed} student${ctx.parsed !== 1 ? 's' : ''} (${pct(ctx.parsed, total)}%)`,
          },
        },
      },
    },
  });

  /* ── All-assignments table ── */
  const tbody = document.getElementById('assignmentsBody');
  tbody.innerHTML = Object.entries(assignments)
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([name, info]) => `
      <tr>
        <td>${esc(name)}</td>
        <td>${esc(info.project)}</td>
        <td class="text-center">${rankBadge(info.rank)}</td>
      </tr>
    `).join('');

  /* ── Project group cards ── */
  document.getElementById('projectGroupCards').innerHTML =
    Object.entries(project_groups)
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([proj, members]) => `
        <div class="col-sm-6 col-lg-4">
          <div class="project-group-card">
            <div class="group-header">
              <span>${esc(proj)}</span>
              <span class="badge bg-white text-primary">${members.length}</span>
            </div>
            <div class="group-body">
              ${members.map(m => `<span class="student-chip">${esc(m)}</span>`).join('')}
            </div>
          </div>
        </div>
      `).join('');
}

/* ── Download CSV ─────────────────────────────────────────────── */
document.getElementById('downloadCsvBtn').addEventListener('click', async () => {
  if (!state.lastResult) return;
  try {
    const res  = await fetch('/download', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify(state.lastResult),
    });
    const blob = await res.blob();
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement('a');
    a.href = url; a.download = 'capstone_assignments.csv'; a.click();
    URL.revokeObjectURL(url);
  } catch {
    showToast('Download failed.');
  }
});

/* ── Navigation buttons ───────────────────────────────────────── */
document.getElementById('backToConfigBtn').addEventListener('click', () => showSection('configure'));

document.getElementById('startOverBtn').addEventListener('click', () => {
  state.students = [];
  state.projects = [];
  state.lastResult = null;
  state.selectedTechnique = 'linear_programming';
  dropZone.classList.remove('file-accepted');
  document.getElementById('techniqueSelect').value = 'linear_programming';
  showSection('upload');
});

/* ── Helpers ──────────────────────────────────────────────────── */
function esc(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function pct(n, total) {
  return total === 0 ? 0 : Math.round((n / total) * 100);
}

function humanizeTechnique(value) {
  return String(value || '')
    .split('_')
    .filter(Boolean)
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

function rankBadge(rank) {
  if (!rank) return `<span class="rank-badge rank-other">—</span>`;
  const cls = rank <= 6 ? `rank-${rank}` : 'rank-other';
  return `<span class="rank-badge ${cls}">#${rank}</span>`;
}
