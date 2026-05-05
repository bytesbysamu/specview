# Task 2: ErrorParserService — Execution Plan

## Source

howDays `ErrorParserService`: extracts code + message from unknown errors, unwraps `rejection` property. The architecture doc specifies a richer version with `ParsedError` interface returning `{ message, code, retryable }` and a type-narrowing chain.

## Target

`/tmp/wt/final/src/app/shared/error/`

## Files

| File | Purpose |
|------|---------|
| `error-parser.model.ts` | `ParsedError` interface, `ErrorCode` string union |
| `error-parser.service.ts` | Stateless service, `parse(error: unknown): ParsedError` |
| `toast-error.helper.ts` | Function mapping ParsedError to Ionic toast |
| `error-parser.service.spec.ts` | Tests covering all 8 error type variants |
| `index.ts` | Barrel export |

## Error Type Mapping (from architecture)

| Input Type | `message` | `code` | `retryable` |
|------------|-----------|--------|-------------|
| `HttpErrorResponse` with body `{ message }` | Body message | `SERVER` | `status >= 500` |
| `HttpErrorResponse` without body message | Status text | `SERVER` | `status >= 500` |
| `TypeError` | "Network error -- check your connection" | `NETWORK` | `true` |
| `DOMException` (name=AbortError) | "Request was cancelled" | `ABORT` | `false` |
| `string` | The string itself | `UNKNOWN` | `false` |
| `null` / `undefined` / unknown | "Something went wrong" | `UNKNOWN` | `false` |

## Design

- Chain of Responsibility: type-narrowing `if/else` chain, most specific first.
- Unwrap `rejection` property (from howDays pattern) before type narrowing.
- `HttpErrorResponse` imported from `@angular/common/http` -- available in Angular 20 via `@angular/common`.
- `toast-error.helper.ts` is a standalone function, not a service. Takes `ToastController` and `ParsedError`, shows danger/warning toast.
- Fully independent module -- no dependency on Capacitor base or any other shared module.

## Conventions

- Injectable, `providedIn: 'root'`.
- Tests use concrete objects (no stubs): real `HttpErrorResponse`, real `TypeError`, real `DOMException`.
- Test naming: `condition_action_expectedResult`.

## Commit

`1b8153b` feat(error): add ErrorParserService with parsed error model and toast helper

## Test Results

12 tests covering: HttpErrorResponse with body message, HttpErrorResponse status-only, HttpErrorResponse 5xx retryable, TypeError (network), DOMException AbortError, DOMException non-abort, string, null, undefined, random object, Capacitor plugin error with code, rejection unwrapping.
