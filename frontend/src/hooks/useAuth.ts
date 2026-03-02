'use client';

import { useState, useEffect } from 'react';
import { getMe, isAuthenticated, logout } from '@/lib/auth';
import type { User } from '@/types/auth';

export function useAuth() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchUser() {
      if (!isAuthenticated()) {
        setLoading(false);
        return;
      }

      try {
        const me = await getMe();
        setUser(me);
      } catch {
        logout();
      } finally {
        setLoading(false);
      }
    }

    fetchUser();
  }, []);

  return { user, loading, logout };
}
