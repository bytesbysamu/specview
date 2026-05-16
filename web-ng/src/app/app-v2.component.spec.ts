import { TestBed } from '@angular/core/testing';
import { fakeAsync, tick, discardPeriodicTasks, flushMicrotasks } from '@angular/core/testing';
import { NO_ERRORS_SCHEMA, signal } from '@angular/core';
import { Router } from '@angular/router';
import { provideRouter } from '@angular/router';

import { AppV2Component } from './app-v2.component';
import { ProjectsService, Project, AccessDeniedError } from './services/projects.service';
import { AiService } from './services/ai.service';
import { AuthService } from './services/auth.service';
import { SubscriptionService } from './services/subscription.service';

import { createProjectsServiceMock } from './services/projects.service.mock';
import { createAiServiceMock } from './services/ai.service.mock';
import { createMockSubscriptionService } from './services/subscription.service.mock';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function makeProject(overrides: Partial<Project> = {}): Project {
  return {
    id: 'proj-1',
    name: 'Test Project',
    createdAt: '2024-01-01T00:00:00Z',
    specs: [],
    ...overrides,
  };
}

function makeSpec(filename: string, content = 'hello') {
  return { filename, label: filename.replace('.md', ''), content };
}

function makeAuthServiceMock(isLoggedIn = false): jasmine.SpyObj<AuthService> {
  const isLoggedInSignal = signal(isLoggedIn);
  const mock = jasmine.createSpyObj<AuthService>('AuthService', ['signOut', 'login', 'register', 'getStoredJwt']);
  Object.defineProperty(mock, 'isLoggedIn', { get: () => isLoggedInSignal, configurable: true });
  mock.signOut.and.callFake(() => { isLoggedInSignal.set(false); });
  return mock;
}


// ---------------------------------------------------------------------------
// TestBed factory — reused across all describe groups
// ---------------------------------------------------------------------------

async function buildTestBed(options: {
  isLoggedIn?: boolean;
  localStorageTheme?: string;
} = {}) {
  const projectsMock = createProjectsServiceMock();
  const aiMock = createAiServiceMock();
  const subscriptionMock = createMockSubscriptionService();
  const authMock = makeAuthServiceMock(options.isLoggedIn ?? false);

  // Spy on localStorage
  const localStorageGetSpy = spyOn(localStorage, 'getItem').and.callFake((key: string) => {
    if (key === 'theme') return options.localStorageTheme ?? 'light';
    return null;
  });
  const localStorageSetSpy = spyOn(localStorage, 'setItem').and.stub();

  await TestBed.configureTestingModule({
    imports: [AppV2Component],
    providers: [
      provideRouter([]),
      { provide: ProjectsService, useValue: projectsMock },
      { provide: AiService, useValue: aiMock },
      { provide: AuthService, useValue: authMock },
      { provide: SubscriptionService, useValue: subscriptionMock },
    ],
    schemas: [NO_ERRORS_SCHEMA],
  }).compileComponents();

  const routerMock = TestBed.inject(Router);

  return { projectsMock, aiMock, subscriptionMock, authMock, routerMock, localStorageGetSpy, localStorageSetSpy };
}

// ===========================================================================
// 1. Signal initialization
// ===========================================================================

