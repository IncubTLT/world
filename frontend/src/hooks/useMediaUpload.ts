'use client';

import { useCallback, useState } from 'react';
import {
  uploadMediaFile,
  UploadResult,
  MediaVisibility,
} from '@/lib/filehub-api';

type Status = 'idle' | 'uploading' | 'success' | 'error';

export function useMediaUpload(defaultVisibility: MediaVisibility = 'private') {
  const [status, setStatus] = useState<Status>('idle');
  const [progress, setProgress] = useState<number>(0);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<UploadResult | null>(null);

  const upload = useCallback(
    async (file: File, visibility: MediaVisibility = defaultVisibility) => {
      setStatus('uploading');
      setProgress(0);
      setError(null);

      try {
        const res = await uploadMediaFile(file, {
          visibility,
          onProgress: setProgress,
        });

        setResult(res);
        setStatus('success');
        return res;
      } catch (e) {
        console.error(e);
        setStatus('error');
        setResult(null);
        setProgress(0);
        setError(
          e instanceof Error
            ? e.message
            : 'Неизвестная ошибка при загрузке файла.'
        );
        throw e;
      }
    },
    [defaultVisibility]
  );

  return {
    status,
    progress,
    error,
    result,
    upload,
  };
}
