import { TestBed } from '@angular/core/testing';
import { signal } from '@angular/core';

import { DemoAwareProjectsService } from './demo-aware-projects.service';
import { AuthService } from './auth.service';
import { ProjectsService, Project, Spec } from './projects.service';
import { DEMO_FIXTURE_PROJECTS } from './demo-fixtures';
import { createProjectsServiceMock } from './projects.service.mock';

// ---------------------------------------------------------------------------
// Factory helpers
// ---------------------------------------------------------------------------

function makeAuthServiceMock(loggedIn = false): jasmine.SpyObj<AuthService> {
  const mock = jasmine.createSpyObj<AuthService>('AuthService', ['signOut', 'login', 'register', 'getStoredJwt']);
  (mock as any).isLoggedIn = signal(loggedIn);
  return mock;
}

function makeProject(overrides: Partial<Project> = {}): Project {
  return {
    id: 'real-proj-1',
    name: 'Real Project',
    createdAt: '2026-01-01T00:00:00Z',
    specs: [],
    ...overrides,
  };
}

function makeSpec(filename: string, overrides: Partial<Spec> = {}): Spec {
  return { filename, label: filename, ...overrides };
}

// ---------------------------------------------------------------------------
// DemoAwareProjectsService
// ---------------------------------------------------------------------------

