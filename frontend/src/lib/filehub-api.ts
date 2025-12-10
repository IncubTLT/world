import { API_BASE_URL, ApiError } from './api';

export type MediaVisibility = 'private' | 'public';

export interface MediaFileDto {
  id: number;
  url: string;
  original_name: string;
  size: number;
}

export interface UploadResult {
  media: MediaFileDto;
}

export async function uploadMediaFile(
  file: File,
  opts?: {
    visibility?: MediaVisibility;
    signal?: AbortSignal;
    onProgress?(percent: number): void;
  }
): Promise<UploadResult> {
  return new Promise((resolve, reject) => {
    const formData = new FormData();
    formData.append('file', file);
    if (opts?.visibility) {
      formData.append('visibility', opts.visibility);
    }

    const xhr = new XMLHttpRequest();
    xhr.open('POST', `${API_BASE_URL}/api/filehub/uploads/`);
    xhr.withCredentials = true;

    if (xhr.upload && opts?.onProgress) {
      xhr.upload.onprogress = (event) => {
        if (!event.lengthComputable) return;
        const percent = Math.round((event.loaded / event.total) * 100);
        opts.onProgress?.(percent);
      };
    }

    xhr.onreadystatechange = () => {
      if (xhr.readyState !== XMLHttpRequest.DONE) return;

      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          const data = JSON.parse(xhr.responseText) as UploadResult;
          resolve(data);
        } catch (e) {
          reject(
            new Error('Не удалось разобрать ответ сервера при загрузке файла.')
          );
        }
      } else {
        reject(new ApiError(xhr.status, xhr.responseText));
      }
    };

    if (opts?.signal) {
      opts.signal.addEventListener('abort', () => {
        xhr.abort();
        reject(new DOMException('Загрузка отменена', 'AbortError'));
      });
    }

    xhr.onerror = () => {
      reject(new Error('Ошибка сети при загрузке файла.'));
    };

    xhr.send(formData);
  });
}
