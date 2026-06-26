export const environment = {
  production: false,
  // Same-origin by default. Services call root-relative `/api/*` paths; under
  // `ng serve` proxy.conf.json forwards them to the dev API, and the docker
  // nginx build proxies `/api` to the api container — so an empty base keeps
  // both web paths working with no host prefix.
  //
  // A Capacitor native build (no same-origin server) overrides this with the
  // absolute API origin via a dedicated build configuration; baseUrlInterceptor
  // then prefixes every `/api/*` call. See base-url.interceptor.ts.
  apiBaseUrl: '',
};
