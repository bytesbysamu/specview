import { ProjectsService } from './projects.service';

export function createProjectsServiceMock(): jasmine.SpyObj<ProjectsService> {
  const mock = jasmine.createSpyObj<ProjectsService>('ProjectsService', [
    'listProjects',
    'getProject',
    'getContext',
    'startBootstrap',
    'pollBootstrap',
    'createProject',
    'saveFile',
    'startEpicGuide',
    'pollEpicGuide',
  ]);
  mock.listProjects.and.returnValue(Promise.resolve([]));
  mock.getProject.and.returnValue(Promise.resolve(undefined as any));
  mock.getContext.and.returnValue(Promise.resolve(undefined as any));
  mock.startBootstrap.and.returnValue(Promise.resolve(undefined as any));
  mock.pollBootstrap.and.returnValue(Promise.resolve(undefined as any));
  mock.createProject.and.returnValue(Promise.resolve(undefined as any));
  mock.saveFile.and.returnValue(Promise.resolve(undefined as any));
  mock.startEpicGuide.and.returnValue(Promise.resolve(undefined as any));
  mock.pollEpicGuide.and.returnValue(Promise.resolve(undefined as any));
  return mock;
}
