'use client';

import Sidebar from '@/components/layout/Sidebar';
import Header from '@/components/layout/Header';

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen">
      <Sidebar role="admin" />
      <div className="flex-1">
        <Header />
        <main className="p-6">{children}</main>
      </div>
    </div>
  );
}
