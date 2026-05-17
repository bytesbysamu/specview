/**
 * pg-section-live-app.component.ts
 *
 * Playground V3 — Section 3 "Main Course".
 * Embeds the real specview V2 app component tree wired to demo fixture data.
 *
 * Dark-mode toggle is scoped to this section's host element only —
 * it sets [data-theme] on the `.live-app` container, not on <html>.
 * This means the scroll shell and all other sections are unaffected.
 *
 * No HTTP calls are made when DEMO_MODE is true (provided by the scroll shell).
 * The demo-mode branch in ProjectsService short-circuits every list/get call
 * and returns fixture data from playground-demo-data.ts.
 *
 * EXTRACTION STATUS: Extractable but heavyweight
 * ──────────────────────────────────────────────
 * Named export: PgSectionLiveAppComponent
 *
 * This component has no coupling to PgScrollShellComponent's internal signals
 * or gating state machine — all state is managed through its own signals.
 * However, it carries two prerequisites that a landing page consumer must
 * satisfy before extracting this component:
 *
 * Prerequisite 1 — DEMO_MODE injection token:
 *   The component itself does not inject DEMO_MODE, but ProjectsService reads
 *   it to short-circuit HTTP calls. The scroll shell provides it via:
 *     providers: [{ provide: DEMO_MODE, useValue: true }]
 *   A landing page or standalone harness must do the same, otherwise
 *   ProjectsService will attempt live HTTP calls.
 *   Import the token from this file:
 *     import { DEMO_MODE } from './pg-section-live-app.component';
 *
 * Prerequisite 2 — playground-demo-data.ts fixture:
 *   This component imports DEMO_PROJECTS, DEMO_NAV_SECTIONS,
 *   DEMO_SECTION_COUNTS, DEMO_ACTIVE_IDS, and PIPELINE_STAGES directly from
 *   playground-demo-data.ts. Any consumer must ensure this fixture file is
 *   included in the build. No additional wiring is required — the imports are
 *   static.
 *
 * Transitive component dependencies (included via standalone imports array):
 *   ProjectGridComponent, SectionNavComponent, StatusBarComponent,
 *   SidebarV2Component, ReaderPanelComponent
 *
 * Usage outside the scroll shell:
 *   // In the consumer's providers array:
 *   providers: [{ provide: DEMO_MODE, useValue: true }]
 *   // In the template:
 *   <app-pg-section-live-app />
 */

