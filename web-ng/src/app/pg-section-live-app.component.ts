/**
 * pg-section-live-app.component.ts
 *
 * Playground V4 — Section 3 "Main Course".
 * Embeds the real specview app UI wired to demo fixture data.
 *
 * View states (Task 1 — Grid-OR-Detail Fix):
 *   - `grid`   — shows the project grid + section nav; no detail panel.
 *   - `detail` — shows a mini-masthead, horizontal tab nav, and the reader
 *                panel for the selected project and spec tab.  Grid is removed
 *                from the DOM entirely when in detail view.
 *
 * Defaults to `detail` with "Payment Gateway Redesign" (demo-ready-1)
 * and the `analysis.md` tab selected so visitors see rich content immediately.
 *
 * External activation (Task 3 — "See it live" handoff):
 *   The `activation` input signal accepts an object with `{ view, tab }`.
 *   The scroll shell (or a sibling section) can pass a value to programmatically
 *   switch to detail view with a specific tab selected.
 *
 * Dark-mode toggle is scoped to this section's host element only —
 * it sets [data-theme] on the `.live-app` container, not on <html>.
 *
 * No HTTP calls are made when DEMO_MODE is true (provided by the scroll shell).
 *
 * EXTRACTION STATUS: Extractable but heavyweight
 * ──────────────────────────────────────────────
 * Named export: PgSectionLiveAppComponent
 *
 * Prerequisite 1 — DEMO_MODE injection token:
 *   providers: [{ provide: DEMO_MODE, useValue: true }]
 *   Import the token from this file:
 *     import { DEMO_MODE } from './pg-section-live-app.component';
 *
 * Prerequisite 2 — playground-demo-data.ts fixture must be in the build.
 *
 * Transitive component dependencies (included via standalone imports array):
 *   ProjectGridComponent, SectionNavComponent, StatusBarComponent,
 *   SidebarV2Component, ReaderPanelComponent
 *
 * Usage outside the scroll shell:
 *   providers: [{ provide: DEMO_MODE, useValue: true }]
 *   <app-pg-section-live-app />
 */

import {
  ChangeDetectionStrategy,
  Component,
  signal,
  computed,
  input,
  output,
  effect,
} from '@angular/core';

import { ProjectGridComponent, ProjectsBySection } from './project-grid.component';
import { SectionNavComponent } from './section-nav.component';
import { StatusBarComponent } from './status-bar.component';
import { SidebarV2Component } from './sidebar-v2.component';
import { ReaderPanelComponent } from './reader-panel.component';

import {
  DEMO_PROJECTS,
  DEMO_NAV_SECTIONS,
  DEMO_SECTION_COUNTS,
  DEMO_ACTIVE_IDS,
} from './playground-demo-data';

import { Project, Spec } from './services/projects.service';
import { sectionFor } from './services/section-taxonomy.service';
import { SECTION_ORDER } from './services/section-taxonomy.service';

// Re-export for backwards compatibility
export { DEMO_MODE } from './tokens/demo-mode.token';

// ── View-state types ───────────────────────────────────────────────────────────

/** The two mutually exclusive view states for the Main Course section. */
export type LiveAppView = 'grid' | 'detail';

/**
 * Activation payload accepted via the `activation` input signal.
 * Task 3 ("See it live" handoff) emits this to programmatically
 * switch the live-app section to a specific view and tab.
 */
export interface LiveAppActivation {
  /** Target view to switch to. */
  view: LiveAppView;
  /** Spec filename (e.g. 'analysis.md') to pre-select in detail view. */
  tab: string;
}

// ── Detail-view tab definitions ───────────────────────────────────────────────

interface DetailTab {
  filename: string;
  label: string;
}

/** Ordered tabs shown in the horizontal section nav in detail view. */
const DETAIL_TABS: DetailTab[] = [
  { filename: 'braindump.md',         label: 'Braindump' },
  { filename: 'analysis.md',          label: 'Analysis' },
  { filename: 'epic.md',              label: 'Epic' },
  { filename: 'architecture.md',      label: 'Architecture' },
  { filename: 'implementation-guide.md', label: 'Impl Guide' },
];

/** ID of the default project shown in detail view on section entry. */
const DEFAULT_PROJECT_ID = 'demo-ready-1';

