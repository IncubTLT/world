'use client';

import { useState } from 'react';
import { useEmailCodeAuth } from '@/hooks/useEmailCodeAuth';
import Link from 'next/link';

export function Header() {
  const [isOpen, setIsOpen] = useState(false);
  const [localEmail, setLocalEmail] = useState('');
  const [code, setCode] = useState('');

  const { status, error, email, isAuthorized, sendCode, verifyCode, logout } =
    useEmailCodeAuth();

  const busy = status === 'requesting-code' || status === 'verifying';

  const handlePrimaryClick = async () => {
    if (!isAuthorized) {
      // шаг 1: отправка кода
      if (!localEmail) return;
      await sendCode(localEmail);
    } else {
      // если вдруг решишь что-то ещё делать
    }
  };

  const handleVerify = async () => {
    if (!code) return;
    await verifyCode(code);
    setCode('');
    setIsOpen(false);
  };

  const handleLogout = () => {
    logout();
    setIsOpen(false);
  };

  const displayEmail = email || localEmail;

  return (
    <header className="w-full border-b border-slate-800 bg-slate-950/80 backdrop-blur z-20">
      <div className="mx-auto max-w-6xl px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="text-lg font-semibold text-slate-50">DCL</span>

          {/* Быстрая ссылка в AI-чат с фиксированным room_id для девелопмента */}
          <Link
            href="/ai/00000000-0000-0000-0000-0000000000aa"
            className="text-[11px] px-2 py-1 rounded-full border border-violet-500/60 text-violet-300 hover:bg-violet-500/10 transition"
          >
            AI-чат
          </Link>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-lg font-semibold text-slate-50">DCL</span>
        </div>

        <div className="relative">
          {/* Кнопка в шапке */}
          {isAuthorized ? (
            <button
              type="button"
              onClick={() => setIsOpen((v) => !v)}
              className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-slate-900 hover:bg-slate-800 border border-slate-700 text-xs text-slate-100 transition"
            >
              <span className="h-7 w-7 rounded-full bg-gradient-to-br from-sky-500 to-violet-500 flex items-center justify-center text-xs font-semibold">
                {displayEmail?.[0]?.toUpperCase() || 'U'}
              </span>
              <span className="hidden sm:inline">
                {displayEmail || 'Профиль'}
              </span>
            </button>
          ) : (
            <button
              type="button"
              onClick={() => setIsOpen((v) => !v)}
              className="px-4 py-1.5 rounded-full bg-gradient-to-r from-sky-500 to-violet-500 text-xs font-medium text-white shadow-md hover:shadow-lg transition"
            >
              Войти
            </button>
          )}

          {/* Попап */}
          {isOpen && (
            <div className="absolute right-0 mt-2 w-80 rounded-2xl bg-slate-900 border border-slate-800 shadow-xl p-4 text-sm text-slate-100">
              <div className="flex justify-between items-center mb-2">
                <span className="text-xs font-semibold text-slate-300">
                  {isAuthorized ? 'Профиль' : 'Вход по коду'}
                </span>
                <button
                  type="button"
                  onClick={() => setIsOpen(false)}
                  className="text-slate-500 hover:text-slate-300 text-xs"
                >
                  ✕
                </button>
              </div>

              {!isAuthorized ? (
                <div className="space-y-3">
                  {/* Шаг 1: email */}
                  <div className="space-y-1">
                    <label className="block text-xs text-slate-400">
                      E-mail
                    </label>
                    <input
                      type="email"
                      className="w-full px-2 py-1.5 rounded-lg bg-slate-950 border border-slate-700 text-xs outline-none focus:border-sky-500"
                      placeholder="user@example.com"
                      value={localEmail}
                      onChange={(e) => setLocalEmail(e.target.value)}
                    />
                  </div>

                  {/* Шаг 2: код */}
                  {status === 'code-sent' && (
                    <div className="space-y-1">
                      <label className="block text-xs text-slate-400">
                        Код из письма
                      </label>
                      <input
                        type="text"
                        className="w-full px-2 py-1.5 rounded-lg bg-slate-950 border border-slate-700 text-xs outline-none focus:border-sky-500"
                        placeholder="123456"
                        value={code}
                        onChange={(e) => setCode(e.target.value)}
                      />
                    </div>
                  )}

                  {error && <div className="text-xs text-red-400">{error}</div>}

                  <div className="flex gap-2 pt-1">
                    {status !== 'code-sent' && (
                      <button
                        type="button"
                        onClick={handlePrimaryClick}
                        disabled={busy || !localEmail}
                        className="flex-1 px-3 py-1.5 rounded-lg bg-sky-600 hover:bg-sky-500 disabled:bg-slate-700 disabled:cursor-not-allowed text-xs font-medium transition"
                      >
                        {busy ? 'Отправка...' : 'Получить код'}
                      </button>
                    )}
                    {status === 'code-sent' && (
                      <button
                        type="button"
                        onClick={handleVerify}
                        disabled={busy || !code}
                        className="flex-1 px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 disabled:bg-slate-700 disabled:cursor-not-allowed text-xs font-medium transition"
                      >
                        {busy ? 'Проверка...' : 'Войти'}
                      </button>
                    )}
                  </div>
                </div>
              ) : (
                <div className="space-y-3">
                  <div>
                    <p className="text-xs text-slate-400">Вы вошли как</p>
                    <p className="text-sm text-slate-100">{displayEmail}</p>
                  </div>
                  <button
                    type="button"
                    onClick={handleLogout}
                    className="w-full px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs font-medium transition"
                  >
                    Выйти
                  </button>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
