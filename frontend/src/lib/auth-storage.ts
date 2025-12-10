export type TokenPair = {
  access: string;
  refresh: string;
};

const ACCESS_TOKEN_KEY = 'auth_access_token';
const REFRESH_TOKEN_KEY = 'auth_refresh_token';

function isBrowser(): boolean {
  return typeof window !== 'undefined';
}

/**
 * Читаем пару токенов из localStorage.
 * На сервере (SSR) всегда возвращает null.
 */
export function loadTokens(): TokenPair | null {
  if (!isBrowser()) return null;

  try {
    const access = window.localStorage.getItem(ACCESS_TOKEN_KEY);
    const refresh = window.localStorage.getItem(REFRESH_TOKEN_KEY);

    if (!access || !refresh) {
      return null;
    }

    return { access, refresh };
  } catch {
    return null;
  }
}

/**
 * Полная очистка токенов из хранилища.
 */
export function clearTokens(): void {
  if (!isBrowser()) return;

  try {
    window.localStorage.removeItem(ACCESS_TOKEN_KEY);
    window.localStorage.removeItem(REFRESH_TOKEN_KEY);
  } catch {
    // можно залогировать, но не обязательно
  }
}

/**
 * Сохраняем пару токенов.
 * Если передан null – просто очищаем хранилище.
 */
export function saveTokens(tokens: TokenPair | null): void {
  if (!isBrowser()) return;

  try {
    if (!tokens) {
      clearTokens();
      return;
    }

    window.localStorage.setItem(ACCESS_TOKEN_KEY, tokens.access);
    window.localStorage.setItem(REFRESH_TOKEN_KEY, tokens.refresh);
  } catch {
    // тихо проглатываем
  }
}

/**
 * Утилита для api.ts – достаём только access-токен.
 */
export function getAccessToken(): string | null {
  const tokens = loadTokens();
  return tokens?.access ?? null;
}

/**
 * Совместимость со старым кодом: достаём refresh-токен.
 */
export function getRefreshToken(): string | null {
  const tokens = loadTokens();
  return tokens?.refresh ?? null;
}

/**
 * Совместимость со старым кодом: setTokens.
 * По сути просто обёртка над saveTokens.
 */
export function setTokens(tokens: TokenPair | null): void {
  saveTokens(tokens);
}
