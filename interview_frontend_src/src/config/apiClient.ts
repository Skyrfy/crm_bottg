import { API_BASE_URL } from "./api";

declare global {
  interface Window {
    Telegram?: {
      WebApp?: {
        initData?: string;
      };
    };
  }
}

const tg = () => window.Telegram?.WebApp;

const getInitData = (): string => tg()?.initData ?? '';

export async function apiFetch(path: string, options: RequestInit = {}): Promise<Response> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    'X-Telegram-Init-Data': getInitData(),
    ...(options.headers as Record<string, string> ?? {}),
  };
  return fetch(`${API_BASE_URL}${path}`, { ...options, headers });
}
