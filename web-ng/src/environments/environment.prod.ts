export const environment = {
  production: true,
  // Prod serves the API same-origin behind the reverse proxy, so relative
  // `/api/*` paths need no host prefix.
  apiBaseUrl: '',
};
