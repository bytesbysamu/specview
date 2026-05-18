import { HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { tap, catchError, throwError } from 'rxjs';
import { SubscriptionService } from '../services/subscription.service';
import { usageRemaining } from '../state/usage.state';

export const billingInterceptor: HttpInterceptorFn = (req, next) => {
  const subscription = inject(SubscriptionService);

  return next(req).pipe(
    tap(event => {
      // HttpResponse carries headers; HttpSentEvent etc. do not
      if ('headers' in event) {
        const remaining = (event as { headers: { get(k: string): string | null } })
          .headers.get('X-Usage-Remaining');
        const limit = (event as { headers: { get(k: string): string | null } })
          .headers.get('X-Usage-Limit');
        if (remaining !== null) {
          usageRemaining.set({
            remaining: parseInt(remaining, 10),
            limit: limit !== null ? parseInt(limit, 10) : 0,
          });
        }
      }
    }),
    catchError((err: unknown) => {
      if (err instanceof HttpErrorResponse && err.status === 429) {
        const plan = subscription.plan();

        if (plan === 'pro') {
          console.warn('[billing] 429 received for pro user — unexpected', err);
          return throwError(() => err);
        }

      }

      return throwError(() => err);
    })
  );
};
