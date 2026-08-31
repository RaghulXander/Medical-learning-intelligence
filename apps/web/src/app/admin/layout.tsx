import { Suspense } from 'react';
import { AdminShell } from '@/components/admin/admin-shell';

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  return (
    <Suspense fallback={<div className="min-h-screen bg-slate-950" />}>
      <AdminShell>{children}</AdminShell>
    </Suspense>
  );
}
