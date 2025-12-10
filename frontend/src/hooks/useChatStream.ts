'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { StreamingSocket, WsChatEvent } from '@/lib/streaming-socket';
import { sanitizeMessageText } from '@/lib/sanitize';

export interface ChatMessage {
  id: string;
  author: string;
  text: string;
  createdAt: string;
  isAi?: boolean;
  isStreaming?: boolean;
}

interface UseChatStreamOptions {
  wsUrl: string;
  initialMessages?: ChatMessage[];
}

export function useChatStream(options: UseChatStreamOptions) {
  const { wsUrl, initialMessages = [] } = options;

  const [messages, setMessages] = useState<ChatMessage[]>(initialMessages);
  const socketRef = useRef<StreamingSocket | null>(null);
  const streamMessageIdRef = useRef<string | null>(null);

  useEffect(() => {
    if (initialMessages.length) {
      setMessages(initialMessages);
    }
  }, [initialMessages]);

  const handleEvent = useCallback((event: WsChatEvent) => {
    // 1) история из messaging
    if (event.type === 'history' && Array.isArray(event.items)) {
      setMessages(() => {
        const historyMessages: ChatMessage[] = event.items!.map((item) => ({
          id: String(item.id),
          author: sanitizeMessageText(item.display_name ?? 'Unknown', 128),
          text: sanitizeMessageText(item.text),
          createdAt: item.created_at,
          isAi: false,
          isStreaming: false,
        }));
        return historyMessages;
      });
      return;
    }

    // 2) обычные/стриминговые сообщения
    if (!event.message) return;

    const authorRaw = event.display_name ?? event.username ?? 'System';
    const author = sanitizeMessageText(authorRaw, 128);
    const messageText = sanitizeMessageText(event.message);

    const isStream = Boolean(event.is_stream);
    const isStart = Boolean(event.is_start);
    const isEnd = Boolean(event.is_end);

    // Не-стриминговое сообщение
    if (!isStream) {
      setMessages((prev) => [
        ...prev,
        {
          id: crypto.randomUUID?.() ?? `${Date.now()}-${Math.random()}`,
          author,
          text: messageText,
          createdAt: new Date().toISOString(),
          isAi: author === 'Mira',
          isStreaming: false,
        },
      ]);
      return;
    }

    // Стриминговые чанки
    setMessages((prev) => {
      const next = [...prev];

      if (isStart || !streamMessageIdRef.current) {
        const id = crypto.randomUUID?.() ?? `${Date.now()}-${Math.random()}`;
        streamMessageIdRef.current = id;

        next.push({
          id,
          author,
          text: messageText,
          createdAt: new Date().toISOString(),
          isAi: author === 'Mira',
          isStreaming: !isEnd,
        });
      } else {
        const id = streamMessageIdRef.current!;
        const idx = next.findIndex((m) => m.id === id);
        if (idx !== -1) {
          next[idx] = {
            ...next[idx],
            text: messageText,
            isStreaming: !isEnd,
          };
        }
      }

      if (isEnd) {
        streamMessageIdRef.current = null;
      }

      return next;
    });
  }, []);

  useEffect(() => {
    const socket = new StreamingSocket(wsUrl);
    socketRef.current = socket;

    const unsubscribe = socket.subscribe(handleEvent);
    socket.connect();

    return () => {
      unsubscribe();
      socket.close();
      socketRef.current = null;
    };
  }, [wsUrl, handleEvent]);

  const sendMessage = useCallback((text: string) => {
    const safeText = sanitizeMessageText(text);
    if (!safeText.trim()) return;
    socketRef.current?.send({ message: safeText });
  }, []);

  return {
    messages,
    sendMessage,
  };
}
