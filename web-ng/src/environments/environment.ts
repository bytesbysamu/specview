export const environment = {
  production: false,
  // oll-core dev instance. Services call relative `/api/*` paths; under
  // `ng serve` those are forwarded here by proxy.conf.json (target :3199).
  // This value documents the same target for non-proxied / direct use.
  apiBaseUrl: 'http://localhost:3199',
};
