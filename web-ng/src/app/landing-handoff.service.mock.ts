import { LandingHandoffService, LandingHandoff } from './landing-handoff.service';

/**
 * Factory for a mock LandingHandoffService.
 *
 * Provides a typed Jasmine spy with a configurable handoff value and
 * spy stubs for all public methods. Call `.and.resolveTo(...)` on each
 * spy in your test to control its resolved value.
 *
 * @param handoff — The handoff state to expose. Defaults to `{ mode: 'none' }`.
 */
export function createMockLandingHandoffService(
  handoff: LandingHandoff = { mode: 'none' }
): jasmine.SpyObj<LandingHandoffService> {
  const mock = jasmine.createSpyObj<LandingHandoffService>(
    'LandingHandoffService',
    ['fetchDemoResult', 'startAnonymousBootstrap', 'pollAnonymousBootstrap'],
    { handoff }
  );
  return mock;
}
