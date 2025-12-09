'use client';
import { CORE_CLIENT_BACKEND } from '@/common/network/core-client';
import Image from 'next/image';
import { useEffect } from 'react';
import { FileUploadButton } from '@/components/filehub/FileUploadButton';

export const Home = () => {
  useEffect(() => {
    CORE_CLIENT_BACKEND.core_backend.get('/').then((res) => {
      console.log(res);
    });
  }, []);

  return (
    <main className="min-h-screen flex items-center justify-center bg-slate-950">
      <div className="center flex-col">
        <p className="text-4xl font-bold">DCL</p>
        <Image
          src="/page/home/hi.JPG"
          className="rounded w-80 h-96"
          fetchPriority="high"
          priority
          alt="hi"
          width={600}
          height={700}
        />
      </div>

      <div className="p-6 rounded-2xl bg-slate-900 shadow-xl space-y-4 max-w-lg w-full">
        <h1 className="text-xl font-semibold text-slate-50">
          Загрузка файлов в filehub
        </h1>

        <p className="text-sm text-slate-300">
          Выбери файл — он уйдёт в S3/MinIO через presigned POST, потом backend
          получит уведомление через <code>upload-complete</code>.
        </p>

        <FileUploadButton
          label="Загрузить аватар"
          visibility="private"
          fileType="image"
          targetAppLabel="users"
          targetModel="user"
          targetObjectId={42}
          role="avatar"
          priority={10}
          onUploaded={(res) => {
            console.log('Файл загружен:', res);
          }}
        />
      </div>
    </main>
  );
};
