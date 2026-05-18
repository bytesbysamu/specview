import { TestBed } from '@angular/core/testing';
import { fakeAsync, tick, discardPeriodicTasks } from '@angular/core/testing';
import { HttpClientTestingModule } from '@angular/common/http/testing';
import { signal } from '@angular/core';
import { provideRouter } from '@angular/router';
import { Router } from '@angular/router';
import { NO_ERRORS_SCHEMA } from '@angular/core';

import { AppComponent } from './app.component';
import { ProjectsService, Project, AccessDeniedError } from './services/projects.service';
import { DemoAwareProjectsService } from './services/demo-aware-projects.service';
import { AiService } from './services/ai.service';
import { AuthService } from './services/auth.service';
import { createProjectsServiceMock } from './services/projects.service.mock';
import { createDemoAwareProjectsServiceMock } from './services/demo-aware-projects.service.mock';
import { createAiServiceMock } from './services/ai.service.mock';

describe('AppComponent', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [AppComponent, HttpClientTestingModule],
    }).compileComponents();
  });

  it('should create the app', () => {
    const fixture = TestBed.createComponent(AppComponent);
    const app = fixture.componentInstance;
    expect(app).toBeTruthy();
  });
});

describe('AppComponent — polling lifecycle', () => {
  let projectsMock: jasmine.SpyObj<ProjectsService>;
  let aiMock: jasmine.SpyObj<AiService>;

  beforeEach(async () => {
    projectsMock = createProjectsServiceMock();
    aiMock = createAiServiceMock();

    await TestBed.configureTestingModule({
      imports: [AppComponent, HttpClientTestingModule],
      providers: [
        { provide: ProjectsService, useValue: projectsMock },
        { provide: AiService, useValue: aiMock },
      ],
    }).compileComponents();
  });

  afterEach(() => {
    TestBed.resetTestingModule();
  });

  it('stops polling (pollTimer becomes null) when listProjects returns successfully on first call', fakeAsync(() => {
    projectsMock.listProjects.and.returnValue(Promise.resolve([]));

    const fixture = TestBed.createComponent(AppComponent);
    const component = fixture.componentInstance;

    // Manually start polling cycle
    component['pollRetries'] = 0;
    component['pollTimer'] = setInterval(async () => {
      await component.checkForUpdates();
    }, 2000);

    // Advance one interval — listProjects resolves with an empty list (no error)
    tick(2000);

    // checkForUpdates is async; flush microtask queue
    tick(0);

    // With pollRetries = 1 (well under POLL_MAX_RETRIES = 30) timer is still running;
    // force it past the limit to verify stopPolling behaviour
    component['pollRetries'] = 31;
    tick(2000);
    tick(0);

    expect(component['pollTimer']).toBeNull();

    discardPeriodicTasks();
  }));

  it('sets pollingError signal after POLL_MAX_RETRIES retries', fakeAsync(() => {
    projectsMock.listProjects.and.returnValue(Promise.resolve([]));

    const fixture = TestBed.createComponent(AppComponent);
    const component = fixture.componentInstance;

    // Seed retry counter just at the threshold
    component['pollRetries'] = 30;

    // checkForUpdates increments to 31 which is > 30 → stops + sets error
    component.checkForUpdates();
    tick(0);

    expect(component.pollingError()).toBeTruthy();
    expect(component['pollTimer']).toBeNull();

    discardPeriodicTasks();
  }));

  it('clears pollTimer on ngOnDestroy', fakeAsync(() => {
    projectsMock.listProjects.and.returnValue(Promise.resolve([]));

    const fixture = TestBed.createComponent(AppComponent);
    const component = fixture.componentInstance;

    // Simulate an active poll timer
    component['pollTimer'] = setInterval(() => {}, 2000);

    fixture.destroy();

    expect(component['pollTimer']).toBeNull();

    discardPeriodicTasks();
  }));

  it('renders [data-test="polling-error"] when pollingError signal is set', fakeAsync(() => {
    projectsMock.listProjects.and.returnValue(Promise.resolve([]));

    const fixture = TestBed.createComponent(AppComponent);
    const component = fixture.componentInstance;

    // Auth must be logged in for the template to render the polling-error div
    const auth = TestBed.inject(AuthService);
    auth.isLoggedIn.set(true);

    // Trigger the error state
    component['pollRetries'] = 30;
    component.checkForUpdates();
    tick(0);

    fixture.detectChanges();

    const el = fixture.nativeElement as HTMLElement;
    const errorEl = el.querySelector('[data-test="polling-error"]');
    expect(errorEl).toBeTruthy();

    discardPeriodicTasks();
  }));
});

