const API = '/api';
let activeProject = null;
let activeFile = null;

const folderIcon = `<svg viewBox="0 0 24 24"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/></svg>`;
const fileIcon   = `<svg viewBox="0 0 24 24"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>`;

async function init() {
  const res = await fetch(`${API}/projects`);
  const projects = await res.json();
  renderSidebar(projects);
}

function renderSidebar(projects) {
  const list = document.getElementById('project-list');
  list.innerHTML = projects.map(p => `
    <button class="nav-item" data-id="${p.id}">
      <span class="nav-item__icon">${folderIcon}</span>
      <span class="nav-item__text">${p.name}</span>
    </button>
  `).join('');
  list.querySelectorAll('.nav-item').forEach(btn => {
    btn.addEventListener('click', () => selectProject(btn.dataset.id, btn));
  });
}

async function selectProject(id, btn) {
  document.querySelectorAll('.nav-item').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');

  // breadcrumb
  document.getElementById('breadcrumb-sep').style.display = '';
  document.getElementById('breadcrumb-project').textContent = btn.querySelector('.nav-item__text').textContent;

  // loading state
  document.getElementById('content').innerHTML = `
    <div style="display:grid;gap:12px;max-width:780px">
      ${[80,60,90,50,70].map(w => `<div class="skeleton" style="height:14px;width:${w}%"></div>`).join('')}
    </div>`;

  const res = await fetch(`${API}/projects/${id}`);
  activeProject = await res.json();
  activeFile = activeProject.specs?.[0]?.filename ?? null;

  renderTabs();
  renderContent();
}

function renderTabs() {
  const tabs = document.getElementById('file-tabs');
  tabs.innerHTML = activeProject.specs.map(s => `
    <button class="tab-btn${s.filename === activeFile ? ' active' : ''}" data-file="${s.filename}">
      ${s.label}
    </button>
  `).join('');
  tabs.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      activeFile = btn.dataset.file;
      tabs.querySelectorAll('.tab-btn').forEach(b => b.classList.toggle('active', b.dataset.file === activeFile));
      renderContent();
    });
  });
}

function renderContent() {
  const content = document.getElementById('content');
  const spec = activeProject.specs.find(s => s.filename === activeFile);
  if (!spec?.content?.trim()) {
    content.innerHTML = '<div class="empty-state">No content</div>';
    return;
  }
  content.innerHTML = `<div class="md">${marked.parse(spec.content)}</div>`;
  content.scrollTop = 0;
}

init();