// ── Component ─────────────────────────────────────────────────────────────────

@Component({
  selector: 'app-pg-section-live-app',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    ProjectGridComponent,
    SectionNavComponent,
    StatusBarComponent,
    SidebarV2Component,
    ReaderPanelComponent,
  ],
  styles: [`
    /* Section wrapper */
    .live-app-section {
      padding: 32px 0 24px;
      height: 100%;
      box-sizing: border-box;
      overflow: hidden;
      display: flex;
      flex-direction: column;
    }

    .live-app__overline {
      font-family: var(--sans);
      font-size: 10px;
      font-weight: 700;
      letter-spacing: 0.16em;
      text-transform: uppercase;
      color: var(--ink-muted);
      margin-bottom: 12px;
      display: block;
    }

    /* Section nav row — horizontal, matching production */
    .live-app__section-nav-row {
      border-bottom: 1px solid var(--border);
    }

    .live-app__theme-toggle {
      display: flex;
      align-items: center;
      padding: 5px 10px;
      border: 1px solid var(--border);
      background: var(--surface);
      color: var(--ink);
      font-size: 14px;
      cursor: pointer;
      transition: background 120ms ease;
    }

    .live-app__theme-toggle:hover {
      background: var(--surface-raised);
    }

    /* ── Scoped app container ───────────────────────────────────────────────── */
    .live-app {
      border: 1px solid var(--border);
      border-radius: 2px;
      overflow: hidden;
      flex: 1;
      display: flex;
      flex-direction: column;
    }

    /* Status bar at top of embedded app */
    .live-app__status {
      border-bottom: 1px solid var(--border);
    }

    /* ── Grid view ─────────────────────────────────────────────────────────── */

    /* Main app body: project grid fills available space */
    .live-app__body {
      flex: 1;
      overflow: hidden;
    }

    /* Project grid column */
    .live-app__grid-col {
      height: 100%;
      overflow: hidden;
    }

    /* ── Detail view ───────────────────────────────────────────────────────── */

    /* Masthead bar — always visible, matches production */
    .live-app__masthead {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 10px 16px;
      border-bottom: 1px solid var(--border);
      background: var(--surface);
    }

    .live-app__masthead-actions {
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .live-app__masthead-logo {
      font-family: var(--serif);
      font-size: 15px;
      font-weight: 700;
      letter-spacing: -0.01em;
      color: var(--ink);
    }

    .live-app__back-btn {
      display: flex;
      align-items: center;
      gap: 6px;
      padding: 5px 12px;
      border: 1px solid var(--border);
      background: var(--surface);
      color: var(--ink-muted);
      font-family: var(--sans);
      font-size: 11px;
      font-weight: 600;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      cursor: pointer;
      transition: background 120ms ease, color 120ms ease, border-color 120ms ease;
    }

    .live-app__back-btn:hover {
      background: var(--surface-raised);
      color: var(--ink);
      border-color: var(--ink-muted);
    }

    /* Horizontal tab nav in detail view */
    .live-app__tab-nav {
      display: flex;
      align-items: stretch;
      border-bottom: 1px solid var(--border);
      background: var(--surface);
      overflow-x: auto;
    }

    .live-app__tab {
      padding: 10px 18px;
      font-family: var(--sans);
      font-size: 12px;
      font-weight: 600;
      letter-spacing: 0.06em;
      color: var(--ink-muted);
      background: none;
      border: none;
      border-bottom: 2px solid transparent;
      cursor: pointer;
      white-space: nowrap;
      transition: color 120ms ease, border-color 120ms ease;
    }

    .live-app__tab:hover {
      color: var(--ink);
    }

    .live-app__tab--active {
      color: var(--ink);
      border-bottom-color: var(--ink);
    }

    .live-app__tab--unavailable {
      opacity: 0.4;
      cursor: default;
      pointer-events: none;
    }

    /* Reader content area in detail view */
    .live-app__detail-body {
      display: grid;
      grid-template-columns: 260px 1fr;
      flex: 1;
      overflow: hidden;
    }

    .live-app__detail-sidebar {
      border-right: 1px solid var(--border);
      overflow: auto;
    }

    .live-app__detail-reader {
      overflow: auto;
    }


    @media (max-width: 768px) {
      .live-app-section {
        padding: 48px 0 80px;
      }

      .live-app__headline {
        font-size: 32px;
        margin-bottom: 12px;
      }

      .live-app__subhead {
        margin-bottom: 32px;
      }

      .live-app__body {
        grid-template-columns: 1fr;
      }

      .live-app__nav-col {
        border-right: none;
        border-bottom: 1px solid var(--border);
      }

      .live-app__detail-body {
        grid-template-columns: 1fr;
      }

      .live-app__detail-sidebar {
        border-right: none;
        border-bottom: 1px solid var(--border);
      }
    }
  `],
  template: `
    <div class="live-app-section">
      <span class="live-app__overline">Main Course — the real app, running on demo data</span>

      <!-- Embedded app container -->
      <div class="live-app" [attr.data-theme]="isDark() ? 'dark' : null">

        <!-- Masthead — matches production layout -->
        <div class="live-app__masthead">
          <span class="live-app__masthead-logo">Specview</span>
          <div class="live-app__masthead-actions">
            @if (activeView() === 'detail') {
              <button class="live-app__back-btn" (click)="closeDetail()">
                ← All Projects
              </button>
            }
            <button class="live-app__theme-toggle" (click)="toggleTheme()">
              {{ isDark() ? '☼' : '☾' }}
            </button>
          </div>
        </div>

        <!-- Section nav — horizontal, matching production -->
        @if (activeView() === 'grid') {
          <div class="live-app__section-nav-row">
            <app-section-nav
              [sections]="navSections"
              [activeSection]="activeNavSection()"
              [sectionCounts]="sectionCounts"
              [pulsingSections]="pulsingSections"
              (sectionSelected)="onNavSelect($event)"
            />
          </div>
        }

        <!-- Status bar -->
        <div class="live-app__status">
          <app-status-bar
            [mode]="'active'"
            [specGenProjectName]="'API Platform Spec'"
            [specGenStep]="'Generating epic…'"
            [specGenElapsed]="'12.4s'"
          />
        </div>

        <!-- ── GRID VIEW ────────────────────────────────────────────────────── -->
        @if (activeView() === 'grid') {
          <div class="live-app__body">
            <div class="live-app__grid-col">
              <app-project-grid
                [activeSection]="activeNavSection()"
                [filteredProjects]="filteredProjects()"
                [projectsBySection]="projectsBySection()"
                [columns]="columns()"
                [sectionLabel]="activeSectionLabel()"
                [teaserFn]="teaserFn"
                [sectionFn]="sectionFn"
                (projectSelected)="onProjectSelect($event)"
              />
            </div>
          </div>
        }

        <!-- ── DETAIL VIEW ──────────────────────────────────────────────────── -->
        @if (activeView() === 'detail') {

          <!-- Sidebar + reader panel -->
          <div class="live-app__detail-body">
            <div class="live-app__detail-sidebar">
              <app-sidebar-v2
                [activeProject]="selectedProject()"
                [activeFile]="activeTab()"
                [expandedProject]="selectedProject()?.name ?? ''"
                [mode]="'idle'"
                [currentSpec]="activeSpec()"
                (fileSelected)="selectTab($event)"
                (closeExpanded)="closeDetail()"
              />
            </div>
            <div class="live-app__detail-reader">
              <app-reader-panel
                [activeProject]="selectedProject()"
                [currentSpec]="activeSpec()"
                [expandedProject]="selectedProject()?.name ?? ''"
                [parsedContent]="parsedContent()"
                (closeExpanded)="closeDetail()"
              />
            </div>
          </div>
        }

      </div><!-- /.live-app -->
    </div>
  `,
})
export class PgSectionLiveAppComponent {

