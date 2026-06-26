import { HttpInterceptorFn } from '@angular/common/http';
import { environment } from '../../environments/environment';

/**
 * Prefixes root-relative API calls with environment.apiBaseUrl.
 *
 * Web (dev ng-serve proxy AND prod nginx) serves the API same-origin, so
 * apiBaseUrl is '' and this is a no-op — root-relative `/api/*` paths resolve
 * against the page origin exactly as before.
 *
 * A Capacitor native build has no same-origin server (the page is served from
 * the device over capacitor://), so it sets apiBaseUrl to the absolute API
 * origin (e.g. https://api.oll.am); this interceptor then rewrites `/api/*`
 * to `https://api.oll.am/api/*`.
 *
 * Registered LAST in the interceptor chain so the auth/billing interceptors
 * still see the original root-relative URL when they match public paths.
 *
 * Native follow-up: add an Angular build configuration (e.g. `--configuration
 * native`) with a fileReplacement swapping in an environment.native.ts that
 * sets apiBaseUrl to the deployed API origin. The HTTP layer needs no further
 * changes — this interceptor already handles the prefixing.
 */
export const baseUrlInterceptor: HttpInterceptorFn = (req, next) => {
  const base = environment.apiBaseUrl;
  // Only rewrite root-relative paths (e.g. "/api/..."). Absolute URLs
  // (http://, https://, capacitor://) and non-rooted paths pass through.
  if (base && req.url.startsWith('/')) {
    return next(req.clone({ url: base.replace(/\/$/, '') + req.url }));
  }
  return next(req);
};
