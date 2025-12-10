import { apiFetch } from './api';

export interface TokenPair {
  access: string;
  refresh: string;
}

export async function requestLoginCode(email: string): Promise<void> {
  await apiFetch<void>('/auth/request-code/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email }),
  });
}

export async function verifyLoginCode(
  email: string,
  code: string
): Promise<TokenPair> {
  const raw = await apiFetch<any>('/auth/verify-code/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, code }),
  });

  console.log('[verifyLoginCode] raw response:', raw);

  const access = raw?.access ?? raw?.access_token ?? raw?.token ?? null;

  const refresh = raw?.refresh ?? raw?.refresh_token ?? null;

  if (!access || !refresh) {
    console.error('[verifyLoginCode] no tokens in response:', raw);
    throw new Error(
      'Backend не вернул access/refresh токены в ответе verify-code.'
    );
  }

  return { access, refresh };
}

export async function refreshToken(refresh: string): Promise<TokenPair> {
  const raw = await apiFetch<any>('/auth/token/refresh/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh }),
  });

  console.log('[refreshToken] raw response:', raw);

  const access = raw?.access ?? raw?.access_token ?? raw?.token ?? null;

  const newRefresh = raw?.refresh ?? raw?.refresh_token ?? null;

  if (!access || !newRefresh) {
    throw new Error(
      'Backend не вернул access/refresh токены в ответе refresh.'
    );
  }

  return { access, refresh: newRefresh };
}
