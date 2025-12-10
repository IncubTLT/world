'use client';

import { CORE_CLIENT_BACKEND } from '@/common/network/core-client';
import Image from 'next/image';
import Link from 'next/link';
import { useEffect, useState } from 'react';
import { FileUploadButton } from '@/components/filehub/FileUploadButton';

export const Home = () => {
  const [chatRoomId, setChatRoomId] = useState(
    '00000000-0000-0000-0000-000000000001' // тестовый UUID, поменяешь на реальный
  );
  const [aiRoomId, setAiRoomId] = useState(
    '00000000-0000-0000-0000-0000000000aa' // тестовый UUID, поменяешь на реальный
  );

  useEffect(() => {
    CORE_CLIENT_BACKEND.core_backend.get('/').then((res) => {
      console.log(res);
    });
  }, []);

  return (
    <main className="min-h-screen flex flex-col items-center justify-center gap-8 bg-slate-950 px-4 py-8">
      {/* Верхний блок: логотип + загрузка файлов */}
      <div className="flex flex-col md:flex-row items-center justify-center gap-10 max-w-5xl w-full">
        <div className="center flex-col space-y-4">
          <p className="text-4xl font-bold text-slate-50">DCL</p>
          <Image
            src="/page/home/hi.JPG"
            className="rounded w-80 h-96 object-cover shadow-xl shadow-slate-900/70"
            fetchPriority="high"
            priority
            alt="hi"
            width={600}
            height={700}
          />
        </div>

        <div className="p-6 rounded-2xl bg-slate-900 shadow-xl space-y-4 max-w-lg w-full border border-slate-800">
          <h1 className="text-xl font-semibold text-slate-50">
            Загрузка файлов в filehub
          </h1>

          <p className="text-sm text-slate-300">
            Выбери файл — он уйдёт в S3/MinIO через presigned POST, потом
            backend получит уведомление через <code>upload-complete</code>.
          </p>

          <FileUploadButton
            label="Загрузить аватар"
            visibility="private"
            fileType="image"
            targetAppLabel="users"
            targetModel="user"
            targetObjectId={42}
            role="avatar"
            priority={10}
            onUploaded={(res) => {
              console.log('Файл загружен:', res);
            }}
          />
        </div>
      </div>

      {/* Нижний блок: навигация по чатам */}
      <div className="grid gap-4 w-full max-w-5xl md:grid-cols-2">
        {/* Обычный пользовательский / групповой чат */}
        <div className="p-5 rounded-2xl bg-slate-900 border border-slate-800 shadow-lg flex flex-col gap-3">
          <h2 className="text-lg font-semibold text-slate-50">
            Чат между пользователями
          </h2>
          <p className="text-xs text-slate-300">
            История подгружается через WebSocket как список сообщений, новые
            сообщения от людей (и в будущем от ИИ) приходят потоково.
          </p>

          <label className="text-xs text-slate-400 mb-1">
            ID комнаты (UUID из backend&apos;а)
          </label>
          <input
            type="text"
            className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-700 text-xs text-slate-100 outline-none focus:border-sky-500"
            value={chatRoomId}
            onChange={(e) => setChatRoomId(e.target.value)}
            placeholder="00000000-0000-0000-0000-000000000001"
          />

          <div className="flex gap-2 pt-2">
            <Link
              href={`/chat/${chatRoomId}`}
              className="flex-1 inline-flex items-center justify-center px-3 py-2 rounded-lg bg-sky-600 hover:bg-sky-500 text-xs font-medium text-white transition"
            >
              Открыть чат
            </Link>
          </div>
        </div>

        {/* AI-чат (Mira) */}
        <div className="p-5 rounded-2xl bg-slate-900 border border-slate-800 shadow-lg flex flex-col gap-3">
          <h2 className="text-lg font-semibold text-slate-50">AI-чат (Mira)</h2>
          <p className="text-xs text-slate-300">
            История подгружается через REST <code>/api/ai/history/</code>,
            ответы ИИ приходят потоково через{' '}
            <code>ws/ai/&lt;room_id&gt;/</code>.
          </p>

          <label className="text-xs text-slate-400 mb-1">
            ID AI-комнаты (UUID, можно использовать тот же)
          </label>
          <input
            type="text"
            className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-700 text-xs text-slate-100 outline-none focus:border-violet-500"
            value={aiRoomId}
            onChange={(e) => setAiRoomId(e.target.value)}
            placeholder="00000000-0000-0000-0000-0000000000aa"
          />

          <div className="flex gap-2 pt-2">
            <Link
              href={`/ai/${aiRoomId}`}
              className="flex-1 inline-flex items-center justify-center px-3 py-2 rounded-lg bg-violet-600 hover:bg-violet-500 text-xs font-medium text-white transition"
            >
              Открыть AI-чат
            </Link>
          </div>

          <p className="text-[10px] text-slate-500 pt-1">
            Позже сюда можно будет заходить из пользовательских и групповых
            комнат, где Mira выступает отдельным участником.
          </p>
        </div>
      </div>
    </main>
  );
};
