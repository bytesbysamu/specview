import { Component, OnInit, OnDestroy, signal, computed, inject, effect } from '@angular/core';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';
import { marked } from 'marked';

import { AuthService } from './services/auth.service';
import { ProjectsService, Project, Spec } from './services/projects.service';
import { AiService } from './services/ai.service';
import { LoginComponent } from './components/login/login.component';

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

  private pollTimer: ReturnType<typeof setInterval> | null = null;

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
    const result = this.aiResult();
    const spec = this.currentSpec();
    const ctx = this.contextContent();
    const content = result ?? spec?.content ?? ctx ?? '';
    if (!content) return '';
    return this.sanitizer.bypassSecurityTrustHtml(marked.parse(content) as string);
  });

  parsedOriginal = computed((): SafeHtml => {
    const content = this.currentSpec()?.content ?? '';
    if (!content) return '';
    return this.sanitizer.bypassSecurityTrustHtml(marked.parse(content) as string);
  });

  sectionLabel = computed(() => SECTIONS.find(s => s.id === this.activeSection())?.label ?? 'Projects');

  showGrid = computed(() => !this.activeProject() && this.contextContent() === null);
  showExpanded = computed(() => !!this.activeProject() || this.contextContent() !== null);
  expandedTitle = computed(() => this.contextContent() !== null ? this.contextTitle() : (this.currentSpec()?.label ?? ''));
  expandedProject = computed(() => this.contextContent() !== null ? 'Context' : (this.activeProject()?.name ?? ''));

  constructor() {
    // Reload projects immediately whenever the user becomes logged in
    // (covers both: app start with stored JWT and post-login transition).
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
  }

  // ── Lifecycle ─────────────────────────────────────
  ngOnInit() {
    const saved = localStorage.getItem('theme') || 'light';
    this.isDark.set(saved === 'dark');
    if (saved === 'dark') document.documentElement.setAttribute('data-theme', 'dark');
  }

  ngOnDestroy() {
    if (this.pollTimer) { clearInterval(this.pollTimer); this.pollTimer = null; }
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
    try {
      const fresh = await this.projectsSvc.listProjects();
      if (fresh.length !== this.knownCount) {
        const diff = fresh.length - this.knownCount;
        this.projects.set(fresh);
        this.knownCount = fresh.length;
        this.updateBanner.set(diff > 0 ? `+${diff} new` : 'Projects updated');
        setTimeout(() => this.updateBanner.set(''), 5000);
      }
    } catch { /* ignore */ }
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
    if (op !== 'rewrite') {
      this.runOp(op as 'expand' | 'compress' | 'clarify');
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

  runOp(op: 'expand' | 'compress' | 'clarify') {
    const spec = this.currentSpec();
    if (!spec?.content) return;
    this._runAi(() => this.aiSvc[op](spec.content!));
  }

  runRewrite(instructions: string) {
    const spec = this.currentSpec();
    if (!spec?.content || !instructions.trim()) return;
    this._runAi(() => this.aiSvc.rewrite(spec.content!, instructions));
  }

  dismissResult() {
    this.aiResult.set(null);
    this.aiLatencyMs.set(null);
    this.aiError.set(false);
    this.activeOp.set(null);
  }

  async copyResult() {
    const result = this.aiResult();
    if (!result) return;
    await navigator.clipboard.writeText(result);
    this.copied.set(true);
    setTimeout(() => this.copied.set(false), 2000);
  }

  // ── Helpers (used in template) ────────────────────
  teaser = teaser;
  categorise = categorise;
}
