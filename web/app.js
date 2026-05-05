const API = '/api';
const REFRESH_INTERVAL = 30_000; // poll every 30s

let allProjects = [];
let activeSection = 'all';
let activeFile = null;
let activeProject = null;
let knownCount = 0;
let searchQuery = '';

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

document.getElementById('masthead-date').textContent =
  new Date().toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });

// ── Categorise ────────────────────────────────
const SECTIONS = [
  { id: 'context',     label: 'Context',      icon: '📐' },
  { id: 'all',         label: 'All',           icon: '' },
  { id: 'products',    label: 'Products',      icon: '🚀' },
  { id: 'platform',    label: 'Platform',      icon: '⚙️' },
  { id: 'braindumps',  label: 'Braindumps',    icon: '🧠' },
  { id: 'engineering', label: 'Engineering',   icon: '🔧' },
  { id: 'devex',       label: 'Dev Experience',icon: '🛠' },
  { id: 'distribution',label: 'Distribution',  icon: '📣' },
  { id: 'status',      label: 'Status',        icon: '📊' },
  { id: 'misc',        label: 'Misc',          icon: '📁' },
];

function categorise(id) {
  const s = id.toLowerCase();
  if (/braindump/.test(s) || /phase\d+-.*braindump/.test(s) || /model-chains-braindump/.test(s)) return 'braindumps';
  if (/^(bubls|trendfy|howdays|relateai|babyname|photoshoot|wardrobai|tennispartner|relationship|specdocv2|michi|portfolio|cold-dm-templates|voice|twitter-bio|linkedin|reddit|the-post|landing-copy|waitlist|github-readme)/.test(s)) return 'products';
  if (/^(saas|v2-spec-doc|spec-doc-flask|spec-doc-api|spec-doc-self|aligning-spec-doc|deployment-stack|saas-feature|saas-port|spec-doc-improvements|status-|run-2026)/.test(s)) return 'platform';
  if (/^(chain|workflow|pipeline|bootstrap|batch|text-chains|two-separate|parallel|iteration|generate-next|run-chain|raise-max|runtime-cancel|retry-recovery)/.test(s)) return 'engineering';
  if (/^(dev-experience|e2e|test-|gherkin|codebase-cleanup|architecture-cleanup|apply-button|integration-test|express-retirement|modular-restructure|directory-listing|port-)/.test(s)) return 'devex';
  if (/^(landing-page|distribution-experiment|the-post|waitlist|linkedin-update|twitter|reddit-post|cold-dm|voice-demo|voice-input|github-readme)/.test(s)) return 'distribution';
  if (/^(status|phase2-|phase3-|phase4-|phase5-|saas-feature-roadmap|saas-port-roadmap|spec-doc-improvements|run-2026)/.test(s)) return 'status';
  return 'misc';
}

// ── Context files ─────────────────────────────
const CONTEXT_FILES = [
  { key: 'builder',    label: 'Builder',    desc: 'How to build with spec-doc' },
  { key: 'principles', label: 'Principles', desc: 'Core development principles' },
  { key: 'codebase',   label: 'Codebase',   desc: 'Codebase overview & conventions' },
  { key: 'references', label: 'References', desc: 'External references & links' },
  { key: 'quality',    label: 'Quality',    desc: 'Quality rules & linting' },
  { key: 'versions',   label: 'Versions',   desc: 'Deployment fact sheet' },
];

