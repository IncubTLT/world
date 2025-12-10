const CONTROL_CHARS_RE = /[\u0000-\u0008\u000B\u000C\u000E-\u001F\u007F]/g;

export const MAX_MESSAGE_LENGTH = 4000;

/**
 * Нормализует строку для безопасного вывода в чат.
 * Важно: мы не рендерим HTML, а показываем текст — React сам экранирует спецсимволы.
 */
export function sanitizeMessageText(
  raw: unknown,
  maxLength: number = MAX_MESSAGE_LENGTH
): string {
  let text: string;

  if (typeof raw === 'string') {
    text = raw;
  } else if (raw == null) {
    text = '';
  } else {
    text = String(raw);
  }

  // Унифицируем переводы строк
  text = text.replace(/\r\n?/g, '\n');

  // Убираем управляющие символы, которые могут ломать рендер
  text = text.replace(CONTROL_CHARS_RE, '');

  // Ограничиваем длину
  if (text.length > maxLength) {
    text = text.slice(0, maxLength) + ' …';
  }

  // Слегка подчистим хвост
  return text.trimEnd();
}
