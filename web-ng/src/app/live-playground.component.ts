import { Component, inject, signal, computed, OnInit } from '@angular/core';
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
import { LandingPitchComponent } from './landing-pitch.component';

import {
  DEMO_PROJECTS,
  DEMO_NAV_SECTIONS,
  DEMO_SECTION_COUNTS,
} from './playground-demo-data';

@Component({
  selector: 'app-live-playground',
  standalone: true,
  imports: [
    SectionNavComponent,
    StatusBarComponent,
    ProjectGridComponent,
    SidebarV2Component,
    ReaderPanelComponent,
    LandingPitchComponent,
  ],
  templateUrl: './live-playground.component.html',
  styleUrl: './live-playground.component.css',
})
export class LivePlaygroundComponent implements OnInit {
  private sanitizer = inject(DomSanitizer);

  // ── Exposed constants for template ───────────────────────────────────────
  readonly demoNavSections = DEMO_NAV_SECTIONS;

  // ── Demo signals ─────────────────────────────────────────────────────────
  demoProjects    = signal<Project[]>(DEMO_PROJECTS);
  demoActiveSection = signal<string>('all');
  demoActiveProject = signal<Project | null>(null);
  demoActiveFile    = signal<string | null>(null);
  isDark            = signal<boolean>(false);

  // ── Computed ──────────────────────────────────────────────────────────────

  demoSectionCounts = computed<Record<string, number>>(() => {
    const counts: Record<string, number> = {};
    this.demoProjects().forEach(p => {
      const sec = sectionFor(p, false);
      counts[sec] = (counts[sec] ?? 0) + 1;
      counts['all'] = (counts['all'] ?? 0) + 1;
    });
    return counts;
  });

  demoProjectsBySection = computed<ProjectsBySection[]>(() => {
    const map = new Map<Section, Project[]>();
    for (const sec of SECTION_ORDER) map.set(sec, []);
    this.demoProjects().forEach(p => {
      const sec = sectionFor(p, false);
      map.get(sec)!.push(p);
    });
    return SECTION_ORDER
      .map(sec => ({ section: sec, projects: map.get(sec)! }))
      .filter(g => g.projects.length > 0);
  });

  demoFilteredProjects = computed<Project[]>(() => {
    const section = this.demoActiveSection();
    if (section === 'all') return this.demoProjects();
    return this.demoProjects().filter(p => sectionFor(p, false) === section);
  });

  demoColumns = computed<Project[][]>(() => {
    const projects = this.demoFilteredProjects();
    const numCols = Math.min(3, Math.ceil(projects.length / 2)) || 1;
    const cols: Project[][] = Array.from({ length: numCols }, () => []);
    projects.forEach((p, i) => cols[i % numCols].push(p));
    return cols;
  });

  demoCurrentSpec = computed(() => {
    const proj = this.demoActiveProject();
    const file = this.demoActiveFile();
    if (!proj || !file) return null;
    return proj.specs.find(s => s.filename === file) ?? null;
  });

  demoParsedContent = computed<SafeHtml>(() => {
    const spec = this.demoCurrentSpec();
    const content = spec?.content ?? '';
    if (!content) return '';
    return this.sanitizer.bypassSecurityTrustHtml(
      DOMPurify.sanitize(marked.parse(content) as string)
    );
  });

  demoSectionLabel = computed(() =>
    DEMO_NAV_SECTIONS.find(s => s.id === this.demoActiveSection())?.label ?? 'Projects'
  );

  demoActiveFileType = computed((): string | null => {
    const file = this.demoActiveFile();
    if (!file || !this.demoActiveProject()) return null;
    return file.replace(/\.md$/i, '').replace(/-/g, ' ').toUpperCase();
  });

  /** Empty Set — no pulsing in the static playground demo. */
  readonly pulsingSections = new Set<string>();

  // ── Methods ───────────────────────────────────────────────────────────────

  selectSection(id: string) {
    this.demoActiveSection.set(id);
  }

  selectProject(id: string) {
    const proj = this.demoProjects().find(p => p.id === id) ?? null;
    this.demoActiveProject.set(proj);
    this.demoActiveFile.set(proj?.specs[0]?.filename ?? null);
  }

  selectFile(filename: string) {
    this.demoActiveFile.set(filename);
  }

  closeExpanded() {
    this.demoActiveProject.set(null);
    this.demoActiveFile.set(null);
  }

  toggleTheme() {
    const next = this.isDark() ? 'light' : 'dark';
    this.isDark.set(next === 'dark');
    document.documentElement.setAttribute('data-theme', next);
    localStorage.setItem('theme', next);
  }

  teaserFn = (p: Project): string => {
    const sec = sectionFor(p, false);
    const specText = (s: any) => s?.content ?? s?.teaser ?? null;
    let leadContent: string | null = null;
    if (sec === 'Specced') {
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

  sectionFn = (p: Project): Section => sectionFor(p, false);

  onContextOpened(_key: string) {
    // No-op in playground — context files are not available in demo mode.
  }

  // ── Lifecycle ──────────────────────────────────────────────────────────────

  ngOnInit() {
    const saved = localStorage.getItem('theme') ?? 'light';
    this.isDark.set(saved === 'dark');
  }

  // Pre-select a project with rich content for the expanded panel demo
  preSelectDemoProject() {
    this.selectProject('demo-ready-1');
    this.demoActiveFile.set('analysis.md');
  }
}
