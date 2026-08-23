'use client';

import React, { useEffect } from 'react';

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error('Global Error caught:', error);
  }, [error]);

  return (
    <html lang="en" className="dark">
      <body className="min-h-screen bg-slate-950 text-white flex items-center justify-center p-6">
        <div className="text-center max-w-md">
          <h2 className="text-2xl font-bold mb-2">Something went wrong</h2>
          <p className="text-sm text-slate-400 mb-6">{error?.message || 'An unexpected application error occurred.'}</p>
          <button
            onClick={() => reset()}
            className="px-4 py-2 bg-sky-500 hover:bg-sky-400 text-white rounded-xl font-semibold text-sm transition-colors"
          >
            Try again
          </button>
        </div>
      </body>
    </html>
  );
}
