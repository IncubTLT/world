'use client';

import { useState, KeyboardEvent } from 'react';
import { ChatMessage } from '@/hooks/useChatStream';

interface ChatWindowProps {
  messages: ChatMessage[];
  onSend: (text: string) => void;
  title?: string;
}

export function ChatWindow({ messages, onSend, title }: ChatWindowProps) {
  const [input, setInput] = useState('');

  const handleSend = () => {
    if (!input.trim()) return;
    onSend(input);
    setInput('');
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex flex-col h-full max-h-[600px] border rounded-lg shadow-sm bg-zinc-900/70">
      {title && (
        <div className="px-4 py-2 border-b border-zinc-700 text-sm font-medium text-zinc-100">
          {title}
        </div>
      )}

      <div className="flex-1 overflow-y-auto px-4 py-3 space-y-2 text-sm">
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex flex-col ${
              msg.isAi ? 'items-start' : 'items-end'
            }`}
          >
            <div className="text-xs text-zinc-400 mb-0.5">
              {msg.author} · {new Date(msg.createdAt).toLocaleTimeString()}{' '}
              {msg.isStreaming ? ' ⌛' : ''}
            </div>
            <div
              className={`inline-block px-3 py-2 rounded-2xl max-w-[80%] whitespace-pre-wrap break-words ${
                msg.isAi
                  ? 'bg-indigo-600/80 text-white'
                  : 'bg-zinc-700/80 text-white'
              }`}
            >
              {msg.text}
            </div>
          </div>
        ))}
      </div>

      <div className="flex items-center gap-2 border-t border-zinc-700 px-3 py-2">
        <input
          className="flex-1 bg-transparent border border-zinc-700 rounded-md px-3 py-2 text-sm text-zinc-100 outline-none focus:ring-1 focus:ring-indigo-500"
          placeholder="Напишите сообщение…"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
        />
        <button
          type="button"
          onClick={handleSend}
          className="px-3 py-2 text-sm rounded-md bg-indigo-600 text-white hover:bg-indigo-500"
        >
          Отправить
        </button>
      </div>
    </div>
  );
}
