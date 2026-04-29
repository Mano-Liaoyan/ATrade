const DEFAULT_LOCAL_API_BASE_URL = 'http://127.0.0.1:5181';

export function getApiBaseUrl(): string {
  const configuredUrl =
    process.env.NEXT_PUBLIC_ATRADE_API_BASE_URL ??
    process.env.ATRADE_FRONTEND_API_BASE_URL ??
    DEFAULT_LOCAL_API_BASE_URL;

  return configuredUrl.replace(/\/+$/, '');
}

export function buildApiUrl(path: string): string {
  const normalizedPath = path.startsWith('/') ? path : `/${path}`;
  return `${getApiBaseUrl()}${normalizedPath}`;
}
