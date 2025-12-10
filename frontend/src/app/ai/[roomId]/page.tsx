'use client';

import { useEffect, useMemo, useState } from 'react';
import { useParams } from 'next/navigation';
import { ChatMessage, useChatStream } from '@/hooks/useChatStream';
import { ChatWindow } from '@/components/chat/ChatWindow';
import { apiFetch } from '@/lib/api';
import { sanitizeMessageText } from '@/lib/sanitize';
import { getAccessToken } from '@/lib/auth-storage';

const WS_BASE = process.env.NEXT_PUBLIC_WS_BASE ?? 'ws://localhost:8000';

export default function AiChatPage() {
  const params = useParams<{ roomId: string }>();
  const roomId = String(params.roomId || '');

  const [initialMessages, setInitialMessages] = useState<ChatMessage[]>([]);
  const [historyError, setHistoryError] = useState<string | null>(null);

  useEffect(() => {
    console.log('[AiChatPage] mount, roomId =', roomId);

    (async () => {
      try {
        const data: any = await apiFetch('/api/ai/history/');
        console.log('[AiChatPage] history raw response =', data);

        let items: any[] = [];

        if (Array.isArray(data)) {
          items = data;
        } else if (Array.isArray(data?.history)) {
          items = data.history;
        } else if (Array.isArray(data?.results)) {
          items = data.results;
        }

        const mapped: ChatMessage[] = items.map(
          (item: any, idx: number): ChatMessage => {
            const question = item.question ?? '';
            const answer = item.answer ?? '';
            const createdAt =
              item.created_at || item.created || new Date().toISOString();

            return {
              id: String(item.id ?? `history-${idx}`),
              author: 'Mira',
              text: sanitizeMessageText(`${question}\n\n${answer}`.trim()),
              createdAt,
              isAi: true,
              isStreaming: false,
            };
          }
        );

        setInitialMessages(mapped);
        setHistoryError(null);
      } catch (err) {
        console.error('[AiChatPage] history fetch error:', err);
        setHistoryError('Не удалось загрузить историю диалогов с ИИ.');
      }
    })();
  }, []);

  const wsUrl = useMemo(() => {
    const token = getAccessToken();
    const qs = token ? `?token=${encodeURIComponent(token)}` : '';
    const url = `${WS_BASE}/ws/ai/${roomId}/${qs}`;
    console.log('[AiChatPage] wsUrl =', url);
    return url;
  }, [roomId]);

  const { messages, sendMessage } = useChatStream({
    wsUrl,
    initialMessages,
  });

  return (
    <div className="p-4 h-screen bg-zinc-950 text-zinc-50">
      <div className="max-w-3xl mx-auto h-full">
        {historyError && (
          <div className="mb-2 text-xs text-red-400">{historyError}</div>
        )}

        <ChatWindow
          title="AI-чат с Мирой"
          messages={messages}
          onSend={sendMessage}
        />
      </div>
    </div>
  );
}