  // ── Dark-mode state (driven by parent scroll shell) ────────────────────────

  readonly isDark = input(false);
  readonly themeToggled = output<void>();

  toggleTheme(): void {
    this.themeToggled.emit();
  }

  // ── External activation (Task 3 — "See it live" handoff) ──────────────────

  /**
   * When the parent (scroll shell or sibling section) wants to programmatically
   * activate a specific view and tab, it passes a LiveAppActivation value here.
   * An effect watches for changes and applies the view/tab transition.
   */
  readonly activation = input<LiveAppActivation | null>(null);

  constructor() {
    effect(() => {
      const act = this.activation();
      if (!act) return;
      this.activeView.set(act.view);
      if (act.view === 'detail') {
        this.activeTab.set(act.tab);
      }
    });
  }

  // ── View state ─────────────────────────────────────────────────────────────

  /**
   * Mutually exclusive view state.
   * Defaults to 'detail' so visitors see rich content (Payment Gateway
   * Redesign analysis) immediately on section entry.
   */
  readonly activeView = signal<LiveAppView>('detail');

  /**
   * The currently selected spec tab in detail view (identified by filename).
   * Defaults to 'analysis.md'.
   */
  readonly activeTab = signal<string>('analysis.md');

  /** Ordered tab definitions rendered in the horizontal nav. */
  readonly detailTabs = DETAIL_TABS;

