import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NO_ERRORS_SCHEMA } from '@angular/core';
import { provideRouter } from '@angular/router';
import { LivePlaygroundComponent } from './live-playground.component';
import { DEMO_PROJECTS, DEMO_NAV_SECTIONS } from './playground-demo-data';
import { Project } from './services/projects.service';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function makeProject(overrides: Partial<Project> = {}): Project {
  return {
    id: 'test-proj-1',
    name: 'Test Project',
    createdAt: '2026-05-01T00:00:00Z',
    specs: [
      { filename: 'braindump.md', label: 'Braindump', teaser: 'A test braindump' },
    ],
    ...overrides,
  };
}

describe('LivePlaygroundComponent', () => {
  let component: LivePlaygroundComponent;
  let fixture: ComponentFixture<LivePlaygroundComponent>;
  let el: HTMLElement;

  beforeEach(async () => {
    // Suppress localStorage reads in ngOnInit
    spyOn(localStorage, 'getItem').and.returnValue('light');
    spyOn(localStorage, 'setItem').and.stub();

    await TestBed.configureTestingModule({
      imports: [LivePlaygroundComponent],
      providers: [provideRouter([])],
      schemas: [NO_ERRORS_SCHEMA],
    }).compileComponents();

    fixture = TestBed.createComponent(LivePlaygroundComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
    el = fixture.nativeElement;
  });

  afterEach(() => {
    // Reset data-theme to avoid cross-test contamination
    document.documentElement.removeAttribute('data-theme');
    fixture.destroy();
  });

  // ── Creation ────────────────────────────────────────────────────────────────

  it('creates the component', () => {
    expect(component).toBeTruthy();
  });

  // ── Initial signal state ─────────────────────────────────────────────────────

  it('initialises demoActiveSection to "all"', () => {
    expect(component.demoActiveSection()).toBe('all');
  });

  it('initialises demoActiveProject to null', () => {
    expect(component.demoActiveProject()).toBeNull();
  });

  it('initialises demoActiveFile to null', () => {
    expect(component.demoActiveFile()).toBeNull();
  });

  it('initialises demoProjects with the DEMO_PROJECTS dataset', () => {
    expect(component.demoProjects()).toEqual(DEMO_PROJECTS);
  });

  it('initialises isDark to false when localStorage returns "light"', () => {
    expect(component.isDark()).toBeFalse();
  });

  // ── Signal computation: demoSectionCounts ────────────────────────────────────

  it('demoSectionCounts includes "all" key covering all demo projects', () => {
    const counts = component.demoSectionCounts();
    expect(counts['all']).toBe(DEMO_PROJECTS.length);
  });

  it('demoSectionCounts has a positive count for "Ready to build"', () => {
    const counts = component.demoSectionCounts();
    expect(counts['Ready to build']).toBeGreaterThan(0);
  });

  it('demoSectionCounts has a positive count for "Specced"', () => {
    const counts = component.demoSectionCounts();
    expect(counts['Specced']).toBeGreaterThan(0);
  });

  it('demoSectionCounts updates when demoProjects signal changes', () => {
    const singleProject = makeProject({
      id: 'solo',
      specs: [
        { filename: 'braindump.md', label: 'Braindump', teaser: 'Solo project' },
      ],
    });
    component.demoProjects.set([singleProject]);
    fixture.detectChanges();

    const counts = component.demoSectionCounts();
    expect(counts['all']).toBe(1);
  });

  // ── Signal computation: demoFilteredProjects ─────────────────────────────────

  it('demoFilteredProjects returns all projects when section is "all"', () => {
    component.demoActiveSection.set('all');
    fixture.detectChanges();
    expect(component.demoFilteredProjects().length).toBe(DEMO_PROJECTS.length);
  });

  it('demoFilteredProjects returns only Braindumps projects when section is "Braindumps"', () => {
    component.demoActiveSection.set('Braindumps');
    fixture.detectChanges();
    const filtered = component.demoFilteredProjects();
    expect(filtered.length).toBeGreaterThan(0);
    filtered.forEach(p => {
      const hasGuide = p.specs.some(s => s.filename === 'implementation-guide.md');
      const hasArch = p.specs.some(s => s.filename === 'architecture.md');
      const hasEpic = p.specs.some(s => s.filename === 'epic.md');
      expect(hasGuide).toBeFalse();
      expect(hasArch || hasEpic).toBeFalse();
    });
  });

  it('demoFilteredProjects returns only Specced projects when section is "Specced"', () => {
    component.demoActiveSection.set('Specced');
    fixture.detectChanges();
    const filtered = component.demoFilteredProjects();
    expect(filtered.length).toBeGreaterThan(0);
    filtered.forEach(p => {
      const hasGuide = p.specs.some(s => s.filename === 'implementation-guide.md');
      expect(hasGuide).toBeTrue();
    });
  });

  // ── Signal computation: demoColumns ──────────────────────────────────────────

  it('demoColumns returns at least one column', () => {
    const cols = component.demoColumns();
    expect(cols.length).toBeGreaterThanOrEqual(1);
  });

  it('demoColumns returns at most 3 columns', () => {
    const cols = component.demoColumns();
    expect(cols.length).toBeLessThanOrEqual(3);
  });

  it('demoColumns distributes all filtered projects across columns', () => {
    const cols = component.demoColumns();
    const total = cols.reduce((sum, col) => sum + col.length, 0);
    expect(total).toBe(component.demoFilteredProjects().length);
  });

  it('demoColumns returns 1 column when only one project is in the filtered set', () => {
    const single = makeProject({ id: 'only', specs: [{ filename: 'braindump.md', label: 'Braindump', teaser: 'x' }] });
    component.demoProjects.set([single]);
    component.demoActiveSection.set('all');
    fixture.detectChanges();
    expect(component.demoColumns().length).toBe(1);
  });

  // ── User interaction: selectSection ─────────────────────────────────────────

  it('selectSection updates the demoActiveSection signal', () => {
    component.selectSection('Specced');
    expect(component.demoActiveSection()).toBe('Specced');
  });

  // ── User interaction: selectProject ─────────────────────────────────────────

  it('selectProject sets demoActiveProject to the matching project', () => {
    component.selectProject('demo-ready-1');
    expect(component.demoActiveProject()).not.toBeNull();
    expect(component.demoActiveProject()!.id).toBe('demo-ready-1');
  });

  it('selectProject sets demoActiveFile to the first spec filename', () => {
    component.selectProject('demo-ready-1');
    const firstFile = DEMO_PROJECTS.find(p => p.id === 'demo-ready-1')!.specs[0].filename;
    expect(component.demoActiveFile()).toBe(firstFile);
  });

  it('selectProject with unknown id sets demoActiveProject to null', () => {
    component.selectProject('nonexistent-id');
    expect(component.demoActiveProject()).toBeNull();
  });

  // ── User interaction: selectFile ─────────────────────────────────────────────

  it('selectFile updates the demoActiveFile signal', () => {
    component.selectProject('demo-ready-1');
    component.selectFile('epic.md');
    expect(component.demoActiveFile()).toBe('epic.md');
  });

  // ── User interaction: closeExpanded ─────────────────────────────────────────

  it('closeExpanded resets demoActiveProject to null', () => {
    component.selectProject('demo-ready-1');
    component.closeExpanded();
    expect(component.demoActiveProject()).toBeNull();
  });

  it('closeExpanded resets demoActiveFile to null', () => {
    component.selectProject('demo-ready-1');
    component.closeExpanded();
    expect(component.demoActiveFile()).toBeNull();
  });

  // ── Computed: demoCurrentSpec ────────────────────────────────────────────────

  it('demoCurrentSpec returns null when no project is selected', () => {
    expect(component.demoCurrentSpec()).toBeNull();
  });

  it('demoCurrentSpec returns the spec matching the active file', () => {
    component.selectProject('demo-ready-1');
    component.selectFile('analysis.md');
    const spec = component.demoCurrentSpec();
    expect(spec).not.toBeNull();
    expect(spec!.filename).toBe('analysis.md');
  });

  // ── Computed: demoSectionLabel ───────────────────────────────────────────────

  it('demoSectionLabel returns "All" when section is "all"', () => {
    component.demoActiveSection.set('all');
    expect(component.demoSectionLabel()).toBe('All');
  });

  it('demoSectionLabel returns "Specced" when section is "Specced"', () => {
    component.demoActiveSection.set('Specced');
    expect(component.demoSectionLabel()).toBe('Specced');
  });

  // ── Dark mode toggle ─────────────────────────────────────────────────────────

  it('toggleTheme sets isDark to true when currently light', () => {
    component.isDark.set(false);
    component.toggleTheme();
    expect(component.isDark()).toBeTrue();
  });

  it('toggleTheme sets isDark to false when currently dark', () => {
    component.isDark.set(true);
    component.toggleTheme();
    expect(component.isDark()).toBeFalse();
  });

  it('toggleTheme sets data-theme attribute to "dark" on document.documentElement', () => {
    component.isDark.set(false);
    component.toggleTheme();
    expect(document.documentElement.getAttribute('data-theme')).toBe('dark');
  });

  it('toggleTheme sets data-theme attribute to "light" when toggling back', () => {
    component.isDark.set(true);
    component.toggleTheme();
    expect(document.documentElement.getAttribute('data-theme')).toBe('light');
  });

  it('toggleTheme persists the theme to localStorage', () => {
    component.isDark.set(false);
    component.toggleTheme();
    expect(localStorage.setItem).toHaveBeenCalledWith('theme', 'dark');
  });

  // ── Shallow composition — child component stubs rendered ─────────────────────

  it('renders the pg-page root element', () => {
    const root = el.querySelector('.pg-page');
    expect(root).toBeTruthy();
  });

  it('renders pg-section elements for all playground sections', () => {
    const sections = el.querySelectorAll('.pg-section');
    expect(sections.length).toBeGreaterThanOrEqual(6);
  });

  it('renders a theme toggle button that shows the current mode', () => {
    component.isDark.set(false);
    fixture.detectChanges();
    const btn = el.querySelector('.pg-btn');
    expect(btn).toBeTruthy();
  });

  // ── preSelectDemoProject ─────────────────────────────────────────────────────

  it('preSelectDemoProject selects the demo-ready-1 project', () => {
    component.preSelectDemoProject();
    expect(component.demoActiveProject()!.id).toBe('demo-ready-1');
  });

  it('preSelectDemoProject sets the active file to analysis.md', () => {
    component.preSelectDemoProject();
    expect(component.demoActiveFile()).toBe('analysis.md');
  });

  // ── Exposed constants ────────────────────────────────────────────────────────

  it('exposes demoNavSections matching DEMO_NAV_SECTIONS', () => {
    expect(component.demoNavSections).toBe(DEMO_NAV_SECTIONS);
  });

  it('pulsingSections is an empty Set', () => {
    expect(component.pulsingSections.size).toBe(0);
  });
});
