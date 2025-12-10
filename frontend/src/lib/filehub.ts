import { apiFetch } from './api';

/**
 * Уровни видимости файла.
 */
export type MediaVisibility = 'public' | 'private' | 'auth';
export type FilehubVisibility = MediaVisibility;

/**
 * Тип файла на фронте.
 * На бэкенд уходит как file_type.
 */
export type FileKind = 'image' | 'video' | 'audio' | 'document' | 'other';

/**
 * Описание presigned POST (старый формат: url + fields).
 */
type PresignedPostDescriptor = {
  url: string;
  fields: Record<string, string>;
  method?: 'POST';
};

/**
 * Описание presigned PUT (новый формат: url + method + headers).
 */
type PresignedPutDescriptor = {
  url: string;
  method: 'PUT';
  headers?: Record<string, string>;
};

/**
 * Универсальный дескриптор загрузки.
 */
export type UploadDescriptor = PresignedPostDescriptor | PresignedPutDescriptor;

/**
 * Ответ по одному файлу из upload-init.
 */
export type UploadInitFile = {
  media_file_id: string;
  key: string;
  visibility: MediaVisibility;
  upload: UploadDescriptor;
};

/**
 * Полный ответ upload-init.
 */
type UploadInitResponse = {
  files: UploadInitFile[];
};

/**
 * Результат, который мы возвращаем наружу после upload-complete.
 * По сути — тот же объект, что прилетел в upload-init.
 */
export type UploadCompleteResult = UploadInitFile;

/**
 * Доп. опции для upload-init.
 */
export type FilehubUploadOptions = {
  visibility?: MediaVisibility;
  fileType?: FileKind; // фронтовое имя; на бэке это уйдёт как file_type
  contentType?: string;

  // Привязка к объекту (совпадает с бэкендом):
  targetAppLabel?: string;
  targetModel?: string;
  targetObjectId?: number;

  role?: string;
  priority?: number;

  // Если будешь считать хеш на фронте
  checksum?: string | null;
};

/**
 * Загрузка одного файла в S3/VK Cloud.
 * Поддерживает оба варианта: presigned POST и presigned PUT.
 */
async function uploadToS3(file: File, upload: UploadDescriptor): Promise<void> {
  // Немного дебага
  if ('fields' in upload) {
    console.log('[uploadToS3] method=POST url=', upload.url);
    console.log('[uploadToS3] fields=', upload.fields);

    const formData = new FormData();
    Object.entries(upload.fields).forEach(([k, v]) => formData.append(k, v));
    formData.append('file', file);

    const res = await fetch(upload.url, {
      method: 'POST',
      body: formData,
    });

    if (!res.ok) {
      const text = await res.text().catch(() => '');
      console.error('[uploadToS3][POST] failed', res.status, text);
      throw new Error(`S3 POST upload failed: ${res.status}`);
    }
    return;
  }

  console.log('[uploadToS3] method=', upload.method, 'url=', upload.url);
  if (upload.headers) {
    console.log('[uploadToS3] headers=', upload.headers);
  }

  const res = await fetch(upload.url, {
    method: upload.method ?? 'PUT',
    headers: upload.headers,
    body: file,
  });

  if (!res.ok) {
    const text = await res.text().catch(() => '');
    console.error('[uploadToS3][PUT] failed', res.status, text);
    throw new Error(`S3 PUT upload failed: ${res.status}`);
  }
}

/**
 * Высокоуровневая функция:
 * 1) дергает /api/filehub/upload-init/
 * 2) загружает файл в S3/VK Cloud (POST или PUT)
 * 3) дергает /api/filehub/upload-complete/
 * 4) возвращает информацию о файле (UploadCompleteResult)
 */
export async function uploadViaFilehub(
  file: File,
  options: FilehubUploadOptions = {}
): Promise<UploadCompleteResult> {
  const {
    visibility = 'private',
    fileType = 'image',
    contentType = file.type || 'application/octet-stream',
    targetAppLabel,
    targetModel,
    targetObjectId,
    role,
    priority,
    checksum,
  } = options;

  // 1) Инициализация на бэке
  const initPayload = {
    files: [
      {
        original_name: file.name,
        file_type: fileType,
        content_type: contentType,
        visibility,
        target_app_label: targetAppLabel,
        target_model: targetModel,
        target_object_id: targetObjectId,
        role,
        priority,
      },
    ],
  };

  const initResp = await apiFetch<UploadInitResponse>(
    '/api/filehub/upload-init/',
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(initPayload),
    }
  );

  if (!initResp.files || !initResp.files.length) {
    console.error(
      '[uploadViaFilehub] upload-init: пустой список файлов',
      initResp
    );
    throw new Error('Backend не вернул ни одного файла в upload-init');
  }

  const fileInfo = initResp.files[0];
  console.log('[uploadViaFilehub] fileInfo =', fileInfo);

  if (!fileInfo.upload || !fileInfo.upload.url) {
    console.error(
      '[uploadViaFilehub] upload-init: неожиданный формат ответа',
      fileInfo
    );
    throw new Error('Backend не вернул upload.url для загрузки файла.');
  }

  // 2) Загрузка файла в S3/VK Cloud
  await uploadToS3(file, fileInfo.upload);

  // 3) Подтверждение загрузки
  const completePayload: {
    media_file_id: string;
    size_bytes: number;
    checksum?: string;
  } = {
    media_file_id: fileInfo.media_file_id,
    size_bytes: file.size,
  };

  // ВАЖНО: не отправляем checksum: null, иначе DRF ругается.
  if (typeof checksum === 'string') {
    completePayload.checksum = checksum;
  }

  await apiFetch<void>('/api/filehub/upload-complete/', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(completePayload),
  });

  // 4) Возвращаем мету файла (id, key, visibility, upload и т.д.)
  return fileInfo;
}