describe('AppV2Component — signal initialization', () => {
  let component: AppV2Component;

  beforeEach(async () => {
    await buildTestBed({ localStorageTheme: 'light' });
    const fixture = TestBed.createComponent(AppV2Component);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  afterEach(() => TestBed.resetTestingModule());

  it('initializes projects as empty array', () => {
    expect(component.projects()).toEqual([]);
  });

  it('initializes activeSection as "all"', () => {
    expect(component.activeSection()).toBe('all');
  });

  it('initializes activeProject as null', () => {
    expect(component.activeProject()).toBeNull();
  });

  it('initializes activeFile as null', () => {
    expect(component.activeFile()).toBeNull();
  });

  it('initializes searchQuery as empty string', () => {
    expect(component.searchQuery()).toBe('');
  });

  it('initializes isDark as false when localStorage returns "light"', () => {
    expect(component.isDark()).toBeFalse();
  });

  it('initializes specGenLoading as false', () => {
    expect(component.specGenLoading()).toBeFalse();
  });

  it('initializes aiLoading as false', () => {
    expect(component.aiLoading()).toBeFalse();
  });

  it('initializes undoStack as empty object', () => {
    expect(component.undoStack()).toEqual({});
  });

  it('initializes polling as false', () => {
    expect(component.polling()).toBeFalse();
  });
});

// ===========================================================================
// 2. Computed derivations
// ===========================================================================

describe('AppV2Component — computed derivations', () => {
  let component: AppV2Component;

  beforeEach(async () => {
    await buildTestBed();
    const fixture = TestBed.createComponent(AppV2Component);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  afterEach(() => TestBed.resetTestingModule());

  it('filteredProjects returns all projects when section is "all" and search is empty', () => {
    const p1 = makeProject({ id: 'a', name: 'Alpha', specs: [] });
    const p2 = makeProject({ id: 'b', name: 'Beta', specs: [] });
    component.projects.set([p1, p2]);
    component.activeSection.set('all');
    component.searchQuery.set('');
    expect(component.filteredProjects().length).toBe(2);
  });

  it('filteredProjects filters by active section', () => {
    const braindump = makeProject({ id: 'b1', name: 'Dump', specs: [makeSpec('braindump.md')] });
    const specced = makeProject({ id: 's1', name: 'Specced', specs: [makeSpec('implementation-guide.md')] });
    component.projects.set([braindump, specced]);
    component.activeSection.set('Braindumps');
    expect(component.filteredProjects()).toEqual([braindump]);
  });

  it('filteredProjects filters by search query on project name', () => {
    const p1 = makeProject({ id: 'x1', name: 'Frontend App', specs: [] });
    const p2 = makeProject({ id: 'x2', name: 'Backend API', specs: [] });
    component.projects.set([p1, p2]);
    component.activeSection.set('all');
    component.searchQuery.set('frontend');
    expect(component.filteredProjects()).toEqual([p1]);
  });

  it('filteredProjects applies section filter and search simultaneously', () => {
    const braindumpFront = makeProject({ id: 'bf', name: 'Frontend Dump', specs: [makeSpec('braindump.md')] });
    const braindumpBack = makeProject({ id: 'bb', name: 'Backend Dump', specs: [makeSpec('braindump.md')] });
    const specced = makeProject({ id: 'ss', name: 'Frontend Specced', specs: [makeSpec('implementation-guide.md')] });
    component.projects.set([braindumpFront, braindumpBack, specced]);
    component.activeSection.set('Braindumps');
    component.searchQuery.set('frontend');
    expect(component.filteredProjects()).toEqual([braindumpFront]);
  });

  it('sectionCounts aggregates projects by section', () => {
    const p1 = makeProject({ id: 'c1', name: 'A', specs: [makeSpec('braindump.md')] });
    const p2 = makeProject({ id: 'c2', name: 'B', specs: [makeSpec('braindump.md')] });
    const p3 = makeProject({ id: 'c3', name: 'C', specs: [makeSpec('implementation-guide.md')] });
    component.projects.set([p1, p2, p3]);
    const counts = component.sectionCounts();
    expect(counts['Braindumps']).toBe(2);
    expect(counts['Specced']).toBe(1);
    expect(counts['all']).toBe(3);
  });

  it('columns distributes projects across at most 3 columns', () => {
    const projs = Array.from({ length: 6 }, (_, i) =>
      makeProject({ id: `p${i}`, name: `P${i}`, specs: [] })
    );
    component.projects.set(projs);
    component.activeSection.set('all');
    const cols = component.columns();
    expect(cols.length).toBeLessThanOrEqual(3);
    const total = cols.reduce((sum, col) => sum + col.length, 0);
    expect(total).toBe(6);
  });

  it('canRevert is false when undoStack has no entries for active file', () => {
    const proj = makeProject({ specs: [makeSpec('epic.md')] });
    component.activeProject.set(proj);
    component.activeFile.set('epic.md');
    component.undoStack.set({});
    expect(component.canRevert()).toBeFalse();
  });

  it('canRevert is true when undoStack has entries for active file', () => {
    const proj = makeProject({ id: 'undo-proj', specs: [makeSpec('epic.md')] });
    component.activeProject.set(proj);
    component.activeFile.set('epic.md');
    component.undoStack.set({ 'undo-proj/epic.md': ['old content'] });
    expect(component.canRevert()).toBeTrue();
  });

  it('showGrid is true when no active project and no context and no accessDenied', () => {
    component.activeProject.set(null);
    component.contextContent.set(null);
    component.accessDenied.set(false);
    expect(component.showGrid()).toBeTrue();
  });

  it('showExpanded is true when activeProject is set', () => {
    component.activeProject.set(makeProject());
    expect(component.showExpanded()).toBeTrue();
  });
});

// ===========================================================================
// 3. Method behavior
// ===========================================================================

describe('AppV2Component — method behavior', () => {
  let component: AppV2Component;
  let projectsMock: jasmine.SpyObj<ProjectsService>;
  let router: Router;
  let localStorageSetSpy: jasmine.Spy;

  beforeEach(async () => {
    const mocks = await buildTestBed();
    projectsMock = mocks.projectsMock;
    router = mocks.routerMock;
    localStorageSetSpy = mocks.localStorageSetSpy;
    const fixture = TestBed.createComponent(AppV2Component);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  afterEach(() => TestBed.resetTestingModule());

  it('selectProject sets activeProject from service response', async () => {
    const proj = makeProject({ id: 'sel-1', specs: [makeSpec('epic.md')] });
    projectsMock.getProject.and.returnValue(Promise.resolve(proj));
    await component.selectProject('sel-1');
    expect(component.activeProject()).toEqual(proj);
  });

  it('selectProject sets activeFile to first spec filename', async () => {
    const proj = makeProject({ id: 'sel-2', specs: [makeSpec('braindump.md'), makeSpec('epic.md')] });
    projectsMock.getProject.and.returnValue(Promise.resolve(proj));
    await component.selectProject('sel-2');
    expect(component.activeFile()).toBe('braindump.md');
  });

  it('selectProject sets accessDenied on AccessDeniedError', async () => {
    projectsMock.getProject.and.returnValue(Promise.reject(new AccessDeniedError()));
    await component.selectProject('denied-proj');
    expect(component.accessDenied()).toBeTrue();
    expect(component.activeProject()).toBeNull();
  });

  it('toggleTheme switches isDark from false to true', () => {
    component.isDark.set(false);
    component.toggleTheme();
    expect(component.isDark()).toBeTrue();
  });

  it('toggleTheme updates document.documentElement data-theme attribute', () => {
    component.isDark.set(false);
    component.toggleTheme();
    expect(document.documentElement.getAttribute('data-theme')).toBe('dark');
    // Restore
    document.documentElement.setAttribute('data-theme', 'light');
  });

  it('toggleTheme persists theme to localStorage', () => {
    component.isDark.set(false);
    component.toggleTheme();
    expect(localStorageSetSpy).toHaveBeenCalledWith('theme', 'dark');
  });

  it('applyResult pushes current content onto undoStack', () => {
    const proj = makeProject({ id: 'apply-proj', specs: [makeSpec('epic.md', 'original content')] });
    component.activeProject.set(proj);
    component.activeFile.set('epic.md');
    component.aiResult.set('new content');
    component.applyResult();
    expect(component.undoStack()['apply-proj/epic.md']).toContain('original content');
  });

  it('applyResult clears aiResult after applying', () => {
    const proj = makeProject({ id: 'apply-proj2', specs: [makeSpec('epic.md', 'orig')] });
    component.activeProject.set(proj);
    component.activeFile.set('epic.md');
    component.aiResult.set('new text');
    component.applyResult();
    expect(component.aiResult()).toBeNull();
  });

  it('applyResult clears the redo stack for the active file', () => {
    const proj = makeProject({ id: 'apply-proj3', specs: [makeSpec('epic.md', 'orig')] });
    component.activeProject.set(proj);
    component.activeFile.set('epic.md');
    component.redoStack.set({ 'apply-proj3/epic.md': ['stale'] });
    component.aiResult.set('new text');
    component.applyResult();
    expect(component.redoStack()['apply-proj3/epic.md']).toEqual([]);
  });

  it('undoVersion pops the last undo entry and restores it to the active spec', () => {
    const proj = makeProject({ id: 'undo-p', specs: [makeSpec('epic.md', 'current')] });
    component.activeProject.set(proj);
    component.activeFile.set('epic.md');
    component.undoStack.set({ 'undo-p/epic.md': ['original'] });
    component.undoVersion();
    const updatedSpec = component.activeProject()!.specs.find(s => s.filename === 'epic.md');
    expect(updatedSpec?.content).toBe('original');
  });

  it('redoVersion restores the last redo entry', () => {
    const proj = makeProject({ id: 'redo-p', specs: [makeSpec('epic.md', 'current')] });
    component.activeProject.set(proj);
    component.activeFile.set('epic.md');
    component.redoStack.set({ 'redo-p/epic.md': ['newer'] });
    component.redoVersion();
    const updatedSpec = component.activeProject()!.specs.find(s => s.filename === 'epic.md');
    expect(updatedSpec?.content).toBe('newer');
  });

  it('onSearch sets searchQuery signal', () => {
    component.onSearch('angular');
    expect(component.searchQuery()).toBe('angular');
  });

  it('selectSection resets searchQuery', () => {
    component.searchQuery.set('hello');
    component.selectSection('Specced');
    expect(component.searchQuery()).toBe('');
  });

  it('selectSection sets activeSection', () => {
    component.selectSection('Braindumps');
    expect(component.activeSection()).toBe('Braindumps');
  });

  it('closeExpanded resets activeProject, activeFile, contextContent, and accessDenied', () => {
    component.activeProject.set(makeProject());
    component.activeFile.set('epic.md');
    component.contextContent.set('some content');
    component.accessDenied.set(true);
    component.closeExpanded();
    expect(component.activeProject()).toBeNull();
    expect(component.activeFile()).toBeNull();
    expect(component.contextContent()).toBeNull();
    expect(component.accessDenied()).toBeFalse();
  });

  it('navigateToUpgrade delegates to Router.navigate', () => {
    const navigateSpy = spyOn(router, 'navigate').and.returnValue(Promise.resolve(true));
    component.navigateToUpgrade();
    expect(navigateSpy).toHaveBeenCalledWith(['/upgrade']);
  });

  it('selectFile sets activeFile and clears aiResult', () => {
    component.aiResult.set('some result');
    component.selectFile('architecture.md');
    expect(component.activeFile()).toBe('architecture.md');
    expect(component.aiResult()).toBeNull();
  });
});

// ===========================================================================
// 4. Polling lifecycle
// ===========================================================================

describe('AppV2Component — polling lifecycle', () => {
  let component: AppV2Component;
  let projectsMock: jasmine.SpyObj<ProjectsService>;

  beforeEach(async () => {
    const mocks = await buildTestBed();
    projectsMock = mocks.projectsMock;
    const fixture = TestBed.createComponent(AppV2Component);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  afterEach(() => {
    TestBed.resetTestingModule();
  });

  it('checkForUpdates sets polling to true during a pending request', fakeAsync(() => {
    let resolveList!: (v: Project[]) => void;
    projectsMock.listProjects.and.returnValue(new Promise(r => { resolveList = r; }));

    component.checkForUpdates();
    tick(0);
    expect(component.polling()).toBeTrue();

    resolveList([]);
    tick(1000); // flush the 700ms setTimeout inside checkForUpdates
    discardPeriodicTasks();
  }));

  it('checkForUpdates stops polling and sets pollingError after POLL_MAX_RETRIES', fakeAsync(() => {
    projectsMock.listProjects.and.returnValue(Promise.resolve([]));
    component['pollRetries'] = 30;
    component.checkForUpdates();
    tick(0);
    expect(component.pollingError()).toBeTruthy();
    expect(component['pollTimer']).toBeNull();
    discardPeriodicTasks();
  }));

  it('pollTimer is null after ngOnDestroy clears it', fakeAsync(() => {
    component['pollTimer'] = setInterval(() => {}, 5000);
    TestBed.createComponent(AppV2Component).destroy();
    discardPeriodicTasks();
    // The component under test
    component.ngOnDestroy();
    expect(component['pollTimer']).toBeNull();
  }));

  it('pollOk is set to false when listProjects rejects', fakeAsync(() => {
    projectsMock.listProjects.and.returnValue(Promise.reject(new Error('network error')));
    component.checkForUpdates();
    flushMicrotasks();
    tick(1000);
    expect(component.pollOk()).toBeFalse();
    discardPeriodicTasks();
  }));

  it('checkForUpdates updates knownCount when project count changes', fakeAsync(() => {
    const initial = [makeProject({ id: 'p0', name: 'P0', specs: [] })];
    component.projects.set(initial);
    component.knownCount.set(1);

    const fresh = [
      makeProject({ id: 'p0', name: 'P0', specs: [] }),
      makeProject({ id: 'p1', name: 'P1', specs: [] }),
    ];
    projectsMock.listProjects.and.returnValue(Promise.resolve(fresh));

    component.checkForUpdates();
    tick(1000);

    expect(component.knownCount()).toBe(2);
    discardPeriodicTasks();
  }));
});

// ===========================================================================
// 5. Bootstrap pipeline (_runBootstrap)
// ===========================================================================

describe('AppV2Component — bootstrap pipeline', () => {
  let component: AppV2Component;
  let projectsMock: jasmine.SpyObj<ProjectsService>;

  beforeEach(async () => {
    const mocks = await buildTestBed();
    projectsMock = mocks.projectsMock;
    const fixture = TestBed.createComponent(AppV2Component);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  afterEach(() => {
    TestBed.resetTestingModule();
  });

  it('generateFromBraindump sets specGenLoading to true during generation', fakeAsync(() => {
    const proj = makeProject({ id: 'boot-1', specs: [makeSpec('braindump.md', 'my idea')] });
    component.activeProject.set(proj);

    // startBootstrap resolves, then pollBootstrap never resolves (stuck)
    projectsMock.startBootstrap.and.returnValue(Promise.resolve({ job_id: 'job-abc' }));
    projectsMock.pollBootstrap.and.returnValue(new Promise(() => {}));

    component.generateFromBraindump();
    tick(0);

    expect(component.specGenLoading()).toBeTrue();
    discardPeriodicTasks();
  }));

  it('generateFromBraindump sets specGenJobId from startBootstrap response', fakeAsync(() => {
    const proj = makeProject({ id: 'boot-2', specs: [makeSpec('braindump.md', 'idea')] });
    component.activeProject.set(proj);

    projectsMock.startBootstrap.and.returnValue(Promise.resolve({ job_id: 'job-xyz' }));
    projectsMock.pollBootstrap.and.returnValue(new Promise(() => {}));

    component.generateFromBraindump();
    tick(0);
    flushMicrotasks();

    expect(component.specGenJobId()).toBe('job-xyz');
    discardPeriodicTasks();
  }));

  it('generateFromBraindump sets specGenError when bootstrap rejects', fakeAsync(() => {
    const proj = makeProject({ id: 'boot-3', specs: [makeSpec('braindump.md', 'idea')] });
    component.activeProject.set(proj);

    projectsMock.startBootstrap.and.returnValue(Promise.reject(new Error('server down')));

    component.generateFromBraindump();
    tick(10000); // advance past the retry logic
    flushMicrotasks();

    expect(component.specGenError()).toBeTruthy();
    discardPeriodicTasks();
  }));

  it('generateFromBraindump resets specGenLoading to false after completion', fakeAsync(() => {
    const finalProj = makeProject({ id: 'boot-4', specs: [makeSpec('analysis.md', 'done')] });
    const proj = makeProject({ id: 'boot-4', specs: [makeSpec('braindump.md', 'idea')] });
    component.activeProject.set(proj);

    projectsMock.startBootstrap.and.returnValue(Promise.resolve({ job_id: 'j1' }));
    projectsMock.pollBootstrap.and.returnValue(Promise.resolve({
      running: false,
      done: true,
      current_step: null,
      files: [{ filename: 'analysis.md', content: 'done' }],
    }));
    projectsMock.saveFile.and.returnValue(Promise.resolve());
    projectsMock.getProject.and.returnValue(Promise.resolve(finalProj));

    component.generateFromBraindump();
    tick(10000);
    flushMicrotasks();
    tick(5000);
    flushMicrotasks();

    expect(component.specGenLoading()).toBeFalse();
    discardPeriodicTasks();
  }));

  it('createProject sets specGenProjectName during generation', fakeAsync(() => {
    projectsMock.createProject.and.returnValue(Promise.resolve(makeProject({ id: 'new-p' })));
    projectsMock.listProjects.and.returnValue(Promise.resolve([]));
    projectsMock.getProject.and.returnValue(new Promise(() => {}));
    projectsMock.startBootstrap.and.returnValue(new Promise(() => {}));

    const nameEl = { value: 'New Project' } as HTMLInputElement;
    const braindumpEl = { value: 'my braindump' } as HTMLTextAreaElement;

    component.createProject(nameEl, braindumpEl);
    tick(0);
    flushMicrotasks();

    expect(component.specGenLoading()).toBeTrue();
    discardPeriodicTasks();
  }));

  it('specGenStep is updated when pollBootstrap returns current_step', fakeAsync(() => {
    const proj = makeProject({ id: 'step-proj', specs: [makeSpec('braindump.md', 'idea')] });
    component.activeProject.set(proj);

    let pollCallCount = 0;
    projectsMock.startBootstrap.and.returnValue(Promise.resolve({ job_id: 'step-job' }));
    projectsMock.pollBootstrap.and.callFake(() => {
      pollCallCount++;
      if (pollCallCount === 1) {
        return Promise.resolve({
          running: true,
          done: false,
          current_step: 'analysis',
          files: [],
        });
      }
      return new Promise(() => {});
    });

    component.generateFromBraindump();
    tick(5000);
    flushMicrotasks();

    expect(component.specGenStep()).toBe('analysis');
    discardPeriodicTasks();
  }));

  it('specGenFailedStep is set when pollBootstrap returns failed_step', fakeAsync(() => {
    const proj = makeProject({ id: 'fail-proj', specs: [makeSpec('braindump.md', 'idea')] });
    component.activeProject.set(proj);

    projectsMock.startBootstrap.and.returnValue(Promise.resolve({ job_id: 'fail-job' }));
    projectsMock.pollBootstrap.and.returnValue(Promise.resolve({
      running: false,
      done: true,
      current_step: null,
      failed_step: 'epic',
      error: 'Epic generation failed',
      files: [],
    }));

    component.generateFromBraindump();
    tick(10000);
    flushMicrotasks();
    tick(5000);
    flushMicrotasks();

    expect(component.specGenFailedStep()).toBe('epic');
    discardPeriodicTasks();
  }));

  it('generateFromBraindump does not run when specGenLoading is already true', fakeAsync(() => {
    component.specGenLoading.set(true);
    const proj = makeProject({ id: 'busy-proj', specs: [makeSpec('braindump.md', 'idea')] });
    component.activeProject.set(proj);

    component.generateFromBraindump();
    tick(0);

    expect(projectsMock.startBootstrap).not.toHaveBeenCalled();
    discardPeriodicTasks();
  }));
});

// ===========================================================================
// 6. Basic behavior — service injection, conditional rendering (logged out)
// ===========================================================================

describe('AppV2Component — basic behavior', () => {
  let component: AppV2Component;
  let fixture: ReturnType<typeof TestBed.createComponent<AppV2Component>>;
  let projectsMock: jasmine.SpyObj<ProjectsService>;
  let aiMock: jasmine.SpyObj<AiService>;
  let subscriptionMock: jasmine.SpyObj<SubscriptionService>;
  let authMock: jasmine.SpyObj<AuthService>;
  let routerMock: Router;

  beforeEach(async () => {
    const mocks = await buildTestBed({ isLoggedIn: false });
    projectsMock = mocks.projectsMock;
    aiMock = mocks.aiMock;
    subscriptionMock = mocks.subscriptionMock;
    authMock = mocks.authMock;
    routerMock = mocks.routerMock;

    fixture = TestBed.createComponent(AppV2Component);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  afterEach(() => TestBed.resetTestingModule());

  // ── Service injection verification ──────────────────────────────────────

  it('injects ProjectsService and the instance matches the mock', () => {
    const injected = TestBed.inject(ProjectsService);
    expect(injected).toBeDefined();
    expect(injected).toBe(projectsMock);
  });

  it('injects AiService and the instance matches the mock', () => {
    const injected = TestBed.inject(AiService);
    expect(injected).toBeDefined();
    expect(injected).toBe(aiMock);
  });

  it('injects AuthService and the instance matches the mock', () => {
    const injected = TestBed.inject(AuthService);
    expect(injected).toBeDefined();
    expect(injected).toBe(authMock);
  });

  it('injects SubscriptionService and the instance matches the mock', () => {
    const injected = TestBed.inject(SubscriptionService);
    expect(injected).toBeDefined();
    expect(injected).toBe(subscriptionMock);
  });

  it('injects Router and the instance is defined', () => {
    const injected = TestBed.inject(Router);
    expect(injected).toBeDefined();
    expect(injected).toBe(routerMock);
  });

  // ── Conditional rendering (logged-out state) ─────────────────────────────

  it('renders landing-pitch when user is not logged in', () => {
    fixture.detectChanges();
    const landingPitch = fixture.debugElement.nativeElement.querySelector('app-landing-pitch');
    expect(landingPitch).toBeTruthy();
  });

  it('hides workspace shell when user is not logged in', () => {
    fixture.detectChanges();
    const shell = fixture.debugElement.nativeElement.querySelector('.v2-shell');
    expect(shell).toBeNull();
  });

  // ── Navigation delegation ────────────────────────────────────────────────

  it('navigateToUpgrade calls router.navigate with /upgrade', () => {
    const navigateSpy = spyOn(routerMock, 'navigate').and.returnValue(Promise.resolve(true));
    component.navigateToUpgrade();
    expect(navigateSpy).toHaveBeenCalledWith(['/upgrade']);
  });

  it('selectFile sets activeFile to the chosen filename', () => {
    component.selectFile('architecture.md');
    expect(component.activeFile()).toBe('architecture.md');
  });

  it('selectFile clears aiResult when switching files', () => {
    component.aiResult.set('previous result');
    component.selectFile('timeline.md');
    expect(component.aiResult()).toBeNull();
  });

  it('selectProject navigates into the project by setting activeProject', async () => {
    const proj = makeProject({ id: 'nav-proj', specs: [makeSpec('analysis.md'), makeSpec('epic.md')] });
    projectsMock.getProject.and.returnValue(Promise.resolve(proj));
    await component.selectProject('nav-proj');
    expect(component.activeProject()).toEqual(proj);
    expect(component.activeFile()).toBe('analysis.md');
  });

  it('closeExpanded navigates back to grid by clearing activeProject and activeFile', () => {
    component.activeProject.set(makeProject({ id: 'back-proj', specs: [] }));
    component.activeFile.set('epic.md');
    component.closeExpanded();
    expect(component.activeProject()).toBeNull();
    expect(component.activeFile()).toBeNull();
  });
});

// ===========================================================================
// 6b. Basic behavior — conditional rendering (logged-in state)
// ===========================================================================

describe('AppV2Component — basic behavior (logged in)', () => {
  let component: AppV2Component;
  let fixture: ReturnType<typeof TestBed.createComponent<AppV2Component>>;
  let projectsMock: jasmine.SpyObj<ProjectsService>;

  beforeEach(async () => {
    const mocks = await buildTestBed({ isLoggedIn: true });
    projectsMock = mocks.projectsMock;
    // Stub listProjects so the effect-driven loadProjects resolves immediately
    // and does not leave any pending promise chains that block detectChanges.
    projectsMock.listProjects.and.returnValue(Promise.resolve([]));

    fixture = TestBed.createComponent(AppV2Component);
    component = fixture.componentInstance;
    // First detectChanges triggers the isLoggedIn effect → loadProjects().
    fixture.detectChanges();
  });

  afterEach(() => TestBed.resetTestingModule());

  it('shows workspace shell when user is logged in', () => {
    const shell = fixture.debugElement.nativeElement.querySelector('.v2-shell');
    expect(shell).toBeTruthy();
  });

  it('renders project grid when showGrid is true (no active project)', () => {
    component.activeProject.set(null);
    component.contextContent.set(null);
    component.accessDenied.set(false);
    fixture.detectChanges();
    const grid = fixture.debugElement.nativeElement.querySelector('app-project-grid');
    expect(grid).toBeTruthy();
  });

  it('hides project grid and shows expanded panel when activeProject is set', () => {
    component.activeProject.set(makeProject({ id: 'view-proj', specs: [makeSpec('epic.md')] }));
    fixture.detectChanges();
    const grid = fixture.debugElement.nativeElement.querySelector('app-project-grid');
    const expanded = fixture.debugElement.nativeElement.querySelector('.expanded-panel');
    expect(grid).toBeNull();
    expect(expanded).toBeTruthy();
  });

  it('shows masthead title element in the workspace', () => {
    const title = fixture.debugElement.nativeElement.querySelector('[data-test="masthead-title"]');
    expect(title).toBeTruthy();
    expect(title.textContent.trim()).toBe('Specview');
  });

  it('renders pollingError banner when pollingError signal is set', () => {
    component.pollingError.set('Too many retries — refresh to resume.');
    fixture.detectChanges();
    const errorEl = fixture.debugElement.nativeElement.querySelector('[data-test="polling-error"]');
    expect(errorEl).toBeTruthy();
    expect(errorEl.textContent).toContain('Too many retries');
  });
});
