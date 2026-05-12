// Co-located mock factory — consumed only by auth.service.spec.ts.
// If a second test file needs this mock, move it to web-ng/src/app/testing/ and
// update this import path.

import { signal } from '@angular/core';
import { TokenLifecycleService } from './token-lifecycle.service';

export function createTokenLifecycleServiceMock(): jasmine.SpyObj<TokenLifecycleService> {
  const mock = jasmine.createSpyObj<TokenLifecycleService>('TokenLifecycleService', [
    'storeToken',
    'getRawToken',
    'getToken',
    'handleAuthFailure',
  ]);
  // isLoggedIn is a readonly signal property — add it manually so tests can read and set it
  (mock as any).isLoggedIn = signal(false);
  mock.getRawToken.and.returnValue(null);
  mock.getToken.and.returnValue(Promise.resolve(null));
  mock.handleAuthFailure.and.returnValue(Promise.resolve());
  return mock;
}
