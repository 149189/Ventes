export interface User {
  id: number;
  username: string;
  email: string;
  phone: string;
  role: 'admin' | 'merchant' | 'agent';
  is_verified: boolean;
  created_at: string;
}

export interface LoginCredentials {
  username: string;
  password: string;
}

export interface RegisterData {
  username: string;
  email: string;
  password: string;
  password_confirm: string;
  phone?: string;
}