import {
  ChangeDetectionStrategy,
  Component,
  signal,
  computed,
  input,
  output,
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
      padding: 40px 0 40px;
      height: 100%;
      box-sizing: border-box;
      overflow-y: auto;
    }

    .live-app__overline {
      font-family: var(--sans);
      font-size: 11px;
      font-weight: 700;
      letter-spacing: 0.18em;
      text-transform: uppercase;
      color: var(--ink-muted);
      margin-bottom: 32px;
      display: block;
    }

    .live-app__headline {
      font-family: var(--serif);
      font-size: 48px;
      font-weight: 700;
      letter-spacing: -0.02em;
      line-height: 1.1;
      color: var(--ink);
      max-width: 640px;
      margin-bottom: 16px;
    }

    .live-app__subhead {
      font-family: var(--body);
      font-size: 15px;
      line-height: 1.65;
      color: var(--ink-light);
      max-width: 480px;
      margin-bottom: 48px;
    }

    /* Dark-mode toggle row */
    .live-app__controls {
      display: flex;
      align-items: center;
      gap: 12px;
      margin-bottom: 32px;
      padding-bottom: 20px;
      border-bottom: 1px solid var(--border);
    }

    .live-app__controls-label {
      font-family: var(--sans);
      font-size: 11px;
      font-weight: 600;
      letter-spacing: 0.12em;
      text-transform: uppercase;
      color: var(--ink-muted);
    }

    .live-app__theme-toggle {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 6px 14px;
      border: 1px solid var(--border);
      background: var(--surface);
      color: var(--ink);
      font-family: var(--sans);
      font-size: 12px;
      font-weight: 600;
      letter-spacing: 0.06em;
      cursor: pointer;
      transition: background 120ms ease, border-color 120ms ease;
    }

    .live-app__theme-toggle:hover {
      background: var(--surface-raised);
      border-color: var(--ink-muted);
    }

    .live-app__theme-note {
      font-family: var(--body);
      font-size: 12px;
      color: var(--ink-muted);
      font-style: italic;
    }

    /* ── Scoped app container ───────────────────────────────────────────────── */
    /* [data-theme] on this element overrides tokens for children only */
    .live-app {
      border: 1px solid var(--border);
      border-radius: 2px;
      overflow: hidden;
    }

    /* Status bar at top of embedded app */
    .live-app__status {
      border-bottom: 1px solid var(--border);
    }

    /* Main app body: section nav + project grid side by side */
    .live-app__body {
      display: grid;
      grid-template-columns: auto 1fr;
      min-height: 420px;
    }

    /* Section nav column */
    .live-app__nav-col {
      border-right: 1px solid var(--border);
    }

    /* Project grid column */
    .live-app__grid-col {
      overflow: auto;
    }

    /* Selected project detail: sidebar + reader panel */
    .live-app__detail {
      display: grid;
      grid-template-columns: 260px 1fr;
      border-top: 1px solid var(--border);
      min-height: 360px;
    }

    .live-app__detail-sidebar {
      border-right: 1px solid var(--border);
      overflow: auto;
    }

    .live-app__detail-reader {
      overflow: auto;
    }

    /* Caption below the embedded app */
    .live-app__caption {
      font-family: var(--body);
      font-size: 13px;
      font-style: italic;
      color: var(--ink-muted);
      line-height: 1.55;
      margin-top: 24px;
      border-top: 1px solid var(--border);
      padding-top: 16px;
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

      .live-app__detail {
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
      <span class="live-app__overline">Main Course</span>

      <h2 class="live-app__headline">The real app, running on demo data.</h2>

      <p class="live-app__subhead">
        Every component you see is production code — project grid, sidebar,
        reader panel, section nav, and status bar — wired to fixture data
        instead of the Flask API.
      </p>

      <!-- Dark-mode toggle — scoped to this section only -->
      <div class="live-app__controls">
        <span class="live-app__controls-label">Theme</span>
        <button class="live-app__theme-toggle" (click)="toggleTheme()">
          {{ isDark() ? 'Switch to Light' : 'Switch to Dark' }}
        </button>
        <span class="live-app__theme-note">
          Affects the embedded app only — not the rest of the page.
        </span>
      </div>

      <!-- Embedded app container -->
      <div class="live-app">

        <!-- Status bar -->
        <div class="live-app__status">
          <app-status-bar
            [mode]="'active'"
            [specGenProjectName]="'API Platform Spec'"
            [specGenStep]="'Generating epic…'"
            [specGenElapsed]="'12.4s'"
          />
        </div>

        <!-- Section nav + project grid -->
        <div class="live-app__body">
          <div class="live-app__nav-col">
            <app-section-nav
              [sections]="navSections"
              [activeSection]="activeNavSection()"
              [sectionCounts]="sectionCounts"
              [pulsingSections]="pulsingSections"
              (sectionSelected)="onNavSelect($event)"
            />
          </div>
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

        <!-- Expanded project detail: sidebar + reader -->
        @if (selectedProject()) {
          <div class="live-app__detail">
            <div class="live-app__detail-sidebar">
              <app-sidebar-v2
                [activeProject]="selectedProject()"
                [activeFile]="activeFile()"
                [expandedProject]="selectedProject()!.name"
                [mode]="'idle'"
                [currentSpec]="activeSpec()"
                (fileSelected)="onFileSelect($event)"
                (closeExpanded)="onCloseProject()"
              />
            </div>
            <div class="live-app__detail-reader">
              <app-reader-panel
                [activeProject]="selectedProject()"
                [currentSpec]="activeSpec()"
                [expandedProject]="selectedProject()!.name"
                [parsedContent]="parsedContent()"
                (closeExpanded)="onCloseProject()"
              />
            </div>
          </div>
        }

      </div><!-- /.live-app -->

      <p class="live-app__caption">
        No HTTP calls — all data is local. The dark-mode toggle proves the token
        system: a single <code>[data-theme]</code> attribute swap rewires every
        component in the tree.
      </p>
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

  // ── Demo data ──────────────────────────────────────────────────────────────

  readonly navSections = DEMO_NAV_SECTIONS;
  readonly sectionCounts = DEMO_SECTION_COUNTS;
  readonly pulsingSections = new Set<string>(['Active']);

  /** Projects enriched with an active-job flag based on DEMO_ACTIVE_IDS. */
  private readonly allProjects = DEMO_PROJECTS;

  // ── Section nav state ──────────────────────────────────────────────────────

  readonly activeNavSection = signal('all');

  onNavSelect(id: string): void {
    this.activeNavSection.set(id);
    // Clear project selection when switching tabs
    this.selectedProjectId.set(null);
  }

  readonly activeSectionLabel = computed(() => {
    const id = this.activeNavSection();
    return this.navSections.find(s => s.id === id)?.label ?? 'Projects';
  });

  // ── Project filtering ──────────────────────────────────────────────────────

  readonly filteredProjects = computed((): Project[] => {
    const section = this.activeNavSection();
    if (section === 'all') return this.allProjects;
    return this.allProjects.filter(p => this.sectionFn(p) === section);
  });

  /**
   * Projects grouped by taxonomy section in canonical order.
   * Used by the 'all' view of project-grid.
   */
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

  /**
   * Column layout for filtered (non-'all') views.
   * Splits projects into two columns for the masonry-style grid.
   */
  readonly columns = computed((): Project[][] => {
    const projects = this.filteredProjects();
    if (this.activeNavSection() === 'all') return [];
    const col1: Project[] = [];
    const col2: Project[] = [];
    projects.forEach((p, i) => (i % 2 === 0 ? col1 : col2).push(p));
    return col2.length > 0 ? [col1, col2] : [col1];
  });

  /** Teaser text for a project card — uses first spec teaser or name. */
  readonly teaserFn = (p: Project): string => {
    const spec = p.specs.find(s => s.teaser || s.content);
    return spec?.teaser ?? spec?.content?.slice(0, 120) ?? p.name;
  };

  /** Section classifier for a project. */
  readonly sectionFn = (p: Project) =>
    sectionFor(p, DEMO_ACTIVE_IDS.has(p.id));

  // ── Project selection and reader state ────────────────────────────────────

  readonly selectedProjectId = signal<string | null>('demo-ready-1');

  readonly selectedProject = computed((): Project | null => {
    const id = this.selectedProjectId();
    return id ? (this.allProjects.find(p => p.id === id) ?? null) : null;
  });

  readonly activeFile = signal<string | null>('analysis.md');

  readonly activeSpec = computed((): Spec | null => {
    const project = this.selectedProject();
    const file = this.activeFile();
    if (!project || !file) return null;
    return project.specs.find(s => s.filename === file) ?? null;
  });

  /** SafeHtml — for the demo we pass the raw markdown text as string (no XSS risk with static fixtures). */
  readonly parsedContent = computed((): string => {
    const spec = this.activeSpec();
    return spec?.content ?? spec?.teaser ?? '';
  });

  onProjectSelect(id: string): void {
    this.selectedProjectId.set(id);
    const project = this.allProjects.find(p => p.id === id);
    if (project && project.specs.length > 0) {
      this.activeFile.set(project.specs[0].filename);
    }
  }

  onFileSelect(filename: string): void {
    this.activeFile.set(filename);
  }

  onCloseProject(): void {
    this.selectedProjectId.set(null);
    this.activeFile.set(null);
  }
}
