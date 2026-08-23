import type { Metadata } from 'next';
import '@/styles/globals.css';
import { Navbar } from '@/components/navbar';
import { Footer } from '@/components/footer';

export const metadata: Metadata = {
  title: 'DocEdge — Medical Exam AI & Pathology Intelligence',
  description:
    'Scalable Medical Education, Universal Question Bank & Mock Exam Platform for NEET-PG, NEET-SS Oncopathology, and INI-CET.',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans antialiased">
        <Navbar />
        <main className="flex-1">{children}</main>
        <Footer />
      </body>
    </html>
  );
}
