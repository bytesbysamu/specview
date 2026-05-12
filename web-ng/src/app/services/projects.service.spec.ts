import { TestBed } from '@angular/core/testing';
import { HttpClientTestingModule, HttpTestingController } from '@angular/common/http/testing';

import {
  ProjectsService,
  Project,
  Spec,
  PollStatusResponse,
  PollResultResponse,
  GeneratedFile,
} from './projects.service';

// ---------------------------------------------------------------------------
// Factory helpers
// ---------------------------------------------------------------------------

function makeSpec(filename: string, overrides: Partial<Spec> = {}): Spec {
  return { filename, label: filename, ...overrides };
}

function makeProject(overrides: Partial<Project> = {}): Project {
  return {
    id: 'proj-1',
    name: 'Test Project',
    createdAt: '2024-01-01T00:00:00Z',
    specs: [],
    ...overrides,
  };
}

function makePollStatus(overrides: Partial<PollStatusResponse> = {}): PollStatusResponse {
  return { running: false, done: true, current_step: null, ...overrides };
}

function makePollResult(overrides: Partial<PollResultResponse> = {}): PollResultResponse {
  return { running: false, done: true, ...overrides };
}

// ---------------------------------------------------------------------------
// sortSpecs ordering — tested via listProjects and getProject
// ---------------------------------------------------------------------------

describe('sortSpecs (via listProjects)', () => {
  let service: ProjectsService;
  let httpController: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({ imports: [HttpClientTestingModule] });
    service = TestBed.inject(ProjectsService);
    httpController = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpController.verify();
  });

  const CANONICAL_ORDER = ['braindump', 'analysis', 'epic', 'architecture', 'timeline', 'implementation-guide'];

  it('orders specs in canonical sequence regardless of API response order', async () => {
    const reversed = [...CANONICAL_ORDER].reverse().map(n => makeSpec(`${n}.md`));
    const promise = service.listProjects();

    const req = httpController.expectOne('/api/projects');
    req.flush([makeProject({ specs: reversed })]);

    const [project] = await promise;
    const names = project.specs.map(s => s.filename.replace(/\.md$/, ''));
    expect(names).toEqual(CANONICAL_ORDER);
  });

  it('places unknown filenames after all canonical entries', async () => {
    const specs = [
      makeSpec('unknown-file.md'),
      makeSpec('braindump.md'),
      makeSpec('epic.md'),
    ];
    const promise = service.listProjects();

    const req = httpController.expectOne('/api/projects');
    req.flush([makeProject({ specs })]);

    const [project] = await promise;
    const filenames = project.specs.map(s => s.filename);
    expect(filenames[0]).toBe('braindump.md');
    expect(filenames[1]).toBe('epic.md');
    expect(filenames[2]).toBe('unknown-file.md');
  });

  it('sorts multiple unknown filenames alphabetically among themselves', async () => {
    const specs = [
      makeSpec('zebra.md'),
      makeSpec('apple.md'),
      makeSpec('mango.md'),
    ];
    const promise = service.listProjects();

    const req = httpController.expectOne('/api/projects');
    req.flush([makeProject({ specs })]);

    const [project] = await promise;
    const filenames = project.specs.map(s => s.filename);
    expect(filenames).toEqual(['apple.md', 'mango.md', 'zebra.md']);
  });

  it('handles a project with no specs', async () => {
    const promise = service.listProjects();

    const req = httpController.expectOne('/api/projects');
    req.flush([makeProject({ specs: [] })]);

    const [project] = await promise;
    expect(project.specs).toEqual([]);
  });
});

// ---------------------------------------------------------------------------
// ProjectsService — HTTP methods
// ---------------------------------------------------------------------------

