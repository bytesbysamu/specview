import { Component, OnInit, OnDestroy, signal, computed, inject, effect } from '@angular/core';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';
import { trigger, transition, style, animate, query, group } from '@angular/animations';
import { marked } from 'marked';
import DOMPurify from 'dompurify';

import { NavigationEnd, Router, RouterLink, RouterOutlet } from '@angular/router';
import { filter } from 'rxjs/operators';
import { AuthService } from './services/auth.service';
import { ProjectsService, Project, Spec, GeneratedFile, AccessDeniedError } from './services/projects.service';
import { DemoAwareProjectsService } from './services/demo-aware-projects.service';
import { AiService } from './services/ai.service';
import { Section, sectionFor, SECTION_ORDER } from './services/section-taxonomy.service';
import { projectTeaser, countTasks } from './services/project-teaser';
import { WordCountPipe } from './word-count.pipe';
import { UsageMeterComponent } from './components/usage-meter/usage-meter.component';
import { SubscriptionService } from './services/subscription.service';

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

const NAV_SECTIONS = [
  { id: 'context',        label: 'Context',        icon: 'ruler' },
  { id: 'all',            label: 'All',             icon: '' },
  { id: 'Active',         label: 'Active',          icon: 'zap' },
  { id: 'Ready to build', label: 'Ready to build',  icon: 'hammer' },
  { id: 'Specced',        label: 'Specced',         icon: 'check-circle' },
  { id: 'Braindumps',     label: 'Braindumps',      icon: 'brain' },
  { id: 'Archive',        label: 'Archive',         icon: 'archive' },
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




@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet, RouterLink, WordCountPipe, UsageMeterComponent],
  templateUrl: './app.component.html',
  animations: [
    trigger('panelEnter', [
      transition(':enter', [
        group([
          query('.expanded-sidebar', [
            style({ transform: 'translateX(-8px)', opacity: 0 }),
            animate('250ms ease-out', style({ transform: 'translateX(0)', opacity: 1 })),
          ], { optional: true }),
          query('.expanded-main', [
            style({ transform: 'translateY(8px)', opacity: 0 }),
            animate('250ms 40ms ease-out', style({ transform: 'translateY(0)', opacity: 1 })),
          ], { optional: true }),
        ]),
      ]),
      transition(':leave', [
        group([
          query('.expanded-sidebar', [
            animate('150ms ease-in', style({ transform: 'translateX(-8px)', opacity: 0 })),
          ], { optional: true }),
          query('.expanded-main', [
            animate('150ms ease-in', style({ transform: 'translateY(8px)', opacity: 0 })),
          ], { optional: true }),
        ]),
      ]),
    ]),
  ],
})
export class AppComponent implements OnInit, OnDestroy {
  private sanitizer = inject(DomSanitizer);
  private projectsSvc = inject(ProjectsService);
  private demoSvc = inject(DemoAwareProjectsService);
  private aiSvc = inject(AiService);
  auth = inject(AuthService);
  subscription = inject(SubscriptionService);
  private router = inject(Router);

  /** Whether the current route is a full-page route (only /playground). */
  isFullPageRoute = signal(false);

  private _routeSub = this.router.events.pipe(
    filter((e): e is NavigationEnd => e instanceof NavigationEnd)
  ).subscribe(e => {
    const path = e.urlAfterRedirects.split('?')[0];
    this.isFullPageRoute.set(['/playground', '/login', '/signup', '/demo', '/analyze'].some(r => path === r || path.startsWith(r + '/')));
  });

  readonly sections = NAV_SECTIONS;
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
  knownCount = signal(0);

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
  specGenJobId = signal<string | null>(null);
  specGenFailedStep = signal<string | null>(null);
  cancelling = signal(false);

  // Access denied (403) state
  accessDenied = signal(false);

  // Epic guide generation
  epicGuideLoading = signal(false);
  epicGuideError = signal<string | null>(null);

  // Share project
  shareUrl = signal<string | null>(null);
  shareCopied = signal(false);
  shareLoading = signal(false);

  // Login form
  showLoginForm = signal(false);
  loginLoading = signal(false);
  loginError = signal<string | null>(null);

  toolbarFloating = computed(() => !!(this.activeProject() && this.currentSpec()));
  polling = signal(false);
  pollOk = signal(true);
  pollingError = signal<string | null>(null);
  billingError = signal<string | null>(null);
  private pollTimer: ReturnType<typeof setInterval> | null = null;
  private genPollTimer: ReturnType<typeof setInterval> | null = null;
  private readonly POLL_MAX_RETRIES = 30;
  private readonly POLL_INTERVAL_MS = 2000;
  private pollRetries = 0;

