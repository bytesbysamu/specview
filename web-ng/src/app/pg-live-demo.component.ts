import {
  ChangeDetectionStrategy,
  Component,
  computed,
  inject,
  signal,
} from '@angular/core';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';
import { marked } from 'marked';
import DOMPurify from 'dompurify';

import { Project } from './services/projects.service';
import { Section, sectionFor, SECTION_ORDER } from './services/section-taxonomy.service';
import { projectTeaser, countTasks } from './services/project-teaser';
import { ProjectsBySection } from './project-grid.component';

import { SectionNavComponent } from './section-nav.component';
import { StatusBarComponent } from './status-bar.component';
import { ProjectGridComponent } from './project-grid.component';
import { SidebarV2Component } from './sidebar-v2.component';
import { ReaderPanelComponent } from './reader-panel.component';

import {
  DEMO_PROJECTS,
  DEMO_NAV_SECTIONS,
  DEMO_ACTIVE_IDS,
} from './playground-demo-data';

@Component({
  selector: 'app-pg-live-demo',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    SectionNavComponent,
    StatusBarComponent,
    ProjectGridComponent,
    SidebarV2Component,
    ReaderPanelComponent,
  ],
  template: `
    <!-- ── Editorial header ──────────────────────────────────────────────────── -->
    <div class="ld-header">
      <div class="ld-overline">The Product</div>
      <h2 class="ld-headline">The real app, with demo data.</h2>
      <p class="ld-deck">
        Every component below is the production code — same signals, same templates,
        same CSS — wired to static demo projects instead of the live API.
        No screenshots. No mocks.
      </p>
    </div>

    <!-- ── Demo frame ─────────────────────────────────────────────────────────── -->
    <div class="ld-frame">

      <!-- Section nav -->
      <app-section-nav
        [sections]="demoNavSections"
        [activeSection]="selectedSection()"
        [sectionCounts]="sectionCounts()"
        [pulsingSections]="emptySet"
        [contextFileCount]="0"
        (sectionSelected)="selectSection($event)"
      />

      <!-- Status bar -->
      <app-status-bar
        [mode]="activeProject()?.id === 'demo-active-2' ? 'active' : 'idle'"
        [specGenProjectName]="activeProject()?.id === 'demo-active-2' ? 'API Platform Spec' : null"
        specGenStep="generating epic"
        specGenElapsed="18.4s"
        [specGenJobId]="null"
        [statusFailureMsg]="null"
        [cancelling]="false"
      />

      @if (activeProject() === null) {
        <!-- Project grid -->
        <app-project-grid
          [activeSection]="selectedSection()"
          [filteredProjects]="filteredProjects()"
          [projectsBySection]="projectsBySection()"
          [columns]="columns()"
          [contextFiles]="[]"
          [sectionLabel]="sectionLabel()"
          [teaserFn]="teaserFn"
          [sectionFn]="sectionFn"
          (projectSelected)="selectProject($event)"
          (contextOpened)="onContextOpened($event)"
        />
      } @else {
        <!-- Expanded panel -->
        <div class="ld-expanded">
          <app-sidebar-v2
            [activeProject]="activeProject()"
            [activeFile]="selectedFile()"
            expandedProject=""
            mode="idle"
            [specGenLoading]="false"
            [specGenStep]="null"
            activeStepLabel=""
            [statusFailureMsg]="null"
            [shareLoading]="false"
            [shareUrl]="null"
            [shareCopied]="false"
            [canGenerateSpecs]="false"
            [canGenerateEpicGuide]="false"
            [epicGuideLoading]="false"
            [currentSpec]="currentSpec()"
            [isBraindump]="false"
            [activeOp]="null"
            [aiLoading]="false"
            [aiResult]="null"
            [canRevert]="false"
            [canRedo]="false"
            [fileOpState]="{}"
            [stylePresets]="[]"
            (fileSelected)="selectFile($event)"
            (closeExpanded)="closeExpanded()"
          />
          <app-reader-panel
            [activeProject]="activeProject()"
            [currentSpec]="currentSpec()"
            [accessDenied]="false"
            [expandedTitle]="currentSpec()?.label ?? ''"
            [expandedProject]="activeProject()?.name ?? ''"
            [activeFileType]="activeFileType()"
            [parsedContent]="parsedContent()"
            parsedAiResult=""
            diffHtmlUnified=""
            [aiResult]="null"
            [aiLoading]="false"
            [aiError]="false"
            [aiLatencyMs]="null"
            [activeOp]="null"
            [isAdditiveOp]="false"
            [billingError]="null"
            [copied]="false"
            brainstormQuestion=""
            [canGenerateSpecs]="false"
            [specGenLoading]="false"
            [specGenProjectName]="null"
            [specGenStep]="null"
            [specGenError]="null"
            [specGenFailedStep]="null"
            [cancelling]="false"
            (closeExpanded)="closeExpanded()"
          />
        </div>
      }

      <!-- Demo annotation -->
      @if (activeProject()?.id === 'demo-active-2') {
        <div class="ld-annotation">Demo — generation simulation</div>
      }

    </div>

    <!-- ── Closing pullquote ───────────────────────────────────────────────────── -->
    <blockquote class="ld-pullquote">
      "A screenshot tells you what the product looks like.
      A live component tells you what it&rsquo;s made of."
    </blockquote>
  `,
  styles: [`
    /* ── Editorial header ──────────────────────────────────────────────────────── */
    .ld-header {
      margin-bottom: 48px;
    }

    .ld-overline {
      font-family: 'Source Sans 3', 'Source Sans Pro', sans-serif;
      font-size: 11px;
      font-weight: 700;
      letter-spacing: 0.12em;
      text-transform: uppercase;
      color: var(--accent, #6366f1);
      margin-bottom: 12px;
    }

    .ld-headline {
      font-family: 'Source Serif 4', 'Source Serif Pro', Georgia, serif;
      font-size: 36px;
      font-weight: 700;
      color: var(--ink, #111827);
      margin: 0 0 16px;
      line-height: 1.15;
    }

    .ld-deck {
      font-family: 'Source Serif 4', 'Source Serif Pro', Georgia, serif;
      font-size: 18px;
      line-height: 1.65;
      color: var(--ink-muted, #6b7280);
      max-width: 640px;
      margin: 0;
    }

    /* ── Demo frame ────────────────────────────────────────────────────────────── */
    .ld-frame {
      border: 1px solid var(--border, #e5e7eb);
      border-radius: 6px;
      overflow: hidden;
      background: var(--bg, #fff);
      margin-bottom: 48px;
    }

    /* ── Expanded panel ────────────────────────────────────────────────────────── */
    .ld-expanded {
      display: flex;
      min-height: 520px;
    }

    /* ── Demo annotation ───────────────────────────────────────────────────────── */
    .ld-annotation {
      padding: 6px 16px;
      font-family: 'Source Sans 3', 'Source Sans Pro', sans-serif;
      font-size: 11px;
      font-weight: 600;
      letter-spacing: 0.06em;
      text-transform: uppercase;
      color: var(--ink-muted, #6b7280);
      border-top: 1px solid var(--border, #e5e7eb);
      background: var(--bg-subtle, #f9fafb);
    }

    /* ── Pullquote ─────────────────────────────────────────────────────────────── */
    .ld-pullquote {
      font-family: 'Source Serif 4', 'Source Serif Pro', Georgia, serif;
      font-size: 22px;
      font-style: italic;
      line-height: 1.5;
      color: var(--ink-muted, #6b7280);
      border-left: 3px solid var(--accent, #6366f1);
      padding: 4px 0 4px 24px;
      margin: 0;
    }
  `],
})
export class PgLiveDemoComponent {
  private sanitizer = inject(DomSanitizer);

