import type { Metadata } from 'next';
import '@/styles/globals.css';
import { AuthProvider } from '@/lib/auth-context';
import { SiteChrome } from '@/components/site-chrome';

export const metadata: Metadata = {
  title: 'DocEdge — Medical Exam AI & Pathology Intelligence',
  description:
    'Scalable Medical Education, Universal Question Bank & Mock Exam Platform for NEET-PG, NEET-SS Oncopathology, and INI-CET.',
};

import Script from 'next/script';

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <head>
        <Script src="https://accounts.google.com/gsi/client" strategy="lazyOnload" />
      </head>
      <body className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans antialiased">
        <AuthProvider>
          <SiteChrome>{children}</SiteChrome>
        </AuthProvider>
      </body>
    </html>
  );
}