  // Status bar: four-state mode
  lastSyncAt = signal<number | null>(null);
  lastSyncElapsed = signal<number>(0);
  statusMode = signal<'idle' | 'active' | 'success-flash' | 'failure'>('idle');
  statusFailureMsg = signal<string | null>(null);
  private _syncElapsedTimer: ReturnType<typeof setInterval> | null = null;
  private _successFlashTimer: ReturnType<typeof setTimeout> | null = null;

  // Generation timer
  specGenStartTime = signal<number | null>(null);
  specGenElapsed = signal<string>('0.0s');
  private _timerInterval: ReturnType<typeof setInterval> | null = null;

  // Per-file dot tracking: filename of the file currently targeted by an AI op
  activeOpFile = signal<string | null>(null);
  fileOpState = signal<Record<string, 'running' | 'success' | 'failure'>>({});

  // Pulse animation tracking for section count badges
  pulsingSections = signal<Set<string>>(new Set());
  private _prevSectionCounts: Record<string, number> = {};

  // ── Computed ──────────────────────────────────────

  /** True if spec-gen is actively running for a given project id. */
  private isActiveJob(projectId: string): boolean {
    return this.specGenLoading() && this.specGenProjectName() === projectId;
  }

  sectionCounts = computed(() => {
    const counts: Record<string, number> = {};
    this.projects().forEach(p => {
      const sec = sectionFor(p, this.isActiveJob(p.id));
      counts[sec] = (counts[sec] || 0) + 1;
      counts['all'] = (counts['all'] || 0) + 1;
    });
    return counts;
  });

  filteredProjects = computed(() => {
    const section = this.activeSection();
    let list = section === 'all'
      ? this.projects()
      : this.projects().filter(p => sectionFor(p, this.isActiveJob(p.id)) === section);
    const q = this.searchQuery().toLowerCase();
    if (q) list = list.filter(p => p.name.toLowerCase().includes(q) || p.id.toLowerCase().includes(q));
    return list;
  });

  /**
   * Projects grouped into the five taxonomy sections in canonical order,
   * filtered by the current search query.
   * Only sections with at least one project are included.
   */
  projectsBySection = computed((): { section: Section; projects: Project[] }[] => {
    const q = this.searchQuery().toLowerCase();
    let all = this.projects();
    if (q) all = all.filter(p => p.name.toLowerCase().includes(q) || p.id.toLowerCase().includes(q));

    const map = new Map<Section, Project[]>();
    for (const sec of SECTION_ORDER) map.set(sec, []);
    all.forEach(p => {
      const sec = sectionFor(p, this.isActiveJob(p.id));
      map.get(sec)!.push(p);
    });

    return SECTION_ORDER
      .map(sec => ({ section: sec, projects: map.get(sec)! }))
      .filter(g => g.projects.length > 0);
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
    return this.sanitizer.bypassSecurityTrustHtml(DOMPurify.sanitize(marked.parse(content) as string));
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
    return this.sanitizer.bypassSecurityTrustHtml(DOMPurify.sanitize(parts.join('')));
  });

  // For brainstorm and TL;DR — render result as plain markdown (no diff)
  parsedAiResult = computed((): SafeHtml => {
    const result = this.aiResult();
    if (!result) return '';
    return this.sanitizer.bypassSecurityTrustHtml(DOMPurify.sanitize(marked.parse(result) as string));
  });

  // True for ops where diff view doesn't make sense (brainstorm is additive)
  isAdditiveOp = computed(() => ['brainstorm', 'tldr'].includes(this.activeOp() ?? ''));

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

  sectionLabel = computed(() => NAV_SECTIONS.find(s => s.id === this.activeSection())?.label ?? 'Projects');

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


  showGrid = computed(() => !this.activeProject() && this.contextContent() === null && !this.accessDenied());
  showExpanded = computed(() => !!this.activeProject() || this.contextContent() !== null || this.accessDenied());
  expandedTitle = computed(() => this.contextContent() !== null ? this.contextTitle() : (this.currentSpec()?.label ?? ''));
  expandedProject = computed(() => this.contextContent() !== null ? 'Context' : (this.activeProject()?.name ?? ''));

