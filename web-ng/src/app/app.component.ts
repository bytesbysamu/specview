import { Component, OnInit, OnDestroy, signal, computed, inject, effect } from '@angular/core';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';
import { marked } from 'marked';

import { AuthService } from './services/auth.service';
import { ProjectsService, Project, Spec, GeneratedFile } from './services/projects.service';
import { AiService } from './services/ai.service';
import { LoginComponent } from './components/login/login.component';

interface ParagraphDiff {
  type: 'keep' | 'add' | 'remove';
  text: string;
}

function computeParagraphDiff(original: string, result: string): ParagraphDiff[] {
  const a = original.split(/\n{2,}/).map(s => s.trim()).filter(Boolean);
  const b = result.split(/\n{2,}/).map(s => s.trim()).filter(Boolean);
  const m = a.length, n = b.length;

  const dp: number[][] = Array.from({ length: m + 1 }, () => new Array(n + 1).fill(0));
  for (let i = m - 1; i >= 0; i--) {
    for (let j = n - 1; j >= 0; j--) {
      dp[i][j] = a[i] === b[j] ? 1 + dp[i+1][j+1] : Math.max(dp[i+1][j], dp[i][j+1]);
    }
  }

  const diffs: ParagraphDiff[] = [];
  let i = 0, j = 0;
  while (i < m || j < n) {
    if (i < m && j < n && a[i] === b[j]) {
      diffs.push({ type: 'keep', text: a[i++] }); j++;
    } else if (i < m && (j >= n || dp[i+1][j] >= dp[i][j+1])) {
      diffs.push({ type: 'remove', text: a[i++] });
    } else {
      diffs.push({ type: 'add', text: b[j++] });
    }
  }
  return diffs;
}

function escHtml(s: string): string {
  return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

const SECTIONS = [
  { id: 'context',      label: 'Context',       icon: '📐' },
  { id: 'all',          label: 'All',            icon: '' },
  { id: 'products',     label: 'Products',       icon: '🚀' },
  { id: 'platform',     label: 'Platform',       icon: '⚙️' },
  { id: 'braindumps',   label: 'Braindumps',     icon: '🧠' },
  { id: 'engineering',  label: 'Engineering',    icon: '🔧' },
  { id: 'devex',        label: 'Dev Experience', icon: '🛠' },
  { id: 'distribution', label: 'Distribution',   icon: '📣' },
  { id: 'status',       label: 'Status',         icon: '📊' },
  { id: 'misc',         label: 'Misc',           icon: '📁' },
];

const CONTEXT_FILES = [
  { key: 'builder',    label: 'Builder',    desc: 'How to build with spec-doc' },
  { key: 'principles', label: 'Principles', desc: 'Core development principles' },
  { key: 'codebase',   label: 'Codebase',   desc: 'Codebase overview & conventions' },
  { key: 'references', label: 'References', desc: 'External references & links' },
  { key: 'quality',    label: 'Quality',    desc: 'Quality rules & linting' },
  { key: 'versions',   label: 'Versions',   desc: 'Deployment fact sheet' },
];

const REFRESH_INTERVAL = 30_000;
const GEN_POLL_INTERVAL = 10_000;

function categorise(id: string): string {
  const s = id.toLowerCase();
  if (/braindump/.test(s) || /phase\d+-.*braindump/.test(s)) return 'braindumps';
  if (/^(bubls|trendfy|howdays|relateai|babyname|photoshoot|wardrobai|tennispartner|relationship|specdocv2|michi|portfolio|cold-dm-templates|voice|twitter-bio|linkedin|reddit|the-post|landing-copy|waitlist|github-readme)/.test(s)) return 'products';
  if (/^(saas|v2-spec-doc|spec-doc-flask|spec-doc-api|spec-doc-self|aligning-spec-doc|deployment-stack|saas-feature|saas-port|spec-doc-improvements|status-|run-2026)/.test(s)) return 'platform';
  if (/^(chain|workflow|pipeline|bootstrap|batch|text-chains|two-separate|parallel|iteration|generate-next|run-chain|raise-max|runtime-cancel|retry-recovery)/.test(s)) return 'engineering';
  if (/^(dev-experience|e2e|test-|gherkin|codebase-cleanup|architecture-cleanup|apply-button|integration-test|express-retirement|modular-restructure|directory-listing|port-)/.test(s)) return 'devex';
  if (/^(landing-page|distribution-experiment|the-post|waitlist|linkedin-update|twitter|reddit-post|cold-dm|voice-demo|voice-input|github-readme)/.test(s)) return 'distribution';
  if (/^(status|phase2-|phase3-|phase4-|phase5-|saas-feature-roadmap|saas-port-roadmap|spec-doc-improvements|run-2026)/.test(s)) return 'status';
  return 'misc';
}

function stripMarkdown(md = ''): string {
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

function teaser(content = '', len = 140): string {
  const plain = stripMarkdown(content);
  return plain.length > len ? plain.slice(0, len).trimEnd() + '…' : plain;
}

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [LoginComponent],
  templateUrl: './app.component.html',
})
export class AppComponent implements OnInit, OnDestroy {
  private sanitizer = inject(DomSanitizer);
  private projectsSvc = inject(ProjectsService);
  private aiSvc = inject(AiService);
  auth = inject(AuthService);

