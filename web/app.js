const API = '/api';
let activeProject = null;
let activeFile = null;
let projects = [];

// ── Theme ──────────────────────────────────────
const savedTheme = localStorage.getItem('theme') || 'light';
if (savedTheme === 'dark') document.documentElement.setAttribute('data-theme', 'dark');
document.getElementById('theme-toggle').textContent = savedTheme === 'dark' ? '🌙' : '☀️';

document.getElementById('theme-toggle').addEventListener('click', () => {
  const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
  const next = isDark ? 'light' : 'dark';
  document.documentElement.setAttribute('data-theme', next);
  localStorage.setItem('theme', next);
  document.getElementById('theme-toggle').textContent = next === 'dark' ? '🌙' : '☀️';
});

// ── Date ───────────────────────────────────────
document.getElementById('masthead-date').textContent =
  new Date().toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });

// ── Helpers ────────────────────────────────────
function stripMarkdown(md = '') {
  return md
    .replace(/```[\s\S]*?```/g, '')   // code blocks
    .replace(/`[^`]*`/g, '')           // inline code
    .replace(/#{1,6}\s+/g, '')         // headings
    .replace(/\*\*([^*]*)\*\*/g, '$1') // bold
    .replace(/\*([^*]*)\*/g, '$1')     // italic
    .replace(/!\[.*?\]\(.*?\)/g, '')   // images
    .replace(/\[([^\]]+)\]\([^)]*\)/g, '$1') // links
    .replace(/[-*+]\s+/g, '')          // list bullets
    .replace(/\n+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

function teaser(content, maxLen = 120) {
  const plain = stripMarkdown(content);
  return plain.length > maxLen ? plain.slice(0, maxLen).trimEnd() + '…' : plain;
}

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
  document.querySelectorAll('#project-nav .section-link').forEach(b =>
    b.classList.toggle('active', b.dataset.id === id)
  );
  closeExpanded();
  activeFile = null;

  document.getElementById('file-grid').innerHTML =
    '<div class="empty-state">Loading…</div>';

  const res = await fetch(`${API}/projects/${id}`);
  activeProject = await res.json();
  renderFileGrid();
}

function renderFileGrid() {
  const grid = document.getElementById('file-grid');
  const specs = activeProject.specs ?? [];

  if (specs.length === 0) {
    grid.innerHTML = '<div class="empty-state">No files in this project.</div>';
    return;
  }

  // Distribute top-down across columns so columns are even, not left-heavy
  const numCols = Math.min(3, specs.length);
  const cols = Array.from({ length: numCols }, () => []);
  specs.forEach((s, i) => cols[i % numCols].push(s));

  grid.innerHTML = cols.map((col, ci) => `
    <div class="file-column">
      <div class="file-header">
        ${ci === 0
          ? `<span style="font-family:'Playfair Display',serif;font-size:16px;font-weight:700">${activeProject.name}</span>`
          : ''}
      </div>
      ${col.map(s => `
        <div class="file-item" data-file="${s.filename}">
          <div class="file-item-title">${s.label}</div>
          ${s.content ? `<div class="file-item-teaser">${teaser(s.content)}</div>` : ''}
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

  // Mark active file in grid
  activeFile = filename;
  document.querySelectorAll('.file-item').forEach(el =>
    el.classList.toggle('active', el.dataset.file === filename)
  );

  document.getElementById('expanded-project').textContent = activeProject.name;
  document.getElementById('expanded-file').textContent = filename;
  document.getElementById('expanded-title').textContent = spec.label;
  document.getElementById('expanded-body').innerHTML = spec.content
    ? marked.parse(spec.content)
    : '<p style="color:var(--ink-muted);font-style:italic">No content.</p>';

  const panel = document.getElementById('expanded-panel');
  panel.classList.add('active');
  setTimeout(() => panel.scrollIntoView({ behavior: 'smooth', block: 'start' }), 50);
}

function closeExpanded() {
  document.getElementById('expanded-panel').classList.remove('active');
  document.querySelectorAll('.file-item').forEach(el => el.classList.remove('active'));
  activeFile = null;
}

document.getElementById('expanded-close').addEventListener('click', () => {
  closeExpanded();
  // Scroll back up to the file grid
  document.getElementById('file-grid').scrollIntoView({ behavior: 'smooth', block: 'start' });
});

init();