// ---------------------------------------------------------------------------
// Shared setup factory for the expanded coverage suites
// ---------------------------------------------------------------------------

function buildTestBed(
  projectsMock: jasmine.SpyObj<ProjectsService>,
  demoMock: jasmine.SpyObj<DemoAwareProjectsService>,
  aiMock: jasmine.SpyObj<AiService>,
) {
  return TestBed.configureTestingModule({
    imports: [AppComponent, HttpClientTestingModule],
    providers: [
      provideRouter([]),
      { provide: ProjectsService, useValue: projectsMock },
      { provide: DemoAwareProjectsService, useValue: demoMock },
      { provide: AiService, useValue: aiMock },
    ],
    schemas: [NO_ERRORS_SCHEMA],
  }).compileComponents();
}

// ---------------------------------------------------------------------------
// doLogin()
// ---------------------------------------------------------------------------

describe('AppComponent — doLogin()', () => {
  let projectsMock: jasmine.SpyObj<ProjectsService>;
  let demoMock: jasmine.SpyObj<DemoAwareProjectsService>;
  let aiMock: jasmine.SpyObj<AiService>;

  beforeEach(async () => {
    projectsMock = createProjectsServiceMock();
    demoMock = createDemoAwareProjectsServiceMock();
    aiMock = createAiServiceMock();
    await buildTestBed(projectsMock, demoMock, aiMock);
  });

  afterEach(() => TestBed.resetTestingModule());

  it('sets loginLoading to true during login, then hides form on success', fakeAsync(() => {
    const fixture = TestBed.createComponent(AppComponent);
    const component = fixture.componentInstance;

    const auth = TestBed.inject(AuthService);
    let loadingDuringCall = false;

    spyOn(auth, 'login').and.callFake(async () => {
      loadingDuringCall = component.loginLoading();
    });

    component.showLoginForm.set(true);
    component.doLogin('user@example.com', 'password123');
    tick(0);

    expect(loadingDuringCall).toBeTrue();
    expect(component.loginLoading()).toBeFalse();
    expect(component.showLoginForm()).toBeFalse();

    discardPeriodicTasks();
  }));

  it('sets loginError on failed login and leaves loginLoading false', fakeAsync(() => {
    const fixture = TestBed.createComponent(AppComponent);
    const component = fixture.componentInstance;

    const auth = TestBed.inject(AuthService);
    spyOn(auth, 'login').and.returnValue(Promise.reject({ error: { error: 'Invalid credentials' } }));

    component.showLoginForm.set(true);
    component.doLogin('bad@example.com', 'wrongpass');
    tick(0);

    expect(component.loginError()).toBe('Invalid credentials');
    expect(component.loginLoading()).toBeFalse();
    expect(component.showLoginForm()).toBeTrue();

    discardPeriodicTasks();
  }));
});

// ---------------------------------------------------------------------------
// toggleLoginForm()
// ---------------------------------------------------------------------------

describe('AppComponent — toggleLoginForm()', () => {
  let projectsMock: jasmine.SpyObj<ProjectsService>;
  let demoMock: jasmine.SpyObj<DemoAwareProjectsService>;
  let aiMock: jasmine.SpyObj<AiService>;

  beforeEach(async () => {
    projectsMock = createProjectsServiceMock();
    demoMock = createDemoAwareProjectsServiceMock();
    aiMock = createAiServiceMock();
    await buildTestBed(projectsMock, demoMock, aiMock);
  });

  afterEach(() => TestBed.resetTestingModule());

  it('toggles showLoginForm from false to true', fakeAsync(() => {
    const fixture = TestBed.createComponent(AppComponent);
    const component = fixture.componentInstance;
    expect(component.showLoginForm()).toBeFalse();

    component.toggleLoginForm();
    expect(component.showLoginForm()).toBeTrue();

    discardPeriodicTasks();
  }));

  it('toggles showLoginForm from true back to false', fakeAsync(() => {
    const fixture = TestBed.createComponent(AppComponent);
    const component = fixture.componentInstance;

    component.showLoginForm.set(true);
    component.toggleLoginForm();
    expect(component.showLoginForm()).toBeFalse();

    discardPeriodicTasks();
  }));
});

// ---------------------------------------------------------------------------
// loadProjects()
// ---------------------------------------------------------------------------