  constructor() {
    // Set initial full-page route state
    const initialPath = this.router.url.split('?')[0];
    this.isFullPageRoute.set(['/playground', '/login', '/signup', '/demo', '/analyze'].some(r => initialPath === r || initialPath.startsWith(r + '/')));

    // Load projects on every auth state change (demo data when not logged in, real when logged in)
    effect(() => {
      const loggedIn = this.auth.isLoggedIn();
      this.loadProjects().then(() => {
        if (loggedIn && !this.pollTimer) {
          this.pollRetries = 0;
          this.pollTimer = setInterval(() => this.checkForUpdates(), REFRESH_INTERVAL);
        } else if (!loggedIn) {
          this.stopPolling();
        }
      });
    });

    // Pulse section count badges when their count changes
    effect(() => {
      const counts = this.sectionCounts();
      const prev = this._prevSectionCounts;
      const changed = Object.keys(counts).filter(sec => counts[sec] !== prev[sec]);
      if (changed.length > 0) {
        this.pulsingSections.set(new Set(changed));
        setTimeout(() => this.pulsingSections.set(new Set()), 250);
      }
      this._prevSectionCounts = { ...counts };
    }, { allowSignalWrites: true });
  }

  // ── Lifecycle ─────────────────────────────────────
  ngOnInit() {
    const saved = localStorage.getItem('theme') || 'light';
    this.isDark.set(saved === 'dark');
    if (saved === 'dark') document.documentElement.setAttribute('data-theme', 'dark');
  }

  ngOnDestroy() {
    this._routeSub.unsubscribe();
    this.stopPolling();
    this._stopGenPoll();
    this._stopSyncElapsedTimer();
    this._stopTimer();
    if (this._successFlashTimer) clearTimeout(this._successFlashTimer);
  }

  private stopPolling() {
    if (this.pollTimer) { clearInterval(this.pollTimer); this.pollTimer = null; }
  }

  private _startGenPoll() {
    if (this.genPollTimer) return;
    this.genPollTimer = setInterval(() => this.checkForUpdates(), GEN_POLL_INTERVAL);
  }

  private _stopGenPoll() {
    if (this.genPollTimer) { clearInterval(this.genPollTimer); this.genPollTimer = null; }
  }

  // ── Status bar transitions ────────────────────
  private _startSyncElapsedTimer() {
    if (this._syncElapsedTimer) return;
    this._syncElapsedTimer = setInterval(() => {
      const at = this.lastSyncAt();
      if (at !== null) {
        this.lastSyncElapsed.set(Math.floor((Date.now() - at) / 1000));
      }
    }, 1000);
  }

  private _stopSyncElapsedTimer() {
    if (this._syncElapsedTimer) { clearInterval(this._syncElapsedTimer); this._syncElapsedTimer = null; }
  }

  private _markSyncNow() {
    this.lastSyncAt.set(Date.now());
    this.lastSyncElapsed.set(0);
    this._startSyncElapsedTimer();
  }

  private _setStatusActive() {
    if (this._successFlashTimer) { clearTimeout(this._successFlashTimer); this._successFlashTimer = null; }
    this.statusMode.set('active');
    this._startTimer();
  }

  private _setStatusSuccess() {
    this._stopTimer();
    this.statusMode.set('success-flash');
    this._markSyncNow();
    if (this._successFlashTimer) clearTimeout(this._successFlashTimer);
    this._successFlashTimer = setTimeout(() => {
      this.statusMode.set('idle');
      this._successFlashTimer = null;
    }, 2000);
  }

  private _setStatusFailure(msg: string) {
    this.statusMode.set('failure');
    this.statusFailureMsg.set(msg);
    this._stopTimer();
  }

  private _startTimer() {
    this.specGenStartTime.set(Date.now());
    this._stopTimer();
    this._timerInterval = setInterval(() => {
      const start = this.specGenStartTime();
      if (start) {
        const elapsed = (Date.now() - start) / 1000;
        this.specGenElapsed.set(elapsed.toFixed(1) + 's');
      }
    }, 100);
  }

  private _stopTimer() {
    if (this._timerInterval) {
      clearInterval(this._timerInterval);
      this._timerInterval = null;
    }
  }

  retryLastOp() {
    if (this.specGenFailedStep()) {
      this.onRetry();
      return;
    }
    // No retryable step — just dismiss the error
    this.statusMode.set('idle');
    this.statusFailureMsg.set(null);
  }

