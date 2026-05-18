import {
  Component,
  EffectRef,
  OnInit,
  OnDestroy,
  signal,
  computed,
  effect,
  inject,
} from '@angular/core';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';
import { marked } from 'marked';
import DOMPurify from 'dompurify';

import { RouterLink } from '@angular/router';
import { AuthService } from '../../services/auth.service';
import { DemoAwareProjectsService } from '../../services/demo-aware-projects.service';
import { Project, Spec } from '../../services/projects.service';
import {
  Section,
  sectionFor,
  SECTION_ORDER,
} from '../../services/section-taxonomy.service';
import { projectTeaser, countTasks } from '../../services/project-teaser';
import { ProjectGridComponent, ProjectsBySection } from '../../project-grid.component';
import { ReaderPanelComponent } from '../../reader-panel.component';
import { StatusBarComponent } from '../../status-bar.component';

@Component({
  selector: 'app-app-page',
  standalone: true,
  imports: [ProjectGridComponent, ReaderPanelComponent, StatusBarComponent, RouterLink],
  templateUrl: './app-page.component.html',
  styleUrl: './app-page.component.css',
})
export class AppPageComponent implements OnInit, OnDestroy {
  private readonly sanitizer = inject(DomSanitizer);
  readonly auth = inject(AuthService);
  readonly dataSvc = inject(DemoAwareProjectsService);

  // ── Project list state ──────────────────────────────────────────────────────

  readonly projects = signal<Project[]>([]);
  readonly loadError = signal<string | null>(null);

  // ── Selection state ─────────────────────────────────────────────────────────

  readonly selectedProjectId = signal<string | null>(null);
  readonly selectedSpecFile = signal<string | null>(null);

  readonly activeProject = computed<Project | null>(() => {
    const id = this.selectedProjectId();
    if (!id) return null;
    return this.projects().find(p => p.id === id) ?? null;
  });

  readonly currentSpec = computed<Spec | null>(() => {
    const p = this.activeProject();
    if (!p) return null;
    const file = this.selectedSpecFile();
    if (file) return p.specs.find(s => s.filename === file) ?? p.specs[0] ?? null;
    return p.specs[0] ?? null;
  });

  // ── Parsed content for reader panel ─────────────────────────────────────────

  readonly parsedContent = computed<SafeHtml>(() => {
    const spec = this.currentSpec();
    const raw = spec?.content ?? '';
    if (!raw) return '';
    const html = marked.parse(raw) as string;
    return this.sanitizer.bypassSecurityTrustHtml(DOMPurify.sanitize(html));
  });

  readonly expandedTitle = computed(() => {
    const spec = this.currentSpec();
    return spec?.label ?? '';
  });

  // ── Section navigation ───────────────────────────────────────────────────────

  readonly activeSection = signal<string>('all');

  readonly projectsBySection = computed<ProjectsBySection[]>(() => {
    const all = this.projects();
    const map = new Map<Section, Project[]>(SECTION_ORDER.map(s => [s, []]));
    for (const p of all) {
      const section = sectionFor(p, false);
      map.get(section)!.push(p);
    }
    return SECTION_ORDER
      .filter(s => (map.get(s)?.length ?? 0) > 0)
      .map(s => ({ section: s, projects: map.get(s)! }));
  });

  readonly filteredProjects = computed<Project[]>(() => {
    const section = this.activeSection();
    const all = this.projects();
    if (section === 'all') return all;
    return all.filter(p => sectionFor(p, false) === section);
  });

  /** Two-column layout for single-section views. */
  readonly columns = computed<Project[][]>(() => {
    const fp = this.filteredProjects();
    if (fp.length === 0) return [[], []];
    const mid = Math.ceil(fp.length / 2);
    return [fp.slice(0, mid), fp.slice(mid)];
  });

  readonly sectionLabel = computed(() => {
    const s = this.activeSection();
    return s === 'all' ? 'Projects' : s;
  });

  // ── Auth-transition reload tracking ─────────────────────────────────────────

  private _lastAuthState: boolean | null = null;
  private _authEffectRef: EffectRef;

  constructor() {
    this._authEffectRef = effect(() => {
      const isLoggedIn = this.auth.isLoggedIn();
      if (this._lastAuthState !== null && isLoggedIn !== this._lastAuthState) {
        // Auth state changed — reload projects reactively
        this.loadProjects();
      }
      this._lastAuthState = isLoggedIn;
    });
  }

  // ── Lifecycle ────────────────────────────────────────────────────────────────

  ngOnInit(): void {
    this.loadProjects();
  }

  ngOnDestroy(): void {
    this._authEffectRef.destroy();
  }

  // ── Data loading ─────────────────────────────────────────────────────────────

  async loadProjects(): Promise<void> {
    this.loadError.set(null);
    try {
      const list = await this.dataSvc.getProjects();
      this.projects.set(list);
      // Auto-select first project so the reader panel is never empty
      if (list.length > 0 && !this.selectedProjectId()) {
        this.selectedProjectId.set(list[0].id);
      }
      // If the authenticated user has no projects, clear any stale selection
      if (list.length === 0) {
        this.selectedProjectId.set(null);
        this.selectedSpecFile.set(null);
      }
    } catch (e: any) {
      this.loadError.set(e?.error?.error ?? e?.message ?? 'Failed to load projects');
    }
  }

  // ── Event handlers ───────────────────────────────────────────────────────────

  selectProject(id: string): void {
    this.selectedProjectId.set(id);
    this.selectedSpecFile.set(null);
  }

  selectSpec(filename: string): void {
    this.selectedSpecFile.set(filename);
  }

  closeReader(): void {
    this.selectedProjectId.set(null);
    this.selectedSpecFile.set(null);
  }

  // ── Template helpers ─────────────────────────────────────────────────────────

  teaserFor(p: Project): string {
    const section = sectionFor(p, false);
    const leadSpec = p.specs.find(s =>
      ['implementation-guide.md', 'architecture.md', 'epic.md', 'analysis.md', 'braindump.md']
        .includes(s.filename)
    );
    const taskCount = leadSpec?.content ? countTasks(leadSpec.content) : null;
    return projectTeaser(section, null, leadSpec?.content, taskCount);
  }

  sectionForProject(p: Project): Section {
    return sectionFor(p, false);
  }
}
