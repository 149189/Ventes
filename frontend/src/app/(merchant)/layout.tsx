'use client';

import Sidebar from '@/components/layout/Sidebar';
import Header from '@/components/layout/Header';

export default function MerchantLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen">
      <Sidebar role="merchant" />
      <div className="flex-1">
        <Header />
        <main className="p-6">{children}</main>
      </div>
    </div>
  );
}
