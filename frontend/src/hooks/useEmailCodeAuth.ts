'use client';

import { useCallback, useEffect, useState } from 'react';
import {
  requestLoginCode,
  verifyLoginCode,
  refreshToken,
} from '@/lib/auth-api';
import { loadTokens, saveTokens, type TokenPair } from '@/lib/auth-storage';

type AuthStatus =
  | 'idle'
  | 'requesting-code'
  | 'code-sent'
  | 'verifying'
  | 'authorized'
  | 'error';

export function useEmailCodeAuth() {
  const [email, setEmail] = useState<string>('');
  const [status, setStatus] = useState<AuthStatus>('idle');
  const [error, setError] = useState<string | null>(null);
  const [tokens, setTokens] = useState<TokenPair | null>(null);

  useEffect(() => {
    const saved = loadTokens();
    if (saved) {
      setTokens(saved);
      setStatus('authorized');
    }
  }, []);

  const sendCode = useCallback(async (emailValue: string) => {
    setStatus('requesting-code');
    setError(null);

    try {
      await requestLoginCode(emailValue);
      setEmail(emailValue);
      setStatus('code-sent');
    } catch (e) {
      console.error(e);
      setStatus('error');
      setError(e instanceof Error ? e.message : 'Не удалось отправить код.');
      throw e;
    }
  }, []);

  const verifyCode = useCallback(
    async (code: string) => {
      if (!email) {
        throw new Error('E-mail не задан. Сначала отправь код.');
      }
      setStatus('verifying');
      setError(null);

      try {
        const pair = await verifyLoginCode(email, code);
        setTokens(pair);
        saveTokens(pair);
        setStatus('authorized');
        return pair;
      } catch (e) {
        console.error(e);
        setStatus('error');
        setError(
          e instanceof Error ? e.message : 'Не удалось подтвердить код.'
        );
        throw e;
      }
    },
    [email]
  );

  const logout = useCallback(() => {
    setTokens(null);
    saveTokens(null);
    setStatus('idle');
    setError(null);
    setEmail('');
  }, []);

  const refresh = useCallback(async () => {
    if (!tokens?.refresh) return null;
    try {
      const newPair = await refreshToken(tokens.refresh);
      setTokens(newPair);
      saveTokens(newPair);
      return newPair;
    } catch (e) {
      console.error(e);
      logout();
      return null;
    }
  }, [tokens, logout]);

  return {
    status,
    error,
    email,
    tokens,
    sendCode,
    verifyCode,
    logout,
    refresh,
    isAuthorized: status === 'authorized',
  };
}