// ── Helpers ────────────────────────────────────
function stripMarkdown(md = '') {
  return md
    .replace(/```[\s\S]*?```/g, '')
    .replace(/`[^`]*`/g, '')
    .replace(/#{1,6}\s+/g, '')
    .replace(/\*\*([^*]*)\*\*/g, '$1')
    .replace(/\*([^*]*)\*/g, '$1')
    .replace(/!\[.*?\]\(.*?\)/g, '')
    .replace(/\[([^\]]+)\]\([^)]*\)/g, '$1')
    .replace(/[-*+]\s+/g, '')
    .replace(/\n+/g, ' ').replace(/\s+/g, ' ').trim();
}

function teaser(content, len = 140) {
  const plain = stripMarkdown(content);
  return plain.length > len ? plain.slice(0, len).trimEnd() + '…' : plain;
}

function sectionFor(id) {
  return SECTIONS.find(s => s.id === id) || SECTIONS[SECTIONS.length - 1];
}

// ── Init & polling ────────────────────────────
async function init() {
  await loadProjects();
  setInterval(checkForUpdates, REFRESH_INTERVAL);
}

async function loadProjects() {
  const res = await fetch(`${API}/projects`);
  allProjects = await res.json();
  knownCount = allProjects.length;
  renderNav();
  renderSection(activeSection);
}

async function checkForUpdates() {
  try {
    const res = await fetch(`${API}/projects`);
    const fresh = await res.json();
    if (fresh.length !== knownCount) {
      allProjects = fresh;
      knownCount = fresh.length;
      showUpdateBanner(fresh.length - knownCount);
      renderNav();
      if (activeSection !== 'context') renderSection(activeSection);
    }
  } catch (_) {}
}

function showUpdateBanner(diff) {
  const existing = document.getElementById('update-banner');
  if (existing) existing.remove();
  const b = document.createElement('div');
  b.id = 'update-banner';
  b.className = 'update-banner';
  b.innerHTML = `${diff > 0 ? `+${diff} new` : 'Projects updated'} · <button onclick="document.getElementById('update-banner').remove()">dismiss</button>`;
  document.querySelector('.section-nav').after(b);
}

// ── Nav ───────────────────────────────────────
function renderNav() {
  const counts = {};
  allProjects.forEach(p => {
    const cat = categorise(p.id);
    counts[cat] = (counts[cat] || 0) + 1;
    counts['all'] = (counts['all'] || 0) + 1;
  });

  const nav = document.getElementById('project-nav');
  nav.innerHTML = SECTIONS.map(s => {
    const count = s.id === 'context' ? CONTEXT_FILES.length : (counts[s.id] ?? '');
    const label = count !== '' ? `${s.icon} ${s.label} <span class="section-count">${count}</span>` : `${s.icon} ${s.label}`;
    return `<button class="section-link${s.id === activeSection ? ' active' : ''}" data-section="${s.id}">${label}</button>`;
  }).join('');

  nav.querySelectorAll('.section-link').forEach(btn => {
    btn.addEventListener('click', () => {
      activeSection = btn.dataset.section;
      searchQuery = '';
      document.getElementById('search-input').value = '';
      closeExpanded();
      renderSection(activeSection);
      nav.querySelectorAll('.section-link').forEach(b => b.classList.toggle('active', b.dataset.section === activeSection));
    });
  });
}

// ── Search ────────────────────────────────────
document.getElementById('search-input').addEventListener('input', e => {
  searchQuery = e.target.value.trim().toLowerCase();
  if (activeSection !== 'context') renderSection(activeSection);
});

// ── Section render ────────────────────────────
function renderSection(section) {
  if (section === 'context') {
    document.getElementById('search-bar').style.display = 'none';
    renderContextSection();
    return;
  }
  document.getElementById('search-bar').style.display = '';
  let projects = section === 'all'
    ? allProjects
    : allProjects.filter(p => categorise(p.id) === section);

  if (searchQuery) {
    projects = projects.filter(p =>
      p.name.toLowerCase().includes(searchQuery) ||
      p.id.toLowerCase().includes(searchQuery)
    );
  }

  const countEl = document.getElementById('search-count');
  countEl.textContent = searchQuery ? `${projects.length} match${projects.length !== 1 ? 'es' : ''}` : '';

  renderProjectGrid(projects);
}

function renderContextSection() {
  const grid = document.getElementById('file-grid');
  grid.innerHTML = `
    <div class="context-grid">
      ${CONTEXT_FILES.map(f => `
        <div class="context-card" data-key="${f.key}">
          <div class="context-card__label">${f.label}</div>
          <div class="context-card__desc">${f.desc}</div>
        </div>
      `).join('')}
    </div>`;

  grid.querySelectorAll('.context-card').forEach(card => {
    card.addEventListener('click', () => openContextFile(card.dataset.key));
  });
}

async function openContextFile(key) {
  const ctx = CONTEXT_FILES.find(f => f.key === key);
  const res = await fetch(`${API}/context/${key}`);
  const data = await res.json();
  const content = data.content || data.text || '';

  document.getElementById('expanded-project').textContent = 'Context';
  document.getElementById('expanded-file').textContent = `${key}.md`;
  document.getElementById('expanded-title').textContent = ctx.label;
  document.getElementById('expanded-body').innerHTML = content
    ? marked.parse(content)
    : '<p style="color:var(--ink-muted);font-style:italic">No content.</p>';

  const panel = document.getElementById('expanded-panel');
  panel.classList.add('active');
  setTimeout(() => panel.scrollIntoView({ behavior: 'smooth', block: 'start' }), 50);
}

// ── Project grid ──────────────────────────────
function renderProjectGrid(projects) {
  const grid = document.getElementById('file-grid');

  if (projects.length === 0) {
    grid.innerHTML = '<div class="empty-state">No projects in this section.</div>';
    return;
  }

  const numCols = Math.min(3, Math.ceil(projects.length / 2));
  const cols = Array.from({ length: numCols }, () => []);
  projects.forEach((p, i) => cols[i % numCols].push(p));

  const sectionLabel = activeSection === 'all' ? 'Projects' : sectionFor(activeSection).label;
  grid.innerHTML = cols.map((col, ci) => `
    <div class="file-column">
      <div class="file-header">
        <span class="col-title">${sectionLabel}</span>
        ${ci === 0 ? `<span class="col-badge">${projects.length}</span>` : ''}
      </div>
      ${col.map((p, pi) => {
        const firstSpec = p.specs?.[0];
        const isFeatured = pi === 0;
        const fileCount = p.specs?.length ?? 0;
        const cat = categorise(p.id);
        return `
          <div class="file-item${isFeatured ? ' featured' : ''}" data-id="${p.id}">
            <div class="file-item-title">${p.name}</div>
            ${firstSpec ? `<div class="file-item-teaser">${teaser(firstSpec.content || '')}</div>` : ''}
            <div class="file-item-meta">
              <span>${fileCount} file${fileCount !== 1 ? 's' : ''}</span>
              <span class="file-item-meta-sep"></span>
              <span>${cat}</span>
            </div>
          </div>`;
      }).join('')}
    </div>
  `).join('');

  grid.querySelectorAll('.file-item').forEach(item => {
    item.addEventListener('click', () => selectProject(item.dataset.id));
  });
}

// ── Project & file open ───────────────────────
async function selectProject(id) {
  document.querySelectorAll('.file-item').forEach(el =>
    el.classList.toggle('active', el.dataset.id === id)
  );

  const cached = allProjects.find(p => p.id === id);
  const res = await fetch(`${API}/projects/${id}`);
  activeProject = await res.json();
  activeFile = activeProject.specs?.[0]?.filename ?? null;

  openFileInExpanded(activeFile);
}

function openFileInExpanded(filename) {
  if (!activeProject || !filename) return;
  const spec = activeProject.specs.find(s => s.filename === filename);
  if (!spec) return;

  activeFile = filename;

  document.getElementById('expanded-project').textContent = activeProject.name;
  document.getElementById('expanded-file').textContent = filename;
  document.getElementById('expanded-title').textContent = spec.label;
  document.getElementById('expanded-body').innerHTML = spec.content
    ? marked.parse(spec.content)
    : '<p style="color:var(--ink-muted);font-style:italic">No content.</p>';

  // Render file tabs in sidebar
  const tabsEl = document.getElementById('expanded-tabs');
  if (tabsEl) {
    tabsEl.innerHTML = activeProject.specs.map(s => `
      <button class="tab-btn${s.filename === filename ? ' active' : ''}" data-file="${s.filename}">${s.label}</button>
    `).join('');
    tabsEl.querySelectorAll('.tab-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        tabsEl.querySelectorAll('.tab-btn').forEach(b => b.classList.toggle('active', b.dataset.file === btn.dataset.file));
        openFileInExpanded(btn.dataset.file);
      });
    });
  }

  const panel = document.getElementById('expanded-panel');
  if (!panel.classList.contains('active')) {
    panel.classList.add('active');
    setTimeout(() => panel.scrollIntoView({ behavior: 'smooth', block: 'start' }), 50);
  }
}

function closeExpanded() {
  document.getElementById('expanded-panel').classList.remove('active');
  document.querySelectorAll('.file-item').forEach(el => el.classList.remove('active'));
  activeProject = null;
  activeFile = null;
}

document.getElementById('expanded-close').addEventListener('click', () => {
  closeExpanded();
  document.getElementById('file-grid').scrollIntoView({ behavior: 'smooth', block: 'start' });
});

init();
