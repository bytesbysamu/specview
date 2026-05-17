import { InjectionToken } from '@angular/core';

/**
 * When true, ProjectsService returns fixture data instead of making HTTP calls.
 * Provided with value `true` by PgScrollShellComponent.
 * All other consumers receive `null` (optional injection).
 */
export const DEMO_MODE = new InjectionToken<boolean>('DEMO_MODE');
