import { ComponentFixture, TestBed, fakeAsync, tick } from '@angular/core/testing';
import { ActivatedRoute } from '@angular/router';

import { AnalyzeResultComponent } from './analyze-result.component';
import { ProjectsService } from '../services/projects.service';
import { PublicAnalyzeJobStatus } from '../api/models/public-analyze-job-status';

const POLL_INTERVAL_MS = 2500;

const RUNNING_STATUS: PublicAnalyzeJobStatus = {
  running: true,
  done: false,
};

const DONE_STATUS: PublicAnalyzeJobStatus = {
  running: false,
  done: true,
  analysis: '# Analysis\n\nSome content.',
  braindump: 'Build a todo app',
  project_id: 'proj-123',
};

const ERROR_STATUS: PublicAnalyzeJobStatus = {
  running: false,
  done: true,
  error: 'Chain provider failed.',
};

function createMockProjectsService(): jasmine.SpyObj<ProjectsService> {
  return jasmine.createSpyObj('ProjectsService', ['pollPublicAnalysis']);
}

function createMockRoute(jobId: string | null) {
  return {
    snapshot: {
      queryParamMap: {
        get: (key: string) => key === 'job' ? jobId : null,
      },
    },
  };
}

describe('AnalyzeResultComponent', () => {
  let fixture: ComponentFixture<AnalyzeResultComponent>;
  let component: AnalyzeResultComponent;
  let mockSvc: jasmine.SpyObj<ProjectsService>;

  function setup(jobId: string | null = 'job-123') {
    mockSvc = createMockProjectsService();

    TestBed.configureTestingModule({
      imports: [AnalyzeResultComponent],
      providers: [
        { provide: ProjectsService, useValue: mockSvc },
        { provide: ActivatedRoute, useValue: createMockRoute(jobId) },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(AnalyzeResultComponent);
    component = fixture.componentInstance;
  }

  afterEach(() => {
    component.ngOnDestroy();
    TestBed.resetTestingModule();
  });

  it('creates the component without errors', () => {
    setup(null);
    fixture.detectChanges();
    expect(component).toBeTruthy();
  });

  it('sets fatalError when no job query param is present', () => {
    setup(null);
    fixture.detectChanges();
    expect(component.fatalError()).toContain('No job ID');
    expect(component.isRunning()).toBeFalse();
  });

  it('calls clearInterval when polling completes (done=true)', fakeAsync(() => {
    setup('job-123');

    mockSvc.pollPublicAnalysis.and.returnValues(
      Promise.resolve(RUNNING_STATUS),
      Promise.resolve(DONE_STATUS)
    );

    const clearIntervalSpy = spyOn(window, 'clearInterval').and.callThrough();

    fixture.detectChanges();

    tick(POLL_INTERVAL_MS);
    tick();

    tick(POLL_INTERVAL_MS);
    tick();

    expect(clearIntervalSpy).toHaveBeenCalled();
    expect(component.isRunning()).toBeFalse();
    expect(component.analysisHtml()).toBeTruthy();
    expect(component.braindumpContent()).toBe('Build a todo app');
    expect(component.projectId()).toBe('proj-123');
  }));

  it('calls clearInterval when polling returns done=true with an error', fakeAsync(() => {
    setup('job-456');

    mockSvc.pollPublicAnalysis.and.resolveTo(ERROR_STATUS);

    const clearIntervalSpy = spyOn(window, 'clearInterval').and.callThrough();

    fixture.detectChanges();

    tick(POLL_INTERVAL_MS);
    tick();

    expect(clearIntervalSpy).toHaveBeenCalled();
    expect(component.isRunning()).toBeFalse();
    expect(component.fatalError()).toBe('Chain provider failed.');
  }));

  it('calls clearInterval when polling receives a 404 response', fakeAsync(() => {
    setup('job-789');

    mockSvc.pollPublicAnalysis.and.rejectWith({ status: 404 });

    const clearIntervalSpy = spyOn(window, 'clearInterval').and.callThrough();

    fixture.detectChanges();

    tick(POLL_INTERVAL_MS);
    tick();

    expect(clearIntervalSpy).toHaveBeenCalled();
    expect(component.isRunning()).toBeFalse();
    expect(component.fatalError()).toContain('not found');
  }));

  it('does not stop polling on a transient non-404 network error', fakeAsync(() => {
    setup('job-abc');

    let callCount = 0;
    mockSvc.pollPublicAnalysis.and.callFake(() => {
      callCount++;
      if (callCount <= 2) {
        return Promise.reject({ status: 503 });
      }
      return Promise.resolve(DONE_STATUS);
    });

    const clearIntervalSpy = spyOn(window, 'clearInterval').and.callThrough();

    fixture.detectChanges();

    tick(POLL_INTERVAL_MS); tick();
    tick(POLL_INTERVAL_MS); tick();
    tick(POLL_INTERVAL_MS); tick();

    expect(clearIntervalSpy).toHaveBeenCalledTimes(1);
    expect(component.isRunning()).toBeFalse();
  }));

  it('stops polling in ngOnDestroy', fakeAsync(() => {
    setup('job-destroy');

    mockSvc.pollPublicAnalysis.and.resolveTo(RUNNING_STATUS);

    const clearIntervalSpy = spyOn(window, 'clearInterval').and.callThrough();

    fixture.detectChanges();

    tick(POLL_INTERVAL_MS); tick();

    fixture.destroy();

    expect(clearIntervalSpy).toHaveBeenCalled();
  }));
});