  readonly sections = SECTIONS;
  readonly contextFiles = CONTEXT_FILES;

  // ── State ────────────────────────────────────────
  projects = signal<Project[]>([]);
  activeSection = signal('all');
  activeProject = signal<Project | null>(null);
  activeFile = signal<string | null>(null);
  searchQuery = signal('');
  isDark = signal(false);
  today = new Date().toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });
  updateBanner = signal('');
  knownCount = 0;

  // AI text ops state
  aiLoading = signal(false);
  aiResult = signal<string | null>(null);
  aiLatencyMs = signal<number | null>(null);
  aiError = signal(false);
  activeOp = signal<string | null>(null); // which chip is open/active
  copied = signal(false);

  // Context viewer
  contextContent = signal<string | null>(null);
  contextTitle = signal('');

  // New project / spec-gen
  showCreateModal = signal(false);
  specGenLoading = signal(false);
  specGenError = signal<string | null>(null);
  specGenStep = signal<string | null>(null);
  specGenProjectName = signal<string | null>(null);

  // Epic guide generation
  epicGuideLoading = signal(false);
  epicGuideError = signal<string | null>(null);


  toolbarFloating = signal(false);
  polling = signal(false);
  pollOk = signal(true);
  private pollTimer: ReturnType<typeof setInterval> | null = null;
  private genPollTimer: ReturnType<typeof setInterval> | null = null;

  // ── Computed ──────────────────────────────────────
  sectionCounts = computed(() => {
    const counts: Record<string, number> = {};
    this.projects().forEach(p => {
      const cat = categorise(p.id);
      counts[cat] = (counts[cat] || 0) + 1;
      counts['all'] = (counts['all'] || 0) + 1;
    });
    return counts;
  });

  filteredProjects = computed(() => {
    const section = this.activeSection();
    let list = section === 'all' ? this.projects() : this.projects().filter(p => categorise(p.id) === section);
    const q = this.searchQuery().toLowerCase();
    if (q) list = list.filter(p => p.name.toLowerCase().includes(q) || p.id.toLowerCase().includes(q));
    return list;
  });

  columns = computed(() => {
    const projects = this.filteredProjects();
    const numCols = Math.min(3, Math.ceil(projects.length / 2)) || 1;
    const cols: Project[][] = Array.from({ length: numCols }, () => []);
    projects.forEach((p, i) => cols[i % numCols].push(p));
    return cols;
  });

  currentSpec = computed((): Spec | null => {
    const proj = this.activeProject();
    const file = this.activeFile();
    if (!proj || !file) return null;
    return proj.specs.find(s => s.filename === file) ?? null;
  });

  parsedContent = computed((): SafeHtml => {
    const spec = this.currentSpec();
    const ctx = this.contextContent();
    const content = spec?.content ?? ctx ?? '';
    if (!content) return '';
    return this.sanitizer.bypassSecurityTrustHtml(marked.parse(content) as string);
  });

  // Undo / redo stacks keyed by "projectId/filename"
  undoStack = signal<Record<string, string[]>>({});
  redoStack = signal<Record<string, string[]>>({});

  // Brainstorm follow-up
  brainstormQuestion = signal('');

  // Paragraph-level diff rendered as markdown HTML (single unified column)
  diffHtmlUnified = computed((): SafeHtml => {
    const result = this.aiResult();
    const original = this.currentSpec()?.content ?? '';
    if (!result) return '';
    const diffs = computeParagraphDiff(original, result);
    const parts = diffs.map(d => {
      const rendered = marked.parse(d.text) as string;
      if (d.type === 'remove') return `<div class="diff-block-remove">${rendered}</div>`;
      if (d.type === 'add')    return `<div class="diff-block-add">${rendered}</div>`;
      return rendered;
    });
    return this.sanitizer.bypassSecurityTrustHtml(parts.join(''));
  });

  // For brainstorm and TL;DR — render result as plain markdown (no diff)
  parsedAiResult = computed((): SafeHtml => {
    const result = this.aiResult();
    if (!result) return '';
    return this.sanitizer.bypassSecurityTrustHtml(marked.parse(result) as string);
  });

  // True for ops where diff view doesn't make sense (brainstorm is additive)
  isAdditivOp = computed(() => ['brainstorm', 'tldr'].includes(this.activeOp() ?? ''));

  aiOpLabel = computed(() => {
    const labels: Record<string, string> = {
      expand: 'Expanding', compress: 'Compressing', clarify: 'Clarifying',
      simplify: 'Simplifying', tldr: 'Generating TL;DR', bullets: 'Converting to bullets',
      brainstorm: 'Brainstorming', style: 'Restyling',
    };
    return labels[this.activeOp() ?? ''] ?? 'Processing';
  });

  canRevert = computed(() => {
    const proj = this.activeProject();
    const file = this.activeFile();
    if (!proj || !file) return false;
    return (this.undoStack()[`${proj.id}/${file}`]?.length ?? 0) > 0;
  });

  canRedo = computed(() => {
    const proj = this.activeProject();
    const file = this.activeFile();
    if (!proj || !file) return false;
    return (this.redoStack()[`${proj.id}/${file}`]?.length ?? 0) > 0;
  });

  sectionLabel = computed(() => SECTIONS.find(s => s.id === this.activeSection())?.label ?? 'Projects');

  // True when project has no generated analysis yet (braindump.md not required)
  canGenerateSpecs = computed(() => {
    const proj = this.activeProject();
    if (!proj) return false;
    return !proj.specs.some(s => s.filename === 'analysis.md');
  });

  // True when project has an epic but no implementation-guide yet
  canGenerateEpicGuide = computed(() => {
    const proj = this.activeProject();
    if (!proj) return false;
    return proj.specs.some(s => s.filename === 'epic.md');
  });


  showGrid = computed(() => !this.activeProject() && this.contextContent() === null);
  showExpanded = computed(() => !!this.activeProject() || this.contextContent() !== null);
  expandedTitle = computed(() => this.contextContent() !== null ? this.contextTitle() : (this.currentSpec()?.label ?? ''));
  expandedProject = computed(() => this.contextContent() !== null ? 'Context' : (this.activeProject()?.name ?? ''));

  constructor() {
    // Reload projects immediately whenever the user becomes logged in
    effect(() => {
      if (this.auth.isLoggedIn()) {
        this.loadProjects().then(() => {
          if (!this.pollTimer) {
            this.pollTimer = setInterval(() => this.checkForUpdates(), REFRESH_INTERVAL);
          }
        });
      } else {
        if (this.pollTimer) { clearInterval(this.pollTimer); this.pollTimer = null; }
      }
    });

    // Toolbar is always fixed at bottom when a project file is open
    effect(() => {
      this.toolbarFloating.set(!!(this.activeProject() && this.currentSpec()));
    });
  }

  // ── Lifecycle ─────────────────────────────────────
  ngOnInit() {
    const saved = localStorage.getItem('theme') || 'light';
    this.isDark.set(saved === 'dark');
    if (saved === 'dark') document.documentElement.setAttribute('data-theme', 'dark');
  }

  ngOnDestroy() {
    if (this.pollTimer) { clearInterval(this.pollTimer); this.pollTimer = null; }
    this._stopGenPoll();
  }

  private _startGenPoll() {
    if (this.genPollTimer) return;
    this.genPollTimer = setInterval(() => this.checkForUpdates(), GEN_POLL_INTERVAL);
  }

  private _stopGenPoll() {
    if (this.genPollTimer) { clearInterval(this.genPollTimer); this.genPollTimer = null; }
  }

  // ── Theme ─────────────────────────────────────────
  toggleTheme() {
    const next = this.isDark() ? 'light' : 'dark';
    this.isDark.set(next === 'dark');
    document.documentElement.setAttribute('data-theme', next);
    localStorage.setItem('theme', next);
  }

  // ── Projects ──────────────────────────────────────
  async loadProjects() {
    try {
      const list = await this.projectsSvc.listProjects();
      this.projects.set(list);
      this.knownCount = list.length;
    } catch { /* 401 handled by interceptor */ }
  }

  async checkForUpdates() {
    this.polling.set(true);
    try {
      const fresh = await this.projectsSvc.listProjects();
      this.pollOk.set(true);
      if (fresh.length !== this.knownCount) {
        const diff = fresh.length - this.knownCount;
        this.projects.set(fresh);
        this.knownCount = fresh.length;
        this.updateBanner.set(diff > 0 ? `+${diff} new` : 'Projects updated');
        setTimeout(() => this.updateBanner.set(''), 5000);
      }
    } catch {
      this.pollOk.set(false);
    } finally {
      setTimeout(() => this.polling.set(false), 700);
    }
  }

  // ── Search ────────────────────────────────────────
  onSearch(value: string) {
    this.searchQuery.set(value);
  }

  // ── Nav ───────────────────────────────────────────
  selectSection(id: string) {
    this.activeSection.set(id);
    this.searchQuery.set('');
    this.closeExpanded();
  }

  // ── Project grid ──────────────────────────────────
  async selectProject(id: string) {
    const proj = await this.projectsSvc.getProject(id);
    this.activeProject.set(proj);
    this.activeFile.set(proj.specs?.[0]?.filename ?? null);
    this.contextContent.set(null);
    this.aiResult.set(null);
    
  }

  closeExpanded() {
    this.activeProject.set(null);
    this.activeFile.set(null);
    this.contextContent.set(null);
    this.aiResult.set(null);
    
  }

  selectFile(filename: string) {
    this.activeFile.set(filename);
    this.aiResult.set(null);
    this.activeOp.set(null);
    this.aiError.set(false);
  }

  // ── Context files ─────────────────────────────────
  async openContext(key: string) {
    const ctx = CONTEXT_FILES.find(f => f.key === key);
    const data = await this.projectsSvc.getContext(key);
    this.contextContent.set(data.content || data.text || '');
    this.contextTitle.set(ctx?.label ?? key);
    this.activeProject.set(null);
    this.activeFile.set(null);
    this.aiResult.set(null);
    
  }

  // Brainstorm available on any file
  isBraindump = computed(() => !!this.currentSpec());

  readonly STYLE_PRESETS = ['Concise', 'Technical', 'Executive', 'Narrative', 'Punchy'];

  // ── AI text ops ───────────────────────────────────
  toggleOp(op: string) {
    if (this.activeOp() === op) {
      this.activeOp.set(null);
      this.aiResult.set(null);
      this.aiError.set(false);
      return;
    }
    this.activeOp.set(op);
    this.aiResult.set(null);
    this.aiError.set(false);
    // 'style' shows preset chips (no immediate call); 'rewrite' kept as alias for style
    const immediateOps = ['expand', 'compress', 'clarify', 'simplify', 'tldr', 'bullets', 'brainstorm'];
    if (immediateOps.includes(op)) {
      this.runOp(op as any);
    }
  }

  private async _runAi(fn: () => Promise<{ text: string; latencyMs: number }>) {
    if (this.aiLoading()) return;
    this.aiLoading.set(true);
    this.aiResult.set(null);
    this.aiLatencyMs.set(null);
    this.aiError.set(false);
    try {
      const res = await fn();
      this.aiResult.set(res.text);
      this.aiLatencyMs.set(res.latencyMs);
    } catch {
      this.aiError.set(true);
    } finally {
      this.aiLoading.set(false);
    }
  }

  runOp(op: 'expand' | 'compress' | 'clarify' | 'simplify' | 'tldr' | 'bullets' | 'brainstorm') {
    const spec = this.currentSpec();
    if (!spec?.content) return;
    this._runAi(() => this.aiSvc[op](spec.content!));
  }

  runStyle(style: string) {
    const spec = this.currentSpec();
    if (!spec?.content) return;
    this._runAi(() => this.aiSvc.styleAs(spec.content!, style));
  }

  followupBrainstorm(question: string) {
    const spec = this.currentSpec();
    const currentResult = this.aiResult();
    if (!question.trim()) return;
    const context = currentResult
      ? `${spec?.content ?? ''}\n\n---\nPrevious brainstorm:\n${currentResult}`
      : undefined;
    this.brainstormQuestion.set('');
    this._runAi(() => this.aiSvc.brainstorm(spec?.content ?? '', question, context));
  }

  async generateFromBrainstormResult() {
    const proj = this.activeProject();
    const result = this.aiResult();
    const spec = this.currentSpec();
    if (!proj || !result || !spec) return;

    // Use brainstorm result + original braindump as the combined context for spec gen
    const enrichedBraindump = `${spec.content ?? ''}\n\n---\n## Brainstorm Output\n\n${result}`;
    this.aiResult.set(null);
    this.specGenLoading.set(true);
    this.specGenError.set(null);
    this.specGenStep.set(null);
    this.specGenProjectName.set(proj.name);
    this._startGenPoll();
    try {
      const remainingFiles = await this._runBootstrap(proj.name, enrichedBraindump, async (file) => {
        await this.projectsSvc.saveFile(proj.id, file.filename, file.content);
        const refreshed = await this.projectsSvc.getProject(proj.id);
        this.activeProject.set(refreshed);
      });
      for (const file of remainingFiles) {
        await this.projectsSvc.saveFile(proj.id, file.filename, file.content);
      }
      const final = await this.projectsSvc.getProject(proj.id);
      this.activeProject.set(final);
      this.activeFile.set(final.specs.find(s => s.filename === 'analysis.md')?.filename ?? final.specs[0]?.filename ?? null);
    } catch (err: any) {
      this.specGenError.set(err?.message || 'Generation failed — check connection and try again.');
    } finally {
      this.specGenLoading.set(false);
      this.specGenStep.set(null);
      this.specGenProjectName.set(null);
      this._stopGenPoll();
    }
  }

  dismissResult() {
    this.aiResult.set(null);
    this.aiLatencyMs.set(null);
    this.aiError.set(false);
    this.activeOp.set(null);
  }

  applyResult() {
    const proj = this.activeProject();
    const file = this.activeFile();
    const result = this.aiResult();
    if (!proj || !file || !result) return;
    const spec = proj.specs.find(s => s.filename === file);
    if (!spec) return;

    const key = `${proj.id}/${file}`;

    // Push current to undo stack
    const undo = { ...this.undoStack() };
    undo[key] = [...(undo[key] ?? []), spec.content ?? ''];
    this.undoStack.set(undo);

    // Applying a new result always clears redo (new branch)
    const redo = { ...this.redoStack() };
    redo[key] = [];
    this.redoStack.set(redo);

    // Update spec in the project signal
    const updatedSpecs = proj.specs.map(s =>
      s.filename === file ? { ...s, content: result } : s
    );
    this.activeProject.set({ ...proj, specs: updatedSpecs });

    this.aiResult.set(null);
    this.activeOp.set(null);
    this.aiLatencyMs.set(null);

    this.projectsSvc.saveFile(proj.id, file, result).catch(() => {});
  }

  undoVersion() {
    const proj = this.activeProject();
    const file = this.activeFile();
    if (!proj || !file) return;
    const key = `${proj.id}/${file}`;

    const undoCurrent = { ...this.undoStack() };
    const undoEntries = undoCurrent[key] ?? [];
    if (!undoEntries.length) return;

    const previous = undoEntries[undoEntries.length - 1];
    undoCurrent[key] = undoEntries.slice(0, -1);
    this.undoStack.set(undoCurrent);

    // Save current content onto redo stack
    const currentContent = proj.specs.find(s => s.filename === file)?.content ?? '';
    const redoCurrent = { ...this.redoStack() };
    redoCurrent[key] = [...(redoCurrent[key] ?? []), currentContent];
    this.redoStack.set(redoCurrent);

    const updatedSpecs = proj.specs.map(s =>
      s.filename === file ? { ...s, content: previous } : s
    );
    this.activeProject.set({ ...proj, specs: updatedSpecs });
    this.projectsSvc.saveFile(proj.id, file, previous).catch(() => {});
  }

  redoVersion() {
    const proj = this.activeProject();
    const file = this.activeFile();
    if (!proj || !file) return;
    const key = `${proj.id}/${file}`;

    const redoCurrent = { ...this.redoStack() };
    const redoEntries = redoCurrent[key] ?? [];
    if (!redoEntries.length) return;

    const next = redoEntries[redoEntries.length - 1];
    redoCurrent[key] = redoEntries.slice(0, -1);
    this.redoStack.set(redoCurrent);

    // Save current content onto undo stack
    const currentContent = proj.specs.find(s => s.filename === file)?.content ?? '';
    const undoCurrent = { ...this.undoStack() };
    undoCurrent[key] = [...(undoCurrent[key] ?? []), currentContent];
    this.undoStack.set(undoCurrent);

    const updatedSpecs = proj.specs.map(s =>
      s.filename === file ? { ...s, content: next } : s
    );
    this.activeProject.set({ ...proj, specs: updatedSpecs });
    this.projectsSvc.saveFile(proj.id, file, next).catch(() => {});
  }

  async copyResult() {
    const result = this.aiResult();
    if (!result) return;
    await navigator.clipboard.writeText(result);
    this.copied.set(true);
    setTimeout(() => this.copied.set(false), 2000);
  }

  // ── New project / spec-gen ────────────────────────
  private async _runBootstrap(
    projectName: string,
    braindump: string,
    onFile?: (file: GeneratedFile) => Promise<void>,
  ): Promise<GeneratedFile[]> {
    const { job_id } = await this.projectsSvc.startBootstrap(projectName, braindump);
    const saved = new Set<string>();
    let pollFailures = 0;
    const MAX_POLL_FAILURES = 5;

    while (true) {
      await new Promise(r => setTimeout(r, 2500));

      let status: Awaited<ReturnType<typeof this.projectsSvc.pollBootstrap>>;
      try {
        status = await this.projectsSvc.pollBootstrap(job_id);
        pollFailures = 0; // reset on success
      } catch {
        pollFailures++;
        if (pollFailures >= MAX_POLL_FAILURES) {
          throw new Error('Lost connection to server after multiple retries.');
        }
        continue; // retry poll
      }

      if (status.current_step) this.specGenStep.set(status.current_step);

      // Save incremental files as each AI step completes
      if (onFile && status.partial_files) {
        for (const file of status.partial_files) {
          if (!saved.has(file.filename)) {
            saved.add(file.filename);
            await onFile(file);
          }
        }
      }

      if (status.done) {
        if (status.error) throw new Error(status.error);
        // Return only files not already saved incrementally
        return (status.files ?? []).filter(f => !saved.has(f.filename));
      }
    }
  }

  openCreateModal() {
    this.showCreateModal.set(true);
    this.specGenError.set(null);
  }

  closeCreateModal() {
    this.showCreateModal.set(false);
    this.specGenError.set(null);
  }

  async createProject(nameEl: HTMLInputElement, braindumpEl: HTMLTextAreaElement) {
    const name = nameEl.value.trim();
    const braindump = braindumpEl.value.trim();
    if (!name || !braindump || this.specGenLoading()) return;

    // Close modal immediately — show fixed status bar
    this.showCreateModal.set(false);
    this.specGenLoading.set(true);
    this.specGenError.set(null);
    this.specGenStep.set(null);
    this.specGenProjectName.set(name);
    nameEl.value = '';
    braindumpEl.value = '';
    this._startGenPoll();

    try {
      // Create project immediately with just the braindump — navigate to it right away
      const project = await this.projectsSvc.createProject(name, [
        { filename: 'braindump.md', content: braindump },
      ]);
      await this.loadProjects();
      await this.selectProject(project.id);

      // Generate specs, saving each file to disk as soon as its AI step completes
      const remainingFiles = await this._runBootstrap(name, braindump, async (file) => {
        await this.projectsSvc.saveFile(project.id, file.filename, file.content);
        const refreshed = await this.projectsSvc.getProject(project.id);
        this.activeProject.set(refreshed);
      });

      // Save remaining files (spec-index, timeline, README — generated at completion)
      for (const file of remainingFiles) {
        await this.projectsSvc.saveFile(project.id, file.filename, file.content);
      }

      // Final refresh and navigate to analysis.md
      const final = await this.projectsSvc.getProject(project.id);
      this.activeProject.set(final);
      this.activeFile.set(final.specs.find(s => s.filename === 'analysis.md')?.filename ?? final.specs[0]?.filename ?? null);
    } catch (err: any) {
      this.specGenError.set(err?.message || 'Generation failed — check connection and try again.');
    } finally {
      this.specGenLoading.set(false);
      this.specGenStep.set(null);
      this.specGenProjectName.set(null);
      this._stopGenPoll();
    }
  }

  async generateFromBraindump() {
    const proj = this.activeProject();
    if (!proj || this.specGenLoading()) return;
    // Use braindump.md if present, otherwise active file, otherwise first spec
    const braindumpSpec =
      proj.specs.find(s => s.filename === 'braindump.md') ??
      this.currentSpec() ??
      proj.specs[0];
    if (!braindumpSpec?.content) return;

    this.specGenLoading.set(true);
    this.specGenError.set(null);
    this.specGenStep.set(null);
    this.specGenProjectName.set(proj.name);
    this._startGenPoll();
    try {
      const remainingFiles = await this._runBootstrap(proj.name, braindumpSpec.content, async (file) => {
        await this.projectsSvc.saveFile(proj.id, file.filename, file.content);
        const refreshed = await this.projectsSvc.getProject(proj.id);
        this.activeProject.set(refreshed);
      });
      for (const file of remainingFiles) {
        await this.projectsSvc.saveFile(proj.id, file.filename, file.content);
      }
      const final = await this.projectsSvc.getProject(proj.id);
      this.activeProject.set(final);
      this.activeFile.set(final.specs.find(s => s.filename === 'analysis.md')?.filename ?? final.specs[0]?.filename ?? null);
    } catch (err: any) {
      this.specGenError.set(err?.message || 'Generation failed — check connection and try again.');
    } finally {
      this.specGenLoading.set(false);
      this.specGenStep.set(null);
      this.specGenProjectName.set(null);
      this._stopGenPoll();
    }
  }

  async generateEpicGuide() {
    const proj = this.activeProject();
    if (!proj || this.epicGuideLoading()) return;

    this.epicGuideLoading.set(true);
    this.epicGuideError.set(null);
    try {
      await this.projectsSvc.startEpicGuide(proj.id);
      while (true) {
        await new Promise(r => setTimeout(r, 3000));
        const status = await this.projectsSvc.pollEpicGuide(proj.id);
        if (status.done) {
          if (status.error) throw new Error(status.error);
          const refreshed = await this.projectsSvc.getProject(proj.id);
          this.activeProject.set(refreshed);
          if (status.filename) this.activeFile.set(status.filename);
          break;
        }
      }
    } catch (err: any) {
      this.epicGuideError.set(err?.message || 'Guide generation failed.');
    } finally {
      this.epicGuideLoading.set(false);
    }
  }

  logout() {
    this.auth.signOut();
  }

  // ── Helpers (used in template) ────────────────────
  teaser = teaser;
  categorise = categorise;
}
