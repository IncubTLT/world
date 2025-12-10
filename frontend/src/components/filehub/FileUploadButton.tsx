'use client';

import { ChangeEvent, useRef } from 'react';
import { useFilehubUpload } from '@/hooks/useFilehubUpload';
import type {
  FileKind,
  MediaVisibility,
  FilehubUploadOptions,
  UploadCompleteResult,
} from '@/lib/filehub';

type Props = {
  label?: string;
  visibility?: MediaVisibility;
  fileType?: FileKind;
  targetAppLabel?: string;
  targetModel?: string;
  targetObjectId?: number;
  role?: string;
  priority?: number;
  onUploaded?(result: UploadCompleteResult): void;
};

export function FileUploadButton({
  label = 'Загрузить файл',
  visibility = 'private',
  fileType = 'image',
  targetAppLabel,
  targetModel,
  targetObjectId,
  role,
  priority,
  onUploaded,
}: Props) {
  const inputRef = useRef<HTMLInputElement | null>(null);

  const baseOptions: FilehubUploadOptions = {
    visibility,
    fileType, // 👈 кладём в options именно fileType, не kind
    targetAppLabel,
    targetModel,
    targetObjectId,
    role,
    priority,
  };

  const { status, error, result, upload } = useFilehubUpload(baseOptions);

  const handleChange = async (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    try {
      const res = await upload(file);
      onUploaded?.(res);
    } finally {
      // чтобы можно было выбрать тот же файл ещё раз
      if (inputRef.current) {
        inputRef.current.value = '';
      }
    }
  };

  const busy = status === 'uploading';

  return (
    <div className="flex flex-col gap-2 text-sm text-slate-100">
      <button
        type="button"
        className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 disabled:bg-slate-700/70 disabled:cursor-not-allowed transition-colors"
        onClick={() => inputRef.current?.click()}
        disabled={busy}
      >
        {busy ? 'Загрузка...' : label}
      </button>

      <input
        ref={inputRef}
        type="file"
        className="hidden"
        onChange={handleChange}
      />

      {status === 'success' && result && (
        <div className="text-xs text-emerald-400">
          Файл успешно загружен (media_file_id: {String(result.media_file_id)})
        </div>
      )}

      {status === 'error' && error && (
        <div className="text-xs text-red-400">Ошибка: {error}</div>
      )}
    </div>
  );
}