  async onCancel() {
    const jobId = this.specGenJobId();
    if (!jobId || this.cancelling()) return;
    this.cancelling.set(true);
    try {
      await this.projectsSvc.cancelBootstrap(jobId);
    } catch { /* ignore — the poll loop will detect the cancelled state */ }
  }

  async onRetry() {
    const jobId = this.specGenJobId();
    const failedStep = this.specGenFailedStep();
    if (!jobId || !failedStep) return;
    try {
      const { job_id } = await this.projectsSvc.retryBootstrapStep(jobId, failedStep);
      this.specGenJobId.set(job_id);
      this.specGenFailedStep.set(null);
      this.specGenError.set(null);
      this.cancelling.set(false);
      this._setStatusActive();
    } catch (err: any) {
      const msg = err?.message || 'Retry failed — check connection and try again.';
      this.specGenError.set(msg);
      this._setStatusFailure(msg);
    }
  }

  // ── Per-file dot helpers ──────────────────────
  private _setFileRunning(filename: string | null) {
    this.activeOpFile.set(filename);
    if (filename) {
      const s = { ...this.fileOpState() };
      s[filename] = 'running';
      this.fileOpState.set(s);
    }
  }

  private _setFileSuccess(filename: string | null) {
    if (!filename) return;
    const s = { ...this.fileOpState() };
    s[filename] = 'success';
    this.fileOpState.set(s);
    setTimeout(() => {
      const cur = { ...this.fileOpState() };
      if (cur[filename] === 'success') {
        delete cur[filename];
        this.fileOpState.set(cur);
      }
    }, 1500);
  }

