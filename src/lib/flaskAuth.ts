export type FlaskRole = 'customer' | 'seller' | 'rider' | 'admin' | 'super_admin' | 'support';

export interface FlaskUser {
  id: number;
  email: string;
  role: FlaskRole;
  is_active: boolean;
  preferred_locale: string | null;
  is_totp_enabled?: boolean;
}

export type LoginResult =
  | { status: 'authenticated'; user: FlaskUser }
  | { status: 'two_factor_required'; challengeId: string; expiresAt: string };

export interface TwoFactorStatus {
  enabled: boolean;
  confirmed_at: string | null;
  backup_codes_remaining: number;
}

export interface TwoFactorSetupData {
  secret: string;
  provisioning_uri: string;
  backup_codes: string[];
}

interface ApiResponse<T> {
  success: boolean;
  data?: T;
  message?: string;
  two_factor_required?: boolean;
  error?: {
    code?: string;
    message?: string;
  };
}

export class FlaskAuthError extends Error {
  readonly status: number;
  readonly code?: string;

  constructor(message: string, status: number, code?: string) {
    super(message);
    this.name = 'FlaskAuthError';
    this.status = status;
    this.code = code;
  }
}

let csrfToken: string | null = null;

export function getFlaskAuthOrigin(): string {
  const configuredOrigin = import.meta.env.VITE_FLASK_API_ORIGIN?.trim();
  if (configuredOrigin) return configuredOrigin.replace(/\/+$/, '');
  return window.location.origin;
}

async function request<T>(
  path: string,
  init: RequestInit = {},
  retryAfterCsrfFailure = true,
): Promise<T> {
  const method = (init.method || 'GET').toUpperCase();
  const headers = new Headers(init.headers);
  if (init.body && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }
  if (method !== 'GET' && method !== 'HEAD') {
    if (!csrfToken) await getCsrfToken();
    if (csrfToken) headers.set('X-CSRFToken', csrfToken);
  }

  const response = await fetch(`${getFlaskAuthOrigin()}${path}`, {
    ...init,
    headers,
    credentials: 'include',
  });
  const payload = (await response.json().catch(() => ({}))) as ApiResponse<T>;

  if (response.status === 403 && payload.error?.code === 'CSRF_ERROR' && retryAfterCsrfFailure) {
    csrfToken = null;
    return request<T>(path, init, false);
  }
  if (!response.ok || !payload.success) {
    throw new FlaskAuthError(
      payload.error?.message || payload.message || 'The authentication request failed.',
      response.status,
      payload.error?.code,
    );
  }
  return payload.data as T;
}

export async function getCsrfToken(): Promise<string> {
  const data = await request<{ csrf_token: string }>('/api/v1/auth/csrf');
  csrfToken = data.csrf_token;
  return csrfToken;
}

export async function getCurrentFlaskUser(): Promise<FlaskUser | null> {
  try {
    return await request<FlaskUser>('/api/v1/auth/me');
  } catch (error) {
    if (error instanceof FlaskAuthError && error.status === 401) return null;
    throw error;
  }
}

export async function loginWithFlask(email: string, password: string): Promise<LoginResult> {
  const headers = new Headers();
  headers.set('Content-Type', 'application/json');
  if (!csrfToken) await getCsrfToken();
  if (csrfToken) headers.set('X-CSRFToken', csrfToken);

  const response = await fetch(`${getFlaskAuthOrigin()}/api/v1/auth/login`, {
    method: 'POST',
    headers,
    credentials: 'include',
    body: JSON.stringify({ email, password }),
  });

  const payload = (await response.json().catch(() => ({}))) as ApiResponse<FlaskUser>;

  if (response.status === 202 || payload.two_factor_required) {
    const challengeData = (payload.data as unknown as { challenge_id?: string; expires_at?: string }) || {};
    return {
      status: 'two_factor_required',
      challengeId: challengeData.challenge_id || '',
      expiresAt: challengeData.expires_at || '',
    };
  }

  if (!response.ok || !payload.success) {
    throw new FlaskAuthError(
      payload.error?.message || payload.message || 'The authentication request failed.',
      response.status,
      payload.error?.code,
    );
  }

  return {
    status: 'authenticated',
    user: payload.data as FlaskUser,
  };
}

export async function verifyTwoFactorChallenge(code: string): Promise<FlaskUser> {
  return request<FlaskUser>('/api/v1/auth/2fa/challenge', {
    method: 'POST',
    body: JSON.stringify({ code }),
  });
}

export async function getTwoFactorStatus(): Promise<TwoFactorStatus> {
  return request<TwoFactorStatus>('/api/v1/auth/2fa/status');
}

export async function startTwoFactorSetup(): Promise<TwoFactorSetupData> {
  return request<TwoFactorSetupData>('/api/v1/auth/2fa/setup', {
    method: 'POST',
  });
}

export async function confirmTwoFactorSetup(code: string): Promise<boolean> {
  const res = await request<{ two_factor_enabled: boolean }>('/api/v1/auth/2fa/confirm', {
    method: 'POST',
    body: JSON.stringify({ code }),
  });
  return res.two_factor_enabled;
}

export async function regenerateBackupCodes(password?: string, code?: string): Promise<string[]> {
  const res = await request<{ backup_codes: string[] }>('/api/v1/auth/2fa/regenerate-backup-codes', {
    method: 'POST',
    body: JSON.stringify({ password, code }),
  });
  return res.backup_codes;
}

export async function disableTwoFactor(password?: string, code?: string): Promise<boolean> {
  const res = await request<{ two_factor_enabled: boolean }>('/api/v1/auth/2fa/disable', {
    method: 'POST',
    body: JSON.stringify({ password, code }),
  });
  return res.two_factor_enabled;
}

export async function logoutFromFlask(): Promise<void> {
  await request<unknown>('/api/v1/auth/logout', { method: 'POST' });
  csrfToken = null;
}

export interface RegistrationRequest {
  role: 'customer' | 'seller';
  email: string;
  full_name: string;
  phone: string;
  password: string;
  store_name?: string;
  business_address?: string;
}

export async function startFlaskRegistration(requestBody: RegistrationRequest): Promise<void> {
  await request<{ email: string; expires_at: string }>('/api/v1/auth/register', {
    method: 'POST',
    body: JSON.stringify(requestBody),
  });
}

export function redirectToFlaskRegistrationVerification(): void {
  window.location.assign(`${getFlaskAuthOrigin()}/auth/verify-registration`);
}