describe('AppComponent — loadProjects()', () => {
  let projectsMock: jasmine.SpyObj<ProjectsService>;
  let demoMock: jasmine.SpyObj<DemoAwareProjectsService>;
  let aiMock: jasmine.SpyObj<AiService>;

  beforeEach(async () => {
    projectsMock = createProjectsServiceMock();
    demoMock = createDemoAwareProjectsServiceMock();
    aiMock = createAiServiceMock();
    await buildTestBed(projectsMock, demoMock, aiMock);
  });

  afterEach(() => TestBed.resetTestingModule());

  it('populates projects signal with the list returned by demoSvc.getProjects()', fakeAsync(() => {
    const fakeProjects: Project[] = [
      { id: 'p1', name: 'Alpha', createdAt: '2026-01-01T00:00:00Z', specs: [] },
      { id: 'p2', name: 'Beta',  createdAt: '2026-01-02T00:00:00Z', specs: [] },
    ];
    demoMock.getProjects.and.returnValue(Promise.resolve(fakeProjects));

    const fixture = TestBed.createComponent(AppComponent);
    const component = fixture.componentInstance;

    component.loadProjects();
    tick(0);

    expect(component.projects()).toEqual(fakeProjects);

    discardPeriodicTasks();
  }));

  it('uses demoSvc.getProjects — not projectsSvc.listProjects directly', fakeAsync(() => {
    demoMock.getProjects.and.returnValue(Promise.resolve([]));

    const fixture = TestBed.createComponent(AppComponent);
    const component = fixture.componentInstance;

    component.loadProjects();
    tick(0);

    expect(demoMock.getProjects).toHaveBeenCalled();
    expect(projectsMock.listProjects).not.toHaveBeenCalled();

    discardPeriodicTasks();
  }));
});

// ---------------------------------------------------------------------------
// selectProject()
// ---------------------------------------------------------------------------

describe('AppComponent — selectProject()', () => {
  let projectsMock: jasmine.SpyObj<ProjectsService>;
  let demoMock: jasmine.SpyObj<DemoAwareProjectsService>;
  let aiMock: jasmine.SpyObj<AiService>;

  beforeEach(async () => {
    projectsMock = createProjectsServiceMock();
    demoMock = createDemoAwareProjectsServiceMock();
    aiMock = createAiServiceMock();
    await buildTestBed(projectsMock, demoMock, aiMock);
  });

  afterEach(() => TestBed.resetTestingModule());

  it('sets activeProject and activeFile from the project returned by demoSvc.getProject()', fakeAsync(() => {
    const fakeProject: Project = {
      id: 'proj-123',
      name: 'My Project',
      createdAt: '2026-01-01T00:00:00Z',
      specs: [
        { filename: 'braindump.md', label: 'Braindump' },
        { filename: 'analysis.md',  label: 'Analysis'  },
      ],
    };
    demoMock.getProject.and.returnValue(Promise.resolve(fakeProject));

    const fixture = TestBed.createComponent(AppComponent);
    const component = fixture.componentInstance;

    component.selectProject('proj-123');
    tick(0);

    expect(component.activeProject()).toEqual(fakeProject);
    expect(component.activeFile()).toBe('braindump.md');

    discardPeriodicTasks();
  }));

  it('sets accessDenied when demoSvc.getProject rejects with AccessDeniedError', fakeAsync(() => {
    demoMock.getProject.and.returnValue(Promise.reject(new AccessDeniedError()));

    const fixture = TestBed.createComponent(AppComponent);
    const component = fixture.componentInstance;

    component.selectProject('locked-project');
    tick(0);

    expect(component.accessDenied()).toBeTrue();
    expect(component.activeProject()).toBeNull();
    expect(component.activeFile()).toBeNull();

    discardPeriodicTasks();
  }));
});

// ---------------------------------------------------------------------------
// closeExpanded()
// ---------------------------------------------------------------------------

describe('AppComponent — closeExpanded()', () => {
  let projectsMock: jasmine.SpyObj<ProjectsService>;
  let demoMock: jasmine.SpyObj<DemoAwareProjectsService>;
  let aiMock: jasmine.SpyObj<AiService>;

  beforeEach(async () => {
    projectsMock = createProjectsServiceMock();
    demoMock = createDemoAwareProjectsServiceMock();
    aiMock = createAiServiceMock();
    await buildTestBed(projectsMock, demoMock, aiMock);
  });

  afterEach(() => TestBed.resetTestingModule());

  it('resets activeProject, activeFile, contextContent, and accessDenied to null/false', fakeAsync(() => {
    const fixture = TestBed.createComponent(AppComponent);
    const component = fixture.componentInstance;

    // Seed some state
    component.activeProject.set({ id: 'x', name: 'X', createdAt: '2026-01-01T00:00:00Z', specs: [] });
    component.activeFile.set('analysis.md');
    component.contextContent.set('some context');
    component.accessDenied.set(true);

    component.closeExpanded();

    expect(component.activeProject()).toBeNull();
    expect(component.activeFile()).toBeNull();
    expect(component.contextContent()).toBeNull();
    expect(component.accessDenied()).toBeFalse();

    discardPeriodicTasks();
  }));
});

