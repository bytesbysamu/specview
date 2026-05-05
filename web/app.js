const API = '/api';
let activeProject = null;
let projects = [];

// ── Theme ──────────────────────────────────────
const savedTheme = localStorage.getItem('theme') || 'light';
if (savedTheme === 'dark') document.documentElement.setAttribute('data-theme', 'dark');

document.getElementById('theme-toggle').addEventListener('click', () => {
  const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
  document.documentElement.setAttribute('data-theme', isDark ? 'light' : 'dark');
  localStorage.setItem('theme', isDark ? 'light' : 'dark');
  document.getElementById('theme-toggle').textContent = isDark ? '☀️' : '🌙';
});
if (savedTheme === 'dark') document.getElementById('theme-toggle').textContent = '🌙';

// ── Date ───────────────────────────────────────
document.getElementById('masthead-date').textContent =
  new Date().toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });

// ── Init ───────────────────────────────────────
async function init() {
  const res = await fetch(`${API}/projects`);
  projects = await res.json();
  renderNav();
  if (projects.length > 0) selectProject(projects[0].id);
}

function renderNav() {
  const nav = document.getElementById('project-nav');
  nav.innerHTML = projects.map(p => `
    <button class="section-link" data-id="${p.id}">${p.name}</button>
  `).join('');
  nav.querySelectorAll('.section-link').forEach(btn => {
    btn.addEventListener('click', () => selectProject(btn.dataset.id));
  });
}

async function selectProject(id) {
  // Update nav active state
  document.querySelectorAll('.section-link').forEach(b =>
    b.classList.toggle('active', b.dataset.id === id)
  );

  // Close any expanded panel
  closeExpanded();

  // Show skeleton
  document.getElementById('file-grid').innerHTML = `
    <div class="empty-state">Loading…</div>`;

  const res = await fetch(`${API}/projects/${id}`);
  activeProject = await res.json();
  renderFileGrid();
}

function renderFileGrid() {
  const grid = document.getElementById('file-grid');
  const specs = activeProject.specs ?? [];

  // Distribute files across 3 columns newspaper-style
  const cols = [[], [], []];
  specs.forEach((s, i) => cols[i % 3].push(s));

  grid.innerHTML = cols.map((col, ci) => `
    <div class="file-column">
      ${ci === 0 ? `<div class="file-header">
        <span style="font-family:'Playfair Display',serif;font-size:16px;font-weight:700">${activeProject.name}</span>
      </div>` : '<div class="file-header"></div>'}
      ${col.map(s => `
        <div class="file-item" data-file="${s.filename}">
          <div class="file-item-title">${s.label}</div>
          <div class="file-item-meta">${s.filename}</div>
        </div>
      `).join('')}
    </div>
  `).join('');

  grid.querySelectorAll('.file-item').forEach(item => {
    item.addEventListener('click', () => openFile(item.dataset.file));
  });
}

function openFile(filename) {
  const spec = activeProject.specs.find(s => s.filename === filename);
  if (!spec) return;

  document.getElementById('expanded-project').textContent = activeProject.name;
  document.getElementById('expanded-file').textContent = filename;
  document.getElementById('expanded-title').textContent = spec.label;
  document.getElementById('expanded-body').innerHTML = spec.content
    ? marked.parse(spec.content)
    : '<p style="color:var(--ink-muted);font-style:italic">No content.</p>';

  const panel = document.getElementById('expanded-panel');
  panel.classList.add('active');

  // Scroll panel into view
  setTimeout(() => panel.scrollIntoView({ behavior: 'smooth', block: 'start' }), 50);
}

function closeExpanded() {
  document.getElementById('expanded-panel').classList.remove('active');
}

document.getElementById('expanded-close').addEventListener('click', closeExpanded);

init();
