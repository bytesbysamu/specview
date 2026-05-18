import { DemoAwareProjectsService } from './demo-aware-projects.service';

export function createDemoAwareProjectsServiceMock(): jasmine.SpyObj<DemoAwareProjectsService> {
  const mock = jasmine.createSpyObj<DemoAwareProjectsService>(
    'DemoAwareProjectsService',
    ['getProjects', 'getProject', 'getSpec'],
  );
  mock.getProjects.and.returnValue(Promise.resolve([]));
  mock.getProject.and.returnValue(Promise.resolve(undefined as any));
  mock.getSpec.and.returnValue(Promise.resolve(undefined as any));
  return mock;
}
