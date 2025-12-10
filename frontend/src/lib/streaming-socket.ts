export interface WsHistoryItem {
  id: string | number;
  text: string;
  display_name: string;
  created_at: string;
}

export interface WsChatEvent {
  type?: string;
  items?: WsHistoryItem[];

  message?: string;
  display_name?: string;
  username?: string;
  error?: boolean;

  is_stream?: boolean;
  is_start?: boolean;
  is_end?: boolean;
}

type MessageListener = (event: WsChatEvent) => void;

export class StreamingSocket {
  private url: string;
  private ws: WebSocket | null = null;
  private listeners = new Set<MessageListener>();
  private reconnectAttempts = 0;
  private readonly maxReconnectAttempts: number;

  constructor(url: string, maxReconnectAttempts = 3) {
    this.url = url;
    this.maxReconnectAttempts = maxReconnectAttempts;
  }

  connect() {
    if (typeof window === 'undefined') return;

    if (
      this.ws &&
      (this.ws.readyState === WebSocket.OPEN ||
        this.ws.readyState === WebSocket.CONNECTING)
    ) {
      return;
    }

    this.ws = new WebSocket(this.url);

    this.ws.onopen = () => {
      this.reconnectAttempts = 0;
    };

    this.ws.onmessage = (event: MessageEvent) => {
      try {
        const data = JSON.parse(event.data) as WsChatEvent;
        this.notify(data);
      } catch {
        // можно залогировать, если нужно
      }
    };

    this.ws.onclose = () => {
      this.ws = null;
      if (this.reconnectAttempts < this.maxReconnectAttempts) {
        const delay = 500 * Math.pow(2, this.reconnectAttempts);
        this.reconnectAttempts += 1;
        setTimeout(() => this.connect(), delay);
      }
    };

    this.ws.onerror = () => {
      // слегка агрессивно:
      this.ws?.close();
    };
  }

  /**
   * Подписка на входящие сообщения.
   * Возвращает функцию для отписки.
   */
  subscribe(listener: MessageListener): () => void {
    this.listeners.add(listener);
    return () => {
      this.listeners.delete(listener);
    };
  }

  private notify(event: WsChatEvent) {
    for (const listener of this.listeners) {
      listener(event);
    }
  }

  send(payload: unknown) {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) return;
    this.ws.send(JSON.stringify(payload));
  }

  close() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }
}