// ---------------------------------------------------------------------------
// toggleTheme()
// ---------------------------------------------------------------------------

describe('AppComponent — toggleTheme()', () => {
  let projectsMock: jasmine.SpyObj<ProjectsService>;
  let demoMock: jasmine.SpyObj<DemoAwareProjectsService>;
  let aiMock: jasmine.SpyObj<AiService>;

  beforeEach(async () => {
    projectsMock = createProjectsServiceMock();
    demoMock = createDemoAwareProjectsServiceMock();
    aiMock = createAiServiceMock();
    await buildTestBed(projectsMock, demoMock, aiMock);
  });

  afterEach(() => TestBed.resetTestingModule());

  it('flips isDark from false to true', fakeAsync(() => {
    const fixture = TestBed.createComponent(AppComponent);
    const component = fixture.componentInstance;

    component.isDark.set(false);
    component.toggleTheme();

    expect(component.isDark()).toBeTrue();

    discardPeriodicTasks();
  }));

  it('flips isDark from true to false', fakeAsync(() => {
    const fixture = TestBed.createComponent(AppComponent);
    const component = fixture.componentInstance;

    component.isDark.set(true);
    component.toggleTheme();

    expect(component.isDark()).toBeFalse();

    discardPeriodicTasks();
  }));
});

// ---------------------------------------------------------------------------
// navigateToUpgrade()
// ---------------------------------------------------------------------------

describe('AppComponent — navigateToUpgrade()', () => {
  let projectsMock: jasmine.SpyObj<ProjectsService>;
  let demoMock: jasmine.SpyObj<DemoAwareProjectsService>;
  let aiMock: jasmine.SpyObj<AiService>;

  beforeEach(async () => {
    projectsMock = createProjectsServiceMock();
    demoMock = createDemoAwareProjectsServiceMock();
    aiMock = createAiServiceMock();
    await buildTestBed(projectsMock, demoMock, aiMock);
  });

  afterEach(() => TestBed.resetTestingModule());

  it('calls router.navigate with ["/upgrade"]', fakeAsync(() => {
    const fixture = TestBed.createComponent(AppComponent);
    const component = fixture.componentInstance;

    const router = TestBed.inject(Router);
    spyOn(router, 'navigate').and.returnValue(Promise.resolve(true));

    component.navigateToUpgrade();

    expect(router.navigate).toHaveBeenCalledWith(['/upgrade']);

    discardPeriodicTasks();
  }));
});

// ---------------------------------------------------------------------------
// isFullPageRoute signal
// ---------------------------------------------------------------------------

describe('AppComponent — isFullPageRoute signal', () => {
  let projectsMock: jasmine.SpyObj<ProjectsService>;
  let demoMock: jasmine.SpyObj<DemoAwareProjectsService>;
  let aiMock: jasmine.SpyObj<AiService>;

  async function buildWithUrl(url: string) {
    projectsMock = createProjectsServiceMock();
    demoMock = createDemoAwareProjectsServiceMock();
    aiMock = createAiServiceMock();

    await TestBed.configureTestingModule({
      imports: [AppComponent, HttpClientTestingModule],
      providers: [
        provideRouter([]),
        { provide: ProjectsService, useValue: projectsMock },
        { provide: DemoAwareProjectsService, useValue: demoMock },
        { provide: AiService, useValue: aiMock },
      ],
      schemas: [NO_ERRORS_SCHEMA],
    }).compileComponents();

    // Override the router URL before construction
    const router = TestBed.inject(Router);
    Object.defineProperty(router, 'url', { get: () => url, configurable: true });

    return TestBed.createComponent(AppComponent).componentInstance;
  }

  afterEach(() => TestBed.resetTestingModule());

  it('is true for /login', fakeAsync(async () => {
    const component = await buildWithUrl('/login');
    expect(component.isFullPageRoute()).toBeTrue();
    discardPeriodicTasks();
  }));

  it('is true for /signup', fakeAsync(async () => {
    const component = await buildWithUrl('/signup');
    expect(component.isFullPageRoute()).toBeTrue();
    discardPeriodicTasks();
  }));

  it('is true for /playground', fakeAsync(async () => {
    const component = await buildWithUrl('/playground');
    expect(component.isFullPageRoute()).toBeTrue();
    discardPeriodicTasks();
  }));

  it('is false for / (root path)', fakeAsync(async () => {
    const component = await buildWithUrl('/');
    expect(component.isFullPageRoute()).toBeFalse();
    discardPeriodicTasks();
  }));
});