describe('DemoAwareProjectsService', () => {
  let service: DemoAwareProjectsService;
  let authMock: jasmine.SpyObj<AuthService>;
  let projectsMock: jasmine.SpyObj<ProjectsService>;

  function createService(loggedIn: boolean) {
    authMock = makeAuthServiceMock(loggedIn);
    projectsMock = createProjectsServiceMock();

    TestBed.configureTestingModule({
      providers: [
        DemoAwareProjectsService,
        { provide: AuthService, useValue: authMock },
        { provide: ProjectsService, useValue: projectsMock },
      ],
    });

    service = TestBed.inject(DemoAwareProjectsService);
  }

  // -------------------------------------------------------------------------
  // loading signal initial state
  // -------------------------------------------------------------------------

  describe('loading signal', () => {
    it('starts as false', () => {
      createService(false);
      expect(service.loading()).toBeFalse();
    });
  });

  // -------------------------------------------------------------------------
  // Unauthenticated — demo fixture behaviour
  // -------------------------------------------------------------------------

  describe('when unauthenticated', () => {
    beforeEach(() => createService(false));

    describe('getProjects()', () => {
      it('returns fixture projects without calling ProjectsService', async () => {
        const result = await service.getProjects();
        expect(projectsMock.listProjects).not.toHaveBeenCalled();
        expect(result.length).toBe(DEMO_FIXTURE_PROJECTS.length);
      });

      it('returns projects whose IDs match the fixture definitions', async () => {
        const result = await service.getProjects();
        const ids = result.map(p => p.id);
        expect(ids).toEqual(DEMO_FIXTURE_PROJECTS.map(p => p.id));
      });

      it('does not set loading to true', async () => {
        await service.getProjects();
        expect(service.loading()).toBeFalse();
      });
    });

    describe('getProject(id)', () => {
      it('returns the matching fixture project without calling ProjectsService', async () => {
        const target = DEMO_FIXTURE_PROJECTS[0];
        const result = await service.getProject(target.id);
        expect(projectsMock.getProject).not.toHaveBeenCalled();
        expect(result.id).toBe(target.id);
        expect(result.name).toBe(target.name);
      });

      it('rejects with an error message when the ID is not in fixtures', async () => {
        await expectAsync(service.getProject('non-existent-id')).toBeRejectedWithError(/Demo project not found/);
      });

      it('does not set loading to true', async () => {
        const target = DEMO_FIXTURE_PROJECTS[0];
        await service.getProject(target.id);
        expect(service.loading()).toBeFalse();
      });
    });

    describe('getSpec(id, section)', () => {
      it('returns the matching spec from fixtures without calling ProjectsService', async () => {
        const target = DEMO_FIXTURE_PROJECTS[0];
        const firstSpec = target.specs[0];
        const result = await service.getSpec(target.id, firstSpec.filename);
        expect(projectsMock.getProject).not.toHaveBeenCalled();
        expect(result.filename).toBe(firstSpec.filename);
      });

      it('rejects when the section does not exist in the project', async () => {
        const target = DEMO_FIXTURE_PROJECTS[0];
        await expectAsync(
          service.getSpec(target.id, 'missing-section.md')
        ).toBeRejectedWithError(/not found/);
      });

      it('rejects when the project ID is not in fixtures', async () => {
        await expectAsync(
          service.getSpec('no-such-project', 'analysis.md')
        ).toBeRejected();
      });
    });
  });

  // -------------------------------------------------------------------------
  // Authenticated — delegates to ProjectsService
  // -------------------------------------------------------------------------

  describe('when authenticated', () => {
    beforeEach(() => createService(true));

    describe('getProjects()', () => {
      it('delegates to ProjectsService.listProjects()', async () => {
        const realProjects = [makeProject()];
        projectsMock.listProjects.and.returnValue(Promise.resolve(realProjects));

        const result = await service.getProjects();

        expect(projectsMock.listProjects).toHaveBeenCalledTimes(1);
        expect(result).toEqual(realProjects);
      });

      it('sets loading to true during the call and false after', async () => {
        let capturedDuringCall = false;
        projectsMock.listProjects.and.callFake(() => {
          capturedDuringCall = service.loading();
          return Promise.resolve([]);
        });

        await service.getProjects();

        expect(capturedDuringCall).toBeTrue();
        expect(service.loading()).toBeFalse();
      });

      it('sets loading back to false even when ProjectsService throws', async () => {
        projectsMock.listProjects.and.returnValue(Promise.reject(new Error('network')));

        await expectAsync(service.getProjects()).toBeRejected();
        expect(service.loading()).toBeFalse();
      });
    });

    describe('getProject(id)', () => {
      it('delegates to ProjectsService.getProject(id)', async () => {
        const realProject = makeProject({ id: 'real-1' });
        projectsMock.getProject.and.returnValue(Promise.resolve(realProject));

        const result = await service.getProject('real-1');

        expect(projectsMock.getProject).toHaveBeenCalledWith('real-1');
        expect(result).toEqual(realProject);
      });

      it('sets loading to false after a successful call', async () => {
        projectsMock.getProject.and.returnValue(Promise.resolve(makeProject()));
        await service.getProject('real-1');
        expect(service.loading()).toBeFalse();
      });

      it('sets loading back to false even when ProjectsService throws', async () => {
        projectsMock.getProject.and.returnValue(Promise.reject(new Error('not found')));
        await expectAsync(service.getProject('bad-id')).toBeRejected();
        expect(service.loading()).toBeFalse();
      });
    });

    describe('getSpec(id, section)', () => {
      it('returns the matching spec from the project returned by ProjectsService', async () => {
        const spec = makeSpec('analysis.md', { content: '# Analysis' });
        const realProject = makeProject({ id: 'p1', specs: [spec] });
        projectsMock.getProject.and.returnValue(Promise.resolve(realProject));

        const result = await service.getSpec('p1', 'analysis.md');

        expect(projectsMock.getProject).toHaveBeenCalledWith('p1');
        expect(result.filename).toBe('analysis.md');
      });

      it('rejects when the section is not present in the returned project', async () => {
        const realProject = makeProject({ id: 'p1', specs: [makeSpec('braindump.md')] });
        projectsMock.getProject.and.returnValue(Promise.resolve(realProject));

        await expectAsync(
          service.getSpec('p1', 'analysis.md')
        ).toBeRejectedWithError(/not found/);
      });
    });
  });

  // -------------------------------------------------------------------------
  // Auth-state transition — no reload required
  // -------------------------------------------------------------------------

  describe('auth-state transition', () => {
    it('switches from fixture data to ProjectsService when isLoggedIn flips to true', async () => {
      createService(false);

      // Initially unauthenticated — expect fixture data
      const demoResult = await service.getProjects();
      expect(projectsMock.listProjects).not.toHaveBeenCalled();
      expect(demoResult.length).toBe(DEMO_FIXTURE_PROJECTS.length);

      // Flip auth state — no page reload, just signal update
      const realProjects = [makeProject()];
      projectsMock.listProjects.and.returnValue(Promise.resolve(realProjects));
      (authMock as any).isLoggedIn.set(true);

      // Next call must delegate to ProjectsService
      const realResult = await service.getProjects();
      expect(projectsMock.listProjects).toHaveBeenCalledTimes(1);
      expect(realResult).toEqual(realProjects);
    });

    it('switches back to fixture data when isLoggedIn flips to false', async () => {
      createService(true);
      projectsMock.listProjects.and.returnValue(Promise.resolve([makeProject()]));

      await service.getProjects();
      expect(projectsMock.listProjects).toHaveBeenCalledTimes(1);

      // Log out
      (authMock as any).isLoggedIn.set(false);

      const demoResult = await service.getProjects();
      // No additional call to ProjectsService
      expect(projectsMock.listProjects).toHaveBeenCalledTimes(1);
      expect(demoResult.length).toBe(DEMO_FIXTURE_PROJECTS.length);
    });
  });
});
