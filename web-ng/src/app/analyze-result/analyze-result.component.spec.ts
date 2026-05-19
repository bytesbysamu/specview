import { ComponentFixture, TestBed, fakeAsync, tick } from '@angular/core/testing';
import { DomSanitizer } from '@angular/platform-browser';

import { AnalyzeResultComponent } from './analyze-result.component';
import { LandingHandoffService, BootstrapJobStatus } from '../landing-handoff.service';
import { createMockLandingHandoffService } from '../landing-handoff.service.mock';

const POLL_INTERVAL_MS = 3000;

const RUNNING_STATUS: BootstrapJobStatus = {
  running: true,
  done: false,
  current_step: 'analysis',
  partial_files: [],
};

const DONE_STATUS: BootstrapJobStatus = {
  running: false,
  done: true,
  files: [
    { filename: 'analysis.md', content: '# Analysis' },
    { filename: 'epic.md', content: '# Epic' },
  ],
  partial_files: [],
};

const ERROR_STATUS: BootstrapJobStatus = {
  running: false,
  done: true,
  error: 'Chain provider failed.',
  files: [],
  partial_files: [],
};

describe('AnalyzeResultComponent', () => {
  let fixture: ComponentFixture<AnalyzeResultComponent>;
  let component: AnalyzeResultComponent;
  let mockSvc: jasmine.SpyObj<LandingHandoffService>;

  function setup(braindump: string | null = 'Build a todo app') {
    mockSvc = createMockLandingHandoffService(
      braindump !== null
        ? { mode: 'real', braindump }
        : { mode: 'none' }
    );

    TestBed.configureTestingModule({
      imports: [AnalyzeResultComponent],
      providers: [
        { provide: LandingHandoffService, useValue: mockSvc },
        {
          provide: DomSanitizer,
          useValue: {
            bypassSecurityTrustHtml: (html: string) => html,
            sanitize: (_ctx: unknown, val: string) => val,
          },
        },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(AnalyzeResultComponent);
    component = fixture.componentInstance;
  }

  afterEach(() => {
    // Ensure any lingering interval is stopped so fakeAsync does not complain
    // about pending timers after the test.
    component.ngOnDestroy();
    TestBed.resetTestingModule();
  });

  // ── Smoke test ─────────────────────────────────────────────────────────────

  it('creates the component without errors', () => {
    setup(null);
    fixture.detectChanges();
    expect(component).toBeTruthy();
  });

  it('sets fatalError when handoff mode is not real', () => {
    setup(null);
    fixture.detectChanges();
    expect(component.fatalError()).toContain('No braindump found');
    expect(mockSvc.startAnonymousBootstrap).not.toHaveBeenCalled();
  });

  // ── Polling: clearInterval called on completion ─────────────────────────────

  it('calls clearInterval when polling completes (done=true)', fakeAsync(() => {
    setup('Build a todo app');

    mockSvc.startAnonymousBootstrap.and.resolveTo({ job_id: 'job-123' });
    // First poll returns running, second returns done
    mockSvc.pollAnonymousBootstrap.and.returnValues(
      Promise.resolve(RUNNING_STATUS),
      Promise.resolve(DONE_STATUS)
    );

    const clearIntervalSpy = spyOn(window, 'clearInterval').and.callThrough();

    fixture.detectChanges(); // triggers ngOnInit -> _startBootstrap

    // Let the async _startBootstrap promise resolve (startAnonymousBootstrap)
    tick();

    // First poll tick
    tick(POLL_INTERVAL_MS);
    tick(); // resolve promise

    // Second poll tick — returns done=true, should clear the interval
    tick(POLL_INTERVAL_MS);
    tick(); // resolve promise

    expect(clearIntervalSpy).toHaveBeenCalled();
    expect(component.isRunning()).toBeFalse();
    expect(component.files().length).toBeGreaterThan(0);
  }));

  // ── Polling: clearInterval called on error status ──────────────────────────

  it('calls clearInterval when polling returns done=true with an error', fakeAsync(() => {
    setup('Build a todo app');

    mockSvc.startAnonymousBootstrap.and.resolveTo({ job_id: 'job-456' });
    mockSvc.pollAnonymousBootstrap.and.resolveTo(ERROR_STATUS);

    const clearIntervalSpy = spyOn(window, 'clearInterval').and.callThrough();

    fixture.detectChanges();
    tick(); // resolve startAnonymousBootstrap

    tick(POLL_INTERVAL_MS);
    tick(); // resolve pollAnonymousBootstrap (done=true with error)

    expect(clearIntervalSpy).toHaveBeenCalled();
    expect(component.isRunning()).toBeFalse();
    expect(component.fatalError()).toBe('Chain provider failed.');
  }));

  // ── Polling: clearInterval called on 404 network error ────────────────────

  it('calls clearInterval when polling receives a 404 response', fakeAsync(() => {
    setup('Build a todo app');

    mockSvc.startAnonymousBootstrap.and.resolveTo({ job_id: 'job-789' });
    mockSvc.pollAnonymousBootstrap.and.rejectWith({ status: 404 });

    const clearIntervalSpy = spyOn(window, 'clearInterval').and.callThrough();

    fixture.detectChanges();
    tick(); // resolve startAnonymousBootstrap

    tick(POLL_INTERVAL_MS);
    tick(); // reject pollAnonymousBootstrap with 404

    expect(clearIntervalSpy).toHaveBeenCalled();
    expect(component.isRunning()).toBeFalse();
  }));

  // ── Polling: does NOT stop on transient network errors ────────────────────

  it('does not stop polling on a transient non-404 network error', fakeAsync(() => {
    setup('Build a todo app');

    mockSvc.startAnonymousBootstrap.and.resolveTo({ job_id: 'job-abc' });

    let callCount = 0;
    mockSvc.pollAnonymousBootstrap.and.callFake(() => {
      callCount++;
      if (callCount <= 2) {
        return Promise.reject({ status: 503 });
      }
      return Promise.resolve(DONE_STATUS);
    });

    const clearIntervalSpy = spyOn(window, 'clearInterval').and.callThrough();

    fixture.detectChanges();
    tick();

    // First poll — 503, swallowed by catch
    tick(POLL_INTERVAL_MS);
    tick();

    // Second poll — 503, swallowed by catch
    tick(POLL_INTERVAL_MS);
    tick();

    // Third poll — done=true, should clear interval
    tick(POLL_INTERVAL_MS);
    tick();

    expect(clearIntervalSpy).toHaveBeenCalledTimes(1);
    expect(component.isRunning()).toBeFalse();
  }));

  // ── ngOnDestroy stops any live interval ───────────────────────────────────

  it('stops polling in ngOnDestroy', fakeAsync(() => {
    setup('Build a todo app');

    mockSvc.startAnonymousBootstrap.and.resolveTo({ job_id: 'job-destroy' });
    // Never resolves with done=true — interval stays alive
    mockSvc.pollAnonymousBootstrap.and.resolveTo(RUNNING_STATUS);

    const clearIntervalSpy = spyOn(window, 'clearInterval').and.callThrough();

    fixture.detectChanges();
    tick();

    tick(POLL_INTERVAL_MS); tick();

    fixture.destroy(); // triggers ngOnDestroy

    expect(clearIntervalSpy).toHaveBeenCalled();
  }));
});
