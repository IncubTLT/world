'use client';

import { useCallback, useState } from 'react';
import { uploadViaFilehub } from '@/lib/filehub';
import type { FilehubUploadOptions, UploadCompleteResult } from '@/lib/filehub';

type Status = 'idle' | 'uploading' | 'success' | 'error';

export function useFilehubUpload(defaultOptions?: FilehubUploadOptions) {
  const [status, setStatus] = useState<Status>('idle');
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<UploadCompleteResult | null>(null);

  const upload = useCallback(
    async (file: File, overrides?: FilehubUploadOptions) => {
      setStatus('uploading');
      setError(null);
      setResult(null);

      try {
        const res = await uploadViaFilehub(file, {
          ...defaultOptions,
          ...overrides,
        });
        setResult(res);
        setStatus('success');
        return res;
      } catch (e) {
        console.error(e);
        setStatus('error');
        setResult(null);
        setError(
          e instanceof Error ? e.message : 'Неизвестная ошибка при загрузке.'
        );
        throw e;
      }
    },
    [defaultOptions]
  );

  return {
    status,
    error,
    result,
    upload,
  };
}
