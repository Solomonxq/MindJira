const API_BASE = import.meta.env.VITE_API_BASE_URL || "/api";

function getStatusMessage(status: number): string {
  switch (status) {
    case 400:
      return "Некоректний запит. Перевірте введені дані.";
    case 401:
      return "Сесія закінчилася. Увійдіть ще раз.";
    case 403:
      return "Недостатньо прав для цієї операції.";
    case 404:
      return "Не знайдено. Перевірте ключ тікета або параметри.";
    case 409:
      return "Конфлікт даних. Можливо, ресурс вже існує.";
    case 422:
      return "Помилка валідації. Перевірте формат даних.";
    case 429:
      return "Занадто багато запитів. Спробуйте пізніше.";
    case 500:
      return "Внутрішня помилка сервера. Спробуйте пізніше.";
    case 502:
      return "Сервіс тимчасово недоступний. Перевірте стан сервісів.";
    case 503:
      return "Сервіс перевантажений або недоступний.";
    default:
      return `Помилка сервера (HTTP ${status}).`;
  }
}

export class ApiError extends Error {
  constructor(
    public status: number,
    public rawMessage: string
  ) {
    super(`HTTP ${status}: ${rawMessage}`);
    this.name = "ApiError";
  }

  getUserMessage(): string {
    const statusText = this.status > 0 ? `[HTTP ${this.status}] ` : "";
    const message = this.rawMessage || getStatusMessage(this.status);
    return `${statusText}${message}`;
  }
}

async function parseError(response: Response): Promise<string> {
  const text = await response.text().catch(() => "");

  try {
    const data = JSON.parse(text);
    if (typeof data.detail === "string") return data.detail;
    if (typeof data.message === "string") return data.message;
    if (Array.isArray(data.detail)) {
      return data.detail.map((item: unknown) => {
        if (typeof item === "string") return item;
        if (item && typeof item === "object" && "msg" in item) {
          return (item as { msg: string }).msg;
        }
        return String(item);
      }).join("; ");
    }
  } catch {
    // Not JSON, use text as is
  }

  return text || getStatusMessage(response.status);
}

async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const token = localStorage.getItem("mj_token");
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...(options.headers as Record<string, string>),
  };

  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      ...options,
      headers,
    });
  } catch {
    throw new ApiError(0, "Не вдалося підключитися до сервера. Перевірте з'єднання.");
  }

  if (!response.ok) {
    const message = await parseError(response);
    throw new ApiError(response.status, message);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

export function getErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    return error.getUserMessage();
  }
  if (error instanceof Error) {
    return error.message;
  }
  return "Сталася невідома помилка.";
}

export const api = {
  auth: {
    login: (email: string, password: string) =>
      request<{ access_token: string }>("/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      }),
    register: (email: string, password: string, full_name?: string) =>
      request("/auth/register", {
        method: "POST",
        body: JSON.stringify({ email, password, full_name }),
      }),
    me: () =>
      request<{ id: string; email: string; full_name: string | null; role: string }>("/auth/me"),
  },
  enrich: {
    generate: (issueKey: string, language?: string) =>
      request<{ issue_key: string; generated_description: string; applied_to_jira: boolean }>(
        `/description-enricher/enrich/${issueKey}${language ? `?language=${language}` : ""}`,
        { method: "POST" }
      ),
  },
  testCases: {
    generate: (issueKey: string, language?: string) =>
      request<{ issue_key: string; test_cases_markdown: string }>(
        `/test-case-generator/generate/${issueKey}${language ? `?language=${language}` : ""}`,
        { method: "POST" }
      ),
  },
  sprintSummary: {
    report: (sprintId: number) =>
      request<{ report: string }>(`/sprint-summary/report/sprint/${sprintId}`, {
        method: "POST",
      }),
    health: (days: number) =>
      request<{ report: string }>(`/sprint-summary/report/health?days=${days}`, {
        method: "POST",
      }),
  },
  gateway: {
    jobs: (limit = 50) =>
      request<Array<{
        id: string;
        service_name: string;
        trigger_type: string;
        status: string;
        created_at: string;
      }>>(`/gateway/jobs/history?limit=${limit}`),
    runJob: (serviceName: string, jql?: string, issueKeys?: string[]) =>
      request("/gateway/jobs/run", {
        method: "POST",
        body: JSON.stringify({
          service_name: serviceName,
          jql,
          issue_keys: issueKeys || [],
        }),
      }),
  },
};
