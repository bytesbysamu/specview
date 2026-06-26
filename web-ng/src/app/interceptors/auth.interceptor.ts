import { HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { from } from 'rxjs';
import { catchError, switchMap, throwError } from 'rxjs';
import { TokenLifecycleService } from '../services/token-lifecycle.service';

// Passwordless endpoints that must NOT carry a bearer (magic-link request and
// the link-token exchange happen before a JWT exists). /api/auth/refresh is
// also listed so the proactive-refresh path in TokenLifecycleService does not
// recurse through getToken(); it attaches its own bearer header directly.
const PUBLIC_PATHS = ['/api/auth/magic-link', '/api/auth/verify', '/api/auth/refresh'];

export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const lifecycle = inject(TokenLifecycleService);

  // Public paths bypass token logic entirely.
  if (PUBLIC_PATHS.some(p => req.url.startsWith(p))) {
    return next(req).pipe(
      catchError((err: unknown) => throwError(() => err))
    );
  }

  return from(lifecycle.getToken()).pipe(
    switchMap(token => {
      const outgoing = token
        ? req.clone({ setHeaders: { Authorization: `Bearer ${token}` } })
        : req;

      return next(outgoing).pipe(
        catchError((err: unknown) => {
          if (err instanceof HttpErrorResponse && err.status === 401) {
            lifecycle.handleAuthFailure();
          }
          return throwError(() => err);
        })
      );
    })
  );
};
