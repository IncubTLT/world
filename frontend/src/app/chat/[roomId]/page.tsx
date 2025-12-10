'use client';

import { useParams } from 'next/navigation';
import { useChatStream } from '@/hooks/useChatStream';
import { ChatWindow } from '@/components/chat/ChatWindow';

const WS_BASE = process.env.NEXT_PUBLIC_WS_BASE ?? 'ws://localhost:8000';

export default function ChatRoomPage() {
  const params = useParams<{ roomId: string }>();
  const roomId = params.roomId;

  const wsUrl = `${WS_BASE}/ws/chat/${roomId}/`;

  const { messages, sendMessage } = useChatStream({ wsUrl });

  return (
    <div className="p-4 h-screen bg-zinc-950 text-zinc-50">
      <div className="max-w-3xl mx-auto h-full">
        <ChatWindow
          title={`Комната ${roomId}`}
          messages={messages}
          onSend={sendMessage}
        />
      </div>
    </div>
  );
}
