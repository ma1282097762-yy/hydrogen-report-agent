const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://127.0.0.1:8000";

export class ApiError extends Error {
  code: string;
  constructor(code: string, message: string) {
    super(message);
    this.name = "ApiError";
    this.code = code;
  }
}

export function extractApiError(
  data: unknown,
  status: number,
): { code: string; message: string } {
  const body = (data || {}) as { error?: { code?: string; message?: string } };
  return {
    code: body.error?.code || `HTTP_${status}`,
    message: body.error?.message || `请求失败（${status}）`,
  };
}

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
  });
  let data: unknown = null;
  try {
    data = await res.json();
  } catch {
    data = null;
  }
  if (!res.ok) {
    const { code, message } = extractApiError(data, res.status);
    throw new ApiError(code, message);
  }
  return data as T;
}
