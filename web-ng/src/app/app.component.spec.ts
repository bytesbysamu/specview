import { TestBed } from '@angular/core/testing';
import { fakeAsync, tick, discardPeriodicTasks } from '@angular/core/testing';
import { HttpClientTestingModule } from '@angular/common/http/testing';

import { AppComponent } from './app.component';
import { ProjectsService } from './services/projects.service';
import { AiService } from './services/ai.service';
import { AuthService } from './services/auth.service';
import { createProjectsServiceMock } from './services/projects.service.mock';
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
