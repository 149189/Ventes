'use client';

import { useAuth } from '@/hooks/useAuth';
import Button from '@/components/ui/Button';

export default function Header() {
  const { user, logout } = useAuth();

  return (
    <header className="bg-white border-b border-gray-200 px-6 py-3 flex items-center justify-between">
      <div />
      <div className="flex items-center gap-4">
        {user && (
          <>
            <span className="text-sm text-gray-600">
              {user.email}
            </span>
            <Button variant="secondary" size="sm" onClick={logout}>
              Logout
            </Button>
          </>
        )}
      </div>
    </header>
  );
}
