import api from './api';
import type { User, LoginCredentials, RegisterData } from '@/types/auth';

export async function login(credentials: LoginCredentials) {
  const response = await api.post('/auth/login/', credentials);
  const { access, refresh } = response.data;
  localStorage.setItem('access_token', access);
  localStorage.setItem('refresh_token', refresh);
  return response.data;
}

export async function register(data: RegisterData) {
  const response = await api.post('/auth/register/', data);
  return response.data;
}

export async function getMe(): Promise<User> {
  const response = await api.get('/auth/me/');
  return response.data;
}

export function logout() {
  localStorage.removeItem('access_token');
  localStorage.removeItem('refresh_token');
  window.location.href = '/login';
}

export function isAuthenticated(): boolean {
  if (typeof window === 'undefined') return false;
  return !!localStorage.getItem('access_token');
}
