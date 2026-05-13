import { HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { Router } from '@angular/router';
import { tap, catchError, throwError } from 'rxjs';
import { SubscriptionService } from '../services/subscription.service';
import { usageRemaining } from '../state/usage.state';

interface LimitErrorBody {
  error: string;
  feature?: string;
  limit?: number;
  reset_at?: string;
  upgrade_url?: string;
}

export const billingInterceptor: HttpInterceptorFn = (req, next) => {
  const router = inject(Router);
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

        const body = err.error as LimitErrorBody | null;
        const feature = body?.feature ?? 'unknown';
        const reason = plan === 'lapsed' ? 'payment_lapsed' : 'limit_reached';

        router.navigate(['/upgrade'], {
          queryParams: { reason, feature },
        });
      }

      return throwError(() => err);
    })
  );
};