  closeDetail(): void {
    this.activeView.set('grid');
  }

  selectTab(filename: string): void {
    if (this.tabAvailable(filename)) {
      this.activeTab.set(filename);
    }
  }

  /** Returns true only when the selected project has a spec for this filename. */
  tabAvailable(filename: string): boolean {
    const project = this.selectedProject();
    if (!project) return false;
    return project.specs.some(s => s.filename === filename);
  }

  // ── Demo data ──────────────────────────────────────────────────────────────

  readonly navSections = DEMO_NAV_SECTIONS;
  readonly sectionCounts = DEMO_SECTION_COUNTS;
  readonly pulsingSections = new Set<string>(['Active']);

  private readonly allProjects = DEMO_PROJECTS;

  // ── Section nav state (grid view) ─────────────────────────────────────────

  readonly activeNavSection = signal('all');

  onNavSelect(id: string): void {
    this.activeNavSection.set(id);
  }

  readonly activeSectionLabel = computed(() => {
    const id = this.activeNavSection();
    return this.navSections.find(s => s.id === id)?.label ?? 'Projects';
  });

  // ── Project filtering (grid view) ─────────────────────────────────────────

  readonly filteredProjects = computed((): Project[] => {
    const section = this.activeNavSection();
    if (section === 'all') return this.allProjects;
    return this.allProjects.filter(p => this.sectionFn(p) === section);
  });

  readonly projectsBySection = computed((): ProjectsBySection[] => {
    const groups: ProjectsBySection[] = [];
    for (const sec of SECTION_ORDER) {
      const projects = this.allProjects.filter(p => this.sectionFn(p) === sec);
      if (projects.length > 0) {
        groups.push({ section: sec, projects });
      }
    }
    return groups;
  });

  readonly columns = computed((): Project[][] => {
    const projects = this.filteredProjects();
    if (this.activeNavSection() === 'all') return [];
    const col1: Project[] = [];
    const col2: Project[] = [];
    projects.forEach((p, i) => (i % 2 === 0 ? col1 : col2).push(p));
    return col2.length > 0 ? [col1, col2] : [col1];
  });

  readonly teaserFn = (p: Project): string => {
    const spec = p.specs.find(s => s.teaser || s.content);
    return spec?.teaser ?? spec?.content?.slice(0, 120) ?? p.name;
  };

  readonly sectionFn = (p: Project) =>
    sectionFor(p, DEMO_ACTIVE_IDS.has(p.id));

  // ── Project selection (detail view) ───────────────────────────────────────

  /**
   * The selected project ID.
   * Defaults to the Payment Gateway Redesign so visitors see rich content
   * immediately when the detail view loads.
   */
  readonly selectedProjectId = signal<string>(DEFAULT_PROJECT_ID);

  readonly selectedProject = computed((): Project | null => {
    const id = this.selectedProjectId();
    return this.allProjects.find(p => p.id === id) ?? null;
  });

  readonly activeSpec = computed((): Spec | null => {
    const project = this.selectedProject();
    const file = this.activeTab();
    if (!project || !file) return null;
    return project.specs.find(s => s.filename === file) ?? null;
  });

  readonly parsedContent = computed((): string => {
    const spec = this.activeSpec();
    return spec?.content ?? spec?.teaser ?? '';
  });

  /** Called when a project card in grid view is clicked. */
  onProjectSelect(id: string): void {
    this.selectedProjectId.set(id);
    this.activeTab.set('analysis.md');
    this.activeView.set('detail');
  }
}
