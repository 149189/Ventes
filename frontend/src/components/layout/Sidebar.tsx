'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { cn } from '@/lib/utils';

interface NavItem {
  label: string;
  href: string;
  icon: string;
}

const merchantNav: NavItem[] = [
  { label: 'Dashboard', href: '/dashboard', icon: '📊' },
  { label: 'Campaigns', href: '/campaigns', icon: '📢' },
  { label: 'Products', href: '/products', icon: '📦' },
  { label: 'Clicks', href: '/clicks', icon: '🔗' },
  { label: 'Billing', href: '/billing', icon: '💳' },
  { label: 'Disputes', href: '/disputes', icon: '⚖️' },
  { label: 'Settings', href: '/settings', icon: '⚙️' },
];

const adminNav: NavItem[] = [
  { label: 'Dashboard', href: '/admin/dashboard', icon: '📊' },
  { label: 'Merchants', href: '/admin/merchants', icon: '🏪' },
  { label: 'Conversations', href: '/admin/conversations', icon: '💬' },
  { label: 'Clicks', href: '/admin/clicks', icon: '🔗' },
  { label: 'Campaigns', href: '/admin/campaigns', icon: '📢' },
  { label: 'Billing', href: '/admin/billing', icon: '💰' },
  { label: 'Settings', href: '/admin/settings', icon: '⚙️' },
];

interface SidebarProps {
  role: 'merchant' | 'admin';
}

export default function Sidebar({ role }: SidebarProps) {
  const pathname = usePathname();
  const navItems = role === 'admin' ? adminNav : merchantNav;

  return (
    <aside className="w-64 bg-white border-r border-gray-200 min-h-screen p-4">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">
          Sales<span className="text-primary-600">Count</span>
        </h1>
        <p className="text-xs text-gray-500 mt-1">
          {role === 'admin' ? 'Admin Panel' : 'Merchant Portal'}
        </p>
      </div>

      <nav className="space-y-1">
        {navItems.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className={cn(
              'flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors',
              pathname === item.href || pathname.startsWith(item.href + '/')
                ? 'bg-primary-50 text-primary-700'
                : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900',
            )}
          >
            <span>{item.icon}</span>
            {item.label}
          </Link>
        ))}
      </nav>
    </aside>
  );
}
