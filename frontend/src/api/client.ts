const BASE_URL = import.meta.env.VITE_API_URL ?? "/api";

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function apiRequest<T>(
  endpoint: string,
  options: RequestInit = {},
): Promise<T> {
  const { body, headers: customHeaders, ...rest } = options;
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(customHeaders as Record<string, string>),
  };
  const config: RequestInit = { ...rest, headers, credentials: "include" };
  if (body !== undefined) {
    config.body = typeof body === "string" ? body : JSON.stringify(body);
  }
  const response = await fetch(`${BASE_URL}${endpoint}`, config);
  if (!response.ok) {
    // Redirect to login on 401, except for auth endpoints (including /auth/me
    // which is called on mount — without this exclusion, unauthenticated users
    // would hit an infinite reload loop)
    if (response.status === 401 && !endpoint.startsWith("/auth/")) {
      window.location.href = "/login";
      return undefined as T;
    }
    const errorBody = await response.json().catch(() => null);
    const message =
      errorBody?.detail ?? errorBody?.message ?? response.statusText;
    throw new ApiError(response.status, message);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export const api = {
  get: <T>(endpoint: string) =>
    apiRequest<T>(endpoint, { method: "GET" }),
  post: <T>(endpoint: string, body?: unknown) =>
    apiRequest<T>(endpoint, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  put: <T>(endpoint: string, body?: unknown) =>
    apiRequest<T>(endpoint, {
      method: "PUT",
      body: JSON.stringify(body),
    }),
  delete: <T>(endpoint: string) =>
    apiRequest<T>(endpoint, { method: "DELETE" }),
};
