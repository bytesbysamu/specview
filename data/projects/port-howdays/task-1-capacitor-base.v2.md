# Task 1: Capacitor Base Service — Execution Plan

## Source

howDays pattern: individual Capacitor wrapper services (e.g. `CapacitorPurchasesService`, `CapacitorSplashScreenService`, `CapacitorPreferencesService`) each repeat platform guards and init logic. The architecture doc specifies extracting this into an abstract base with: `initialized` signal, `Capacitor.isNativePlatform()` guard, typed wrapper methods.

## Target

`/tmp/wt/final/src/app/shared/capacitor/`

## Files

| File | Purpose |
|------|---------|
| `capacitor-base.service.ts` | Abstract class: `initialized` signal, platform detection, one-time init guard, error wrapping |
| `capacitor-base.service.spec.ts` | Tests: web returns mock, native inits once, double-init is no-op |
| `haptics.service.ts` | Concrete example extending base, wraps `@capacitor/haptics` |
| `haptics.service.spec.ts` | Tests: web no-op, native delegates to plugin |
| `index.ts` | Barrel export |

## Design

- Abstract class (not factory) per architecture decision — communicates contract clearly, Angular `inject()` works with class hierarchy.
- `protected abstract initializePlugin(): Promise<void>` — subclass wires the plugin.
- `protected abstract getWebFallback(): T` — subclass returns mock/no-op for web.
- `isNative` signal (readonly) from `Capacitor.isNativePlatform()`.
- `initialized` signal (readonly) flips to true after first `initializePlugin()` call.
- `initialize()` public method: checks guard, calls abstract, flips signal.
- `wrapCall<R>(nativeFn: () => Promise<R>, webFallback: R): Promise<R>` — protected helper that routes based on platform.

## Conventions

- Standalone (no NgModule), providedIn: 'root' on concrete services.
- Base class is not injectable — only concrete subclasses.
- Tests use Jasmine + TestBed, spy on `Capacitor.isNativePlatform()`.
- Test naming: `condition_action_expectedResult`.

## Commit

`ba6b500` feat(capacitor): add CapacitorBaseService abstract class with haptics example

## Test Results

29/29 passing (includes 10 base service tests + 7 haptics tests + 12 error parser tests from Task 2).