  private _setFileFailure(filename: string | null) {
    if (!filename) return;
    const s = { ...this.fileOpState() };
    s[filename] = 'failure';
    this.fileOpState.set(s);
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
      const list = await this.demoSvc.getProjects();
      this.projects.set(list);
      this.knownCount.set(list.length);
      this._markSyncNow();
    } catch { /* 401 handled by interceptor */ }
  }

  async checkForUpdates() {
    this.pollRetries++;
    if (this.pollRetries > this.POLL_MAX_RETRIES) {
      this.stopPolling();
      this.pollingError.set('Polling stopped after too many retries. Refresh to resume.');
      return;
    }
    this.polling.set(true);
    try {
      const fresh = await this.projectsSvc.listProjects();
      this.pollOk.set(true);
      this._markSyncNow();
      // Always update on count change, OR if projects is empty (initial load may have failed)
      if (fresh.length !== this.knownCount() || this.knownCount() === 0) {
        const diff = fresh.length - this.knownCount();
        this.projects.set(fresh);
        this.knownCount.set(fresh.length);
        if (diff > 0 && this.knownCount() > 0) {
          this.updateBanner.set(`+${diff} new`);
          setTimeout(() => this.updateBanner.set(''), 5000);
        }
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
    this.accessDenied.set(false);
    try {
      const proj = await this.demoSvc.getProject(id);
      this.activeProject.set(proj);
      this.activeFile.set(proj.specs?.[0]?.filename ?? null);
      this.contextContent.set(null);
      this.aiResult.set(null);
    } catch (err: any) {
      if (err instanceof AccessDeniedError) {
        this.accessDenied.set(true);
        // Keep expanded panel open so the access-denied block is visible
        this.activeProject.set(null);
        this.activeFile.set(null);
        this.contextContent.set(null);
      } else {
        throw err;
      }
    }
  }

  closeExpanded() {
    this.activeProject.set(null);
    this.activeFile.set(null);
    this.contextContent.set(null);
    this.aiResult.set(null);
    this.accessDenied.set(false);

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

  /**
   * Derives a display label from the active filename for the reader overline.
   * e.g. "architecture.md" → "ARCHITECTURE", "implementation-guide.md" → "IMPLEMENTATION GUIDE"
   * Returns null when no project file is open.
   */
  activeFileType = computed((): string | null => {
    const file = this.activeFile();
    if (!file || !this.activeProject()) return null;
    return file
      .replace(/\.md$/i, '')
      .replace(/-/g, ' ')
      .toUpperCase();
  });

  // True only when the open file is the braindump
  isBraindump = computed(() => {
    const spec = this.currentSpec();
    return spec !== null && spec.filename === 'braindump.md';
  });

  // Status bar four-state mode, derived from statusMode signal
  mode = computed(() => this.statusMode());

  // Idle "last sync" text
  lastSyncLabel = computed(() => {
    const elapsed = this.lastSyncElapsed();
    if (elapsed < 60) return `${elapsed}s ago`;
    return `${Math.floor(elapsed / 60)}m ago`;
  });

  // Active step display
  activeStepLabel = computed(() => {
    if (this.specGenLoading()) return this.specGenStep() ?? 'starting…';
    if (this.aiLoading()) return `${this.aiOpLabel()}…`;
    return '';
  });

  // Short job id for display
  activeJobId = computed(() => {
    const name = this.specGenProjectName();
    if (!name) return null;
    return name.slice(0, 8);
  });

  readonly STYLE_PRESETS = ['Concise', 'Technical', 'Executive', 'Narrative', 'Punchy'];

  // ── AI text ops ───────────────────────────────────
  toggleOp(op: 'expand' | 'compress' | 'clarify' | 'simplify' | 'tldr' | 'bullets' | 'brainstorm' | 'style') {
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
      this.runOp(op as 'expand' | 'compress' | 'clarify' | 'simplify' | 'tldr' | 'bullets' | 'brainstorm');
    }
  }

  private async _runAi(fn: () => Promise<{ text: string; latencyMs: number }>) {
    if (this.aiLoading()) return;
    const targetFile = this.activeFile();
    this.aiLoading.set(true);
    this.aiResult.set(null);
    this.aiLatencyMs.set(null);
    this.aiError.set(false);
    this.billingError.set(null);
    this._setStatusActive();
    this._setFileRunning(targetFile);
    try {
      const res = await fn();
      this.aiResult.set(res.text);
      this.aiLatencyMs.set(res.latencyMs);
      this._setStatusSuccess();
      this._setFileSuccess(targetFile);
    } catch (err: any) {
      if (err?.status === 429) {
        this.billingError.set('You have reached your daily limit. Upgrade to Pro to continue.');
        this._setStatusFailure('Daily limit reached — upgrade to continue.');
        this._setFileFailure(targetFile);
      } else if (!this.auth.isLoggedIn()) {
        this.aiError.set(true);
        this._setStatusFailure('Sign in to use AI features.');
        this._setFileFailure(targetFile);
      } else {
        this.aiError.set(true);
        this._setStatusFailure('Could not reach AI — check connection.');
        this._setFileFailure(targetFile);
      }
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
    this.specGenJobId.set(null);
    this.specGenFailedStep.set(null);
    this.cancelling.set(false);
    this._setStatusActive();
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
      this._setStatusSuccess();
    } catch (err: any) {
      const msg = err?.message || 'Generation failed — check connection and try again.';
      this.specGenError.set(msg);
      this._setStatusFailure(msg);
    } finally {
      this.specGenLoading.set(false);
      this.specGenStep.set(null);
      this.specGenProjectName.set(null);
      this.specGenJobId.set(null);
      this.cancelling.set(false);
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
    this.specGenJobId.set(job_id);
    const saved = new Set<string>();
    let pollFailures = 0;
    const MAX_POLL_FAILURES = 5;

    while (true) {
      await new Promise(r => setTimeout(r, 2500));

      let status: Awaited<ReturnType<typeof this.projectsSvc.pollBootstrap>>;
      try {
        status = await this.projectsSvc.pollBootstrap(this.specGenJobId()!);
        pollFailures = 0; // reset on success
      } catch {
        pollFailures++;
        if (pollFailures >= MAX_POLL_FAILURES) {
          throw new Error('Lost connection to server after multiple retries.');
        }
        continue; // retry poll
      }

      if (status.current_step) this.specGenStep.set(status.current_step);

      // Capture the failed step from the poll response (Task 4 field)
      if (status.failed_step !== undefined) {
        this.specGenFailedStep.set(status.failed_step ?? null);
      }

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
        if (status.status === 'CANCELLED') throw new Error('Generation cancelled');
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
    this.specGenJobId.set(null);
    this.specGenFailedStep.set(null);
    this.cancelling.set(false);
    nameEl.value = '';
    braindumpEl.value = '';
    this._setStatusActive();
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
      this._setStatusSuccess();
    } catch (err: any) {
      const msg = err?.message || 'Generation failed — check connection and try again.';
      this.specGenError.set(msg);
      this._setStatusFailure(msg);
    } finally {
      this.specGenLoading.set(false);
      this.specGenStep.set(null);
      this.specGenProjectName.set(null);
      this.specGenJobId.set(null);
      this.cancelling.set(false);
      this._stopGenPoll();
    }
  }

  async generateFromBraindump() {
    const proj = this.activeProject();
    if (!proj || this.specGenLoading()) return;
    if (!this.auth.isLoggedIn()) {
      this.specGenError.set('Sign in to generate specs.');
      this._setStatusFailure('Sign in to use AI features.');
      return;
    }
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
    this.specGenJobId.set(null);
    this.specGenFailedStep.set(null);
    this.cancelling.set(false);
    this._setStatusActive();
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
      this._setStatusSuccess();
    } catch (err: any) {
      const msg = err?.message || 'Generation failed — check connection and try again.';
      this.specGenError.set(msg);
      this._setStatusFailure(msg);
    } finally {
      this.specGenLoading.set(false);
      this.specGenStep.set(null);
      this.specGenProjectName.set(null);
      this.specGenJobId.set(null);
      this.cancelling.set(false);
      this._stopGenPoll();
    }
  }

  async generateEpicGuide() {
    const proj = this.activeProject();
    if (!proj || this.epicGuideLoading()) return;

    this.epicGuideLoading.set(true);
    this.epicGuideError.set(null);
    this._setStatusActive();
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
          this._setStatusSuccess();
          break;
        }
      }
    } catch (err: any) {
      const msg = err?.message || 'Guide generation failed.';
      this.epicGuideError.set(msg);
      this._setStatusFailure(msg);
    } finally {
      this.epicGuideLoading.set(false);
    }
  }

  navigateToUpgrade() {
    this.router.navigate(['/upgrade']);
  }

  logout() {
    this.auth.signOut();
  }

  toggleLoginForm() {
    this.showLoginForm.update(v => !v);
    this.loginError.set(null);
  }

  async doLogin(email: string, password: string) {
    if (!email || !password) return;
    this.loginLoading.set(true);
    this.loginError.set(null);
    try {
      await this.auth.login(email, password);
      this.showLoginForm.set(false);
    } catch (e: any) {
      this.loginError.set(e?.error?.error ?? 'Login failed');
    } finally {
      this.loginLoading.set(false);
    }
  }

  async shareProject() {
    const proj = this.activeProject();
    if (!proj || this.shareLoading()) return;
    this.shareLoading.set(true);
    try {
      const result = await this.projectsSvc.shareProject(proj.id);
      const fullUrl = `${window.location.origin}${result.url}`;
      this.shareUrl.set(fullUrl);
      await navigator.clipboard.writeText(fullUrl);
      this.shareCopied.set(true);
      setTimeout(() => this.shareCopied.set(false), 3000);
    } catch {
      // Ignore — share is best-effort
    } finally {
      this.shareLoading.set(false);
    }
  }

  // ── Helpers (used in template) ────────────────────

  /** Section name for a project — used in card meta label. */
  sectionForProject(p: Project): Section {
    return sectionFor(p, this.isActiveJob(p.id));
  }

  /**
   * Compute the teaser string for a project card.
   * leadFileContent is taken from the most relevant spec for the section.
   */
  teaserFor(p: Project): string {
    const hasJob = this.isActiveJob(p.id);
    const sec = sectionFor(p, hasJob);
    const activeStep = hasJob ? (this.specGenStep() ?? null) : null;

    // Pick lead file by section
    // Use content if loaded (single-project view), fall back to teaser (list view)
    const specText = (s: any) => s?.content ?? s?.teaser ?? null;

    let leadContent: string | null = null;
    if (sec === 'Active') {
      leadContent = specText(p.specs.find(s => s.filename === 'braindump.md'))
        ?? specText(p.specs.find(s => s.filename === 'epic.md'));
    } else if (sec === 'Specced') {
      leadContent = specText(p.specs.find(s => s.filename === 'implementation-guide.md'));
    } else if (sec === 'Ready to build') {
      leadContent = specText(p.specs.find(s => s.filename === 'architecture.md'))
        ?? specText(p.specs.find(s => s.filename === 'epic.md'));
    } else if (sec === 'Braindumps') {
      leadContent = specText(p.specs.find(s => s.filename === 'braindump.md'));
    }

    // Count tasks in implementation guide if present
    const guideText = specText(p.specs.find(s => s.filename === 'implementation-guide.md'));
    const taskCount = guideText != null ? countTasks(guideText) : null;

    return projectTeaser(sec, activeStep, leadContent, taskCount, null);
  }
}