  readonly demoNavSections = DEMO_NAV_SECTIONS;
  readonly emptySet = new Set<string>();

  // ── State ─────────────────────────────────────────────────────────────────────

  selectedSection = signal<string>('all');
  selectedProject = signal<Project | null>(DEMO_PROJECTS[0]);
  selectedFile    = signal<string | null>(DEMO_PROJECTS[0]?.specs[0]?.filename ?? null);

  // ── Helpers ───────────────────────────────────────────────────────────────────

  private isActive(p: Project): boolean {
    return DEMO_ACTIVE_IDS.has(p.id);
  }

  // ── Computed ──────────────────────────────────────────────────────────────────

  activeProject = computed(() => this.selectedProject());

  sectionCounts = computed<Record<string, number>>(() => {
    const counts: Record<string, number> = {};
    DEMO_PROJECTS.forEach(p => {
      const sec = sectionFor(p, this.isActive(p));
      counts[sec] = (counts[sec] ?? 0) + 1;
      counts['all'] = (counts['all'] ?? 0) + 1;
    });
    return counts;
  });

  filteredProjects = computed<Project[]>(() => {
    const section = this.selectedSection();
    if (section === 'all') return DEMO_PROJECTS;
    return DEMO_PROJECTS.filter(p => sectionFor(p, this.isActive(p)) === section);
  });