describe('ProjectsService', () => {
  let service: ProjectsService;
  let httpController: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({ imports: [HttpClientTestingModule] });
    service = TestBed.inject(ProjectsService);
    httpController = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpController.verify();
  });

  // -------------------------------------------------------------------------
  // listProjects
  // -------------------------------------------------------------------------

  describe('listProjects', () => {
    it('GETs /api/projects and returns sorted project list', async () => {
      const raw = [makeProject({ id: 'p1' }), makeProject({ id: 'p2' })];
      const promise = service.listProjects();

      const req = httpController.expectOne('/api/projects');
      expect(req.request.method).toBe('GET');
      req.flush(raw);

      const result = await promise;
      expect(result.length).toBe(2);
      expect(result[0].id).toBe('p1');
    });
  });

  // -------------------------------------------------------------------------
  // getProject
  // -------------------------------------------------------------------------

  describe('getProject', () => {
    it('GETs /api/projects/:id', async () => {
      const promise = service.getProject('abc-123');

      const req = httpController.expectOne('/api/projects/abc-123');
      expect(req.request.method).toBe('GET');
      req.flush(makeProject({ id: 'abc-123' }));

      const result = await promise;
      expect(result.id).toBe('abc-123');
    });

    it('sorts specs returned from the API', async () => {
      const specs = [makeSpec('epic.md'), makeSpec('braindump.md')];
      const promise = service.getProject('p1');

      const req = httpController.expectOne('/api/projects/p1');
      req.flush(makeProject({ specs }));

      const result = await promise;
      expect(result.specs[0].filename).toBe('braindump.md');
      expect(result.specs[1].filename).toBe('epic.md');
    });
  });

  // -------------------------------------------------------------------------
  // getContext
  // -------------------------------------------------------------------------

  describe('getContext', () => {
    it('GETs /api/context/:key', async () => {
      const promise = service.getContext('builder');

      const req = httpController.expectOne('/api/context/builder');
      expect(req.request.method).toBe('GET');
      req.flush({ content: 'context content', text: 'plain text' });

      const result = await promise;
      expect(result.content).toBe('context content');
    });

    it('resolves with content and optional text field', async () => {
      const promise = service.getContext('principles');

      const req = httpController.expectOne('/api/context/principles');
      req.flush({ content: 'principles content' });

      const result = await promise;
      expect(result.content).toBe('principles content');
      expect(result.text).toBeUndefined();
    });
  });

  // -------------------------------------------------------------------------
  // startBootstrap
  // -------------------------------------------------------------------------

  describe('startBootstrap', () => {
    it('POSTs to /api/ai/text/bootstrap-project with project_name and braindump', async () => {
      const promise = service.startBootstrap('My Project', 'the braindump text');

      const req = httpController.expectOne('/api/ai/text/bootstrap-project');
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual({ project_name: 'My Project', braindump: 'the braindump text' });
      req.flush({ job_id: 'job-42' });

      const result = await promise;
      expect(result.job_id).toBe('job-42');
    });
  });

  // -------------------------------------------------------------------------
  // pollBootstrap
  // -------------------------------------------------------------------------

  describe('pollBootstrap', () => {
    it('GETs /api/ai/text/bootstrap-project/status/:jobId', async () => {
      const promise = service.pollBootstrap('job-42');

      const req = httpController.expectOne('/api/ai/text/bootstrap-project/status/job-42');
      expect(req.request.method).toBe('GET');
      req.flush(makePollStatus({ running: true, done: false, current_step: 'epic' }));

      const result = await promise;
      expect(result.running).toBeTrue();
      expect(result.current_step).toBe('epic');
    });

    it('resolves with done=true and files when job completes', async () => {
      const files: GeneratedFile[] = [{ filename: 'epic.md', content: '# Epic' }];
      const promise = service.pollBootstrap('job-42');

      const req = httpController.expectOne('/api/ai/text/bootstrap-project/status/job-42');
      req.flush(makePollStatus({ done: true, files }));

      const result = await promise;
      expect(result.done).toBeTrue();
      expect(result.files).toEqual(files);
    });
  });

  // -------------------------------------------------------------------------
  // createProject
  // -------------------------------------------------------------------------

  describe('createProject', () => {
    it('POSTs to /api/projects with name and files', async () => {
      const files: GeneratedFile[] = [{ filename: 'braindump.md', content: '# My idea' }];
      const promise = service.createProject('New Project', files);

      const req = httpController.expectOne('/api/projects');
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual({ name: 'New Project', files });
      req.flush(makeProject({ id: 'new-proj', name: 'New Project' }));

      const result = await promise;
      expect(result.id).toBe('new-proj');
    });
  });

  // -------------------------------------------------------------------------
  // saveFile
  // -------------------------------------------------------------------------

  describe('saveFile', () => {
    it('PUTs to /api/projects/:id/files/:filename with content', async () => {
      const promise = service.saveFile('proj-1', 'epic.md', '# Epic content');

      const req = httpController.expectOne('/api/projects/proj-1/files/epic.md');
      expect(req.request.method).toBe('PUT');
      expect(req.request.body).toEqual({ content: '# Epic content' });
      req.flush(null);

      await promise;
    });

    it('resolves without error on success', async () => {
      const promise = service.saveFile('proj-1', 'braindump.md', 'content');

      const req = httpController.expectOne('/api/projects/proj-1/files/braindump.md');
      req.flush(null);

      await expectAsync(promise).toBeResolved();
    });
  });

  // -------------------------------------------------------------------------
  // startEpicGuide
  // -------------------------------------------------------------------------

  describe('startEpicGuide', () => {
    it('POSTs to /api/projects/:id/generate-epic-guide', async () => {
      const promise = service.startEpicGuide('proj-1');

      const req = httpController.expectOne('/api/projects/proj-1/generate-epic-guide');
      expect(req.request.method).toBe('POST');
      req.flush({ started: true });

      const result = await promise;
      expect(result.started).toBeTrue();
    });

    it('resolves with alreadyRunning flag when job is already in progress', async () => {
      const promise = service.startEpicGuide('proj-1');

      const req = httpController.expectOne('/api/projects/proj-1/generate-epic-guide');
      req.flush({ started: false, alreadyRunning: true });

      const result = await promise;
      expect(result.started).toBeFalse();
      expect(result.alreadyRunning).toBeTrue();
    });
  });

  // -------------------------------------------------------------------------
  // pollEpicGuide
  // -------------------------------------------------------------------------

  describe('pollEpicGuide', () => {
    it('GETs /api/projects/:id/generate-epic-guide/status', async () => {
      const promise = service.pollEpicGuide('proj-1');

      const req = httpController.expectOne('/api/projects/proj-1/generate-epic-guide/status');
      expect(req.request.method).toBe('GET');
      req.flush(makePollResult({ running: true, done: false }));

      const result = await promise;
      expect(result.running).toBeTrue();
      expect(result.done).toBeFalse();
    });

    it('resolves with filename when job completes', async () => {
      const promise = service.pollEpicGuide('proj-1');

      const req = httpController.expectOne('/api/projects/proj-1/generate-epic-guide/status');
      req.flush(makePollResult({ done: true, filename: 'implementation-guide.md' }));

      const result = await promise;
      expect(result.done).toBeTrue();
      expect(result.filename).toBe('implementation-guide.md');
    });

    it('resolves with error field when job fails', async () => {
      const promise = service.pollEpicGuide('proj-1');

      const req = httpController.expectOne('/api/projects/proj-1/generate-epic-guide/status');
      req.flush(makePollResult({ done: false, error: 'AI timeout' }));

      const result = await promise;
      expect(result.error).toBe('AI timeout');
    });
  });
});
