# Angular Frontend Conventions — specview web-ng

This reference describes the Angular frontend conventions for `web-ng/src/app/`.
All agents and skills that touch Angular code must read this file first.

## Project Layout

```
web-ng/src/app/
├── app.component.ts        — Root component: sidebar, project list, file viewer
├── app.component.html      — Root template
├── app.component.scss      — Root styles
├── services/
│   └── projects.service.ts — All HTTP calls to /api
└── app.config.ts           — Bootstrap configuration
```

Flat structure — no feature sub-modules. The app is a single-page shell with a
sidebar file list and a main content area for rendered markdown.

## Signal-Based Reactivity

The app uses Angular signals throughout. Mandatory patterns:

- State as `signal<T>(initialValue)` — never use BehaviorSubject for local state.
- Derived values as `computed(() => ...)` — no manual subscriptions for derivations.
- Effects via `effect(() => ...)` for side-effects that react to signal changes.
- Template reads signals as plain function calls: `{{ mySignal() }}`.

Do not mix `Observable` pipelines with signal-based state management.
Use `firstValueFrom()` to bridge HTTP observables to promises in service methods.

## HTTP Service Pattern

All HTTP calls live in `ProjectsService` (`services/projects.service.ts`).
Service methods return `Promise<T>` (not `Observable<T>`).
Components call service methods with `await` inside `async` methods.

Template for a new service method:

```typescript
myMethod(param: string): Promise<ResponseType> {
  return firstValueFrom(
    this.http.post<ResponseType>('/api/endpoint', { param })
  );
}
```

Never call `HttpClient` directly from a component.

## Component Patterns

Root component (`app.component.ts`) holds all application state as signals:

```typescript
projects = signal<Project[]>([]);
activeProject = signal<Project | null>(null);
activeSpec = signal<Spec | null>(null);
loading = signal(false);
error = signal<string | null>(null);
```

Async operations follow this pattern:

```typescript
async doSomething() {
  this.loading.set(true);
  this.error.set(null);
  try {
    const result = await this.projectsService.myMethod(param);
    this.someSignal.set(result);
  } catch (e: any) {
    this.error.set(e?.error?.error ?? e?.message ?? 'Unknown error');
  } finally {
    this.loading.set(false);
  }
}
```

## Polling Pattern

Long-running backend jobs are polled with `setInterval`. Always clear the interval:

```typescript
private pollInterval: ReturnType<typeof setInterval> | null = null;

startPolling(jobId: string) {
  this.pollInterval = setInterval(async () => {
    const status = await this.projectsService.pollJob(jobId);
    if (status.done || status.error) {
      clearInterval(this.pollInterval!);
      this.pollInterval = null;
    }
  }, 3000);
}
```

Never leave an interval running after the operation completes.

## Template Conventions

- `@if` / `@for` control flow (not `*ngIf` / `*ngFor`) — Angular 17+ syntax.
- Bind class conditionally with `[class.active]="condition"`.
- Event handlers: `(click)="method()"` — no inline logic in templates.
- Loading states: show a spinner or disable the button via `[disabled]="loading()"`.

## Routing

No Angular Router — the app is a single view. Navigation is handled by setting
`activeProject` and `activeSpec` signals. Deep links are not supported in v1.

## Markdown Rendering

Spec file content is rendered as HTML via `marked` (already in package.json).
The rendered HTML is injected via `[innerHTML]` with `DOMPurify` sanitization.
Never trust raw API content in innerHTML without sanitization.

## Styles

Component-level SCSS in `*.component.scss`. Global styles in `styles.scss`.
CSS custom properties (variables) for theming — never hardcode colors.
Dark mode via `[data-theme="dark"]` on `<html>`.

## Testing Rules (non-negotiable)

- Every new service in `services/` requires a `*.service.spec.ts` and a `*.service.mock.ts`.
- Mock factory files export `createMock{Name}Service()` returning a typed Jasmine spy — never duplicate spy setup inline.
- Every polling implementation (`setInterval`) requires a `fakeAsync` spec verifying `clearInterval` is called on completion and on error.
- E2E selectors use `[data-test]` attributes only — add them to templates as E2E feature files require them.
- See `references/testing-conventions.md` for the full testing strategy.

## Quality Rules (non-negotiable)

- No `Observable` state — signals only for local component state.
- No direct `HttpClient` calls in components.
- No `*ngIf` / `*ngFor` — use `@if` / `@for`.
- No inline styles in templates.
- No `any` type except in error catch blocks.
- Every `setInterval` must have a corresponding `clearInterval`.
- `firstValueFrom` wraps every `HttpClient` call in services.
