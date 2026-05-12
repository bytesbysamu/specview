import { HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { from } from 'rxjs';
import { catchError, switchMap, throwError } from 'rxjs';
import { TokenLifecycleService } from '../services/token-lifecycle.service';

const PUBLIC_PATHS = ['/api/auth/login', '/api/auth/register', '/api/auth/refresh'];

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
