import {
  getAccessToken,
  getRefreshToken,
  setTokens,
  clearTokens,
} from './auth-storage';

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? '';

export class ApiError extends Error {
  public status: number;
  public details: unknown;

  constructor(status: number, details: unknown) {
    super(`API error: ${status}`);
    this.status = status;
    this.details = details;
  }
}

const CSRFTOKEN_COOKIE_NAME = 'csrftoken';

function getCookie(name: string): string | null {
  if (typeof document === 'undefined') return null;
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) {
    return parts.pop()!.split(';').shift() || null;
  }
  return null;
}

function isUnsafeMethod(method: string): boolean {
  const m = method.toUpperCase();
  return !['GET', 'HEAD', 'OPTIONS', 'TRACE'].includes(m);
}

/**
 * Нормализуем путь до вида `/something/...`,
 * даже если нам передали абсолютный URL.
 */
function normalizePath(path: string): string {
  if (/^https?:\/\//i.test(path)) {
    try {
      return new URL(path).pathname || '/';
    } catch {
      return '/';
    }
  }
  return path.startsWith('/') ? path : `/${path}`;
}

/**
 * Решаем, нужен ли CSRF для конкретного запроса.
 * По твоей логике — только для /auth/* (email-аутентификация).
 */
function shouldAttachCsrf(path: string, method: string): boolean {
  if (!isUnsafeMethod(method)) return false;

  const p = normalizePath(path);
  if (p.startsWith('/auth/')) {
    return true;
  }
  return false;
}

/**
 * Внутренний помощник: один HTTP-запрос с учётом:
 *  - X-Requested-With
 *  - CSRF (для /auth/*)
 *  - Authorization: Bearer <access>
 */
async function doFetch(
  path: string,
  options: RequestInit = {},
  accessTokenOverride?: string
): Promise<Response> {
  const isAbsolute = /^https?:\/\//i.test(path);
  const url = isAbsolute
    ? path
    : `${API_BASE_URL}${path.startsWith('/') ? path : `/${path}`}`;

  const method = (options.method ?? 'GET').toUpperCase();

  const headers = new Headers({
    'X-Requested-With': 'XMLHttpRequest',
    ...(options.headers as Record<string, string> | undefined),
  });

  // CSRF — только для /auth/* и небезопасных методов
  if (shouldAttachCsrf(path, method) && !headers.has('X-CSRFTOKEN')) {
    const token = getCookie(CSRFTOKEN_COOKIE_NAME);
    if (token) {
      headers.set('X-CSRFTOKEN', token);
    }
  }

  // AUTH — глобально, для всех запросов, если есть access-токен
  const accessToken = accessTokenOverride ?? getAccessToken();
  if (accessToken && !headers.has('Authorization')) {
    headers.set('Authorization', `Bearer ${accessToken}`);
  }

  return fetch(url, {
    ...options,
    method,
    credentials: 'include',
    headers,
  });
}

async function parseResponse<T>(res: Response): Promise<T> {
  if (res.status === 204) {
    return undefined as T;
  }

  const contentType = res.headers.get('Content-Type') ?? '';
  if (contentType.includes('application/json')) {
    return (await res.json()) as T;
  }

  // fallback на текст
  return (await res.text()) as unknown as T;
}

/**
 * Универсальный HTTP-клиент:
 *  - делает запрос;
 *  - если 401 и есть refresh — обновляет access и повторяет запрос;
 *  - если всё равно не ок — кидает ApiError.
 */
export async function apiFetch<TResponse>(
  path: string,
  options: RequestInit = {}
): Promise<TResponse> {
  // 1) первая попытка
  let res = await doFetch(path, options);

  if (res.status !== 401) {
    if (!res.ok) {
      const details = await parseResponse<unknown>(res);
      throw new ApiError(res.status, details);
    }
    return parseResponse<TResponse>(res);
  }

  // 2) 401: пробуем обновить токен
  const refresh = getRefreshToken();
  if (!refresh) {
    clearTokens();
    const details = await parseResponse<unknown>(res).catch(() => null);
    throw new ApiError(res.status, details);
  }

  try {
    const refreshRes = await fetch(`${API_BASE_URL}/auth/jwt/refresh/`, {
      method: 'POST',
      credentials: 'include',
      headers: {
        'Content-Type': 'application/json',
        'X-Requested-With': 'XMLHttpRequest',
      },
      body: JSON.stringify({ refresh }),
    });

    if (!refreshRes.ok) {
      clearTokens();
      const details = await parseResponse<unknown>(refreshRes).catch(
        () => null
      );
      throw new ApiError(refreshRes.status, details);
    }

    const data = (await refreshRes.json()) as {
      access: string;
      refresh?: string;
    };

    setTokens({
      access: data.access,
      refresh: data.refresh ?? refresh,
    });

    // 3) повторяем исходный запрос с новым access-токеном
    res = await doFetch(path, options, data.access);

    if (!res.ok) {
      const details = await parseResponse<unknown>(res);
      throw new ApiError(res.status, details);
    }

    return parseResponse<TResponse>(res);
  } catch (err) {
    // Если что-то пошло совсем не так — вычищаем токены
    clearTokens();
    if (err instanceof ApiError) {
      throw err;
    }
    throw err;
  }
}