  projectsBySection = computed<ProjectsBySection[]>(() => {
    const map = new Map<Section, Project[]>();
    for (const sec of SECTION_ORDER) map.set(sec, []);
    DEMO_PROJECTS.forEach(p => {
      const sec = sectionFor(p, this.isActive(p));
      map.get(sec)!.push(p);
    });
    return SECTION_ORDER
      .map(sec => ({ section: sec, projects: map.get(sec)! }))
      .filter(g => g.projects.length > 0);
  });

  columns = computed<Project[][]>(() => {
    const projects = this.filteredProjects();
    const numCols = Math.min(3, Math.ceil(projects.length / 2)) || 1;
    const cols: Project[][] = Array.from({ length: numCols }, () => []);
    projects.forEach((p, i) => cols[i % numCols].push(p));
    return cols;
  });

  sectionLabel = computed(() =>
    DEMO_NAV_SECTIONS.find(s => s.id === this.selectedSection())?.label ?? 'Projects'
  );

  currentSpec = computed(() => {
    const proj = this.selectedProject();
    const file = this.selectedFile();
    if (!proj || !file) return null;
    return proj.specs.find(s => s.filename === file) ?? null;
  });

  parsedContent = computed<SafeHtml>(() => {
    const spec = this.currentSpec();
    const content = spec?.content ?? '';
    if (!content) return '';
    return this.sanitizer.bypassSecurityTrustHtml(
      DOMPurify.sanitize(marked.parse(content) as string)
    );
  });

  activeFileType = computed((): string | null => {
    const file = this.selectedFile();
    if (!file || !this.selectedProject()) return null;
    return file.replace(/\.md$/i, '').replace(/-/g, ' ').toUpperCase();
  });

  // ── Input callbacks for ProjectGridComponent ─────────────────────────────────

  teaserFn = (p: Project): string => {
    const sec = sectionFor(p, this.isActive(p));
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
    } else {
      leadContent = specText(p.specs.find(s => s.filename === 'braindump.md'));
    }
    const guideText = specText(p.specs.find(s => s.filename === 'implementation-guide.md'));
    const taskCount = guideText != null ? countTasks(guideText) : null;
    return projectTeaser(sec, null, leadContent, taskCount, null);
  };

  sectionFn = (p: Project): Section => sectionFor(p, this.isActive(p));

  // ── Methods ───────────────────────────────────────────────────────────────────

  selectSection(id: string): void {
    this.selectedSection.set(id);
    this.selectedProject.set(null);
    this.selectedFile.set(null);
  }

  selectProject(id: string): void {
    const proj = DEMO_PROJECTS.find(p => p.id === id) ?? null;
    this.selectedProject.set(proj);
    this.selectedFile.set(proj?.specs[0]?.filename ?? null);
  }

  selectFile(filename: string): void {
    this.selectedFile.set(filename);
  }

  closeExpanded(): void {
    this.selectedProject.set(null);
    this.selectedFile.set(null);
  }

  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  onContextOpened(_key: string): void {
    // No-op — context files are not available in demo mode.
  }
}
