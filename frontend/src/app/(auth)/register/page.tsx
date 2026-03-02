'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { register } from '@/lib/auth';
import Button from '@/components/ui/Button';
import Input from '@/components/ui/Input';

export default function RegisterPage() {
  const router = useRouter();
  const [form, setForm] = useState({
    username: '',
    email: '',
    password: '',
    password_confirm: '',
    phone: '',
  });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError('');

    if (form.password !== form.password_confirm) {
      setError('Passwords do not match');
      return;
    }

    setLoading(true);

    try {
      await register(form);
      router.push('/login?registered=true');
    } catch (err: any) {
      const data = err.response?.data;
      if (data) {
        const messages = Object.values(data).flat().join(', ');
        setError(messages as string);
      } else {
        setError('Registration failed. Please try again.');
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="card">
      <h2 className="text-xl font-semibold text-center mb-6">Create Account</h2>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mb-4 text-sm">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        <Input
          id="username"
          label="Username"
          value={form.username}
          onChange={(e) => setForm({ ...form, username: e.target.value })}
          required
        />
        <Input
          id="email"
          label="Email"
          type="email"
          value={form.email}
          onChange={(e) => setForm({ ...form, email: e.target.value })}
          required
        />
        <Input
          id="phone"
          label="Phone (optional)"
          type="tel"
          value={form.phone}
          onChange={(e) => setForm({ ...form, phone: e.target.value })}
        />
        <Input
          id="password"
          label="Password"
          type="password"
          value={form.password}
          onChange={(e) => setForm({ ...form, password: e.target.value })}
          required
        />
        <Input
          id="password_confirm"
          label="Confirm Password"
          type="password"
          value={form.password_confirm}
          onChange={(e) => setForm({ ...form, password_confirm: e.target.value })}
          required
        />
        <Button type="submit" className="w-full" loading={loading}>
          Create Account
        </Button>
      </form>

      <p className="text-center text-sm text-gray-600 mt-4">
        Already have an account?{' '}
        <Link href="/login" className="text-primary-600 hover:underline">
          Log In
        </Link>
      </p>
    </div>
  );
}
