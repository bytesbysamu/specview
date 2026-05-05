import { HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { catchError, throwError } from 'rxjs';
import { AuthService } from '../services/auth.service';

const PUBLIC_PATHS = ['/api/auth/login'];

export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const auth = inject(AuthService);
  const jwt = auth.getStoredJwt();

  let r = req;
  if (jwt && req.url.startsWith('/api/')) {
    r = req.clone({ setHeaders: { Authorization: `Bearer ${jwt}` } });
  }

  return next(r).pipe(
    catchError((err: unknown) => {
      if (
        err instanceof HttpErrorResponse &&
        err.status === 401 &&
        !PUBLIC_PATHS.some(p => req.url.startsWith(p))
      ) {
        auth.signOut();
      }
      return throwError(() => err);
    })
  );
};
