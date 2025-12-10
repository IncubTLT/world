export type TokenPair = {
  access: string;
  refresh: string;
};

const TOKENS_KEY = 'auth_tokens';

export function loadTokens(): TokenPair | null {
  if (typeof window === 'undefined') return null;
  try {
    const raw = localStorage.getItem(TOKENS_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as TokenPair;
    if (!parsed.access || !parsed.refresh) return null;
    return parsed;
  } catch {
    return null;
  }
}

export function saveTokens(pair: TokenPair | null): void {
  if (typeof window === 'undefined') return;
  if (!pair) {
    localStorage.removeItem(TOKENS_KEY);
    return;
  }
  localStorage.setItem(TOKENS_KEY, JSON.stringify(pair));
}

export function getAccessToken(): string | null {
  const pair = loadTokens();
  return pair?.access ?? null;
}

export function getRefreshToken(): string | null {
  const pair = loadTokens();
  return pair?.refresh ?? null;
}

export function setTokens(pair: TokenPair | null): void {
  saveTokens(pair);
}

export function clearTokens(): void {
  saveTokens(null);
}
