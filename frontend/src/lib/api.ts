/**
 * Typed client for the SplitBill API.
 *
 * Every failure, including "server unreachable", becomes an ApiError with a
 * machine-readable `code`, so the UI can turn it into plain language in one
 * place (see errors.ts).
 */
import { API_BASE } from "./config";
import type {
  BalancesResponse,
  Expense,
  Group,
  GroupDetail,
  NewExpense,
} from "./types";

export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly code: string,
    message: string,
    readonly details: Record<string, unknown> = {},
  ) {
    super(message);
    this.name = "ApiError";
  }
}

type RequestOptions = {
  method?: "GET" | "POST" | "DELETE";
  body?: unknown;
  idempotencyKey?: string;
  signal?: AbortSignal;
};

async function request<T>(
  user: string,
  path: string,
  { method = "GET", body, idempotencyKey, signal }: RequestOptions = {},
): Promise<T> {
  const headers: Record<string, string> = { "X-User": user };
  if (body !== undefined) headers["Content-Type"] = "application/json";
  if (idempotencyKey) headers["Idempotency-Key"] = idempotencyKey;

  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
      signal,
      cache: "no-store",
    });
  } catch (cause) {
    if (signal?.aborted) throw cause; // caller cancelled; not an error to show
    throw new ApiError(0, "NETWORK_ERROR", "Could not reach the server");
  }

  if (response.status === 204) return undefined as T;

  const payload: unknown = await response.json().catch(() => null);
  if (!response.ok) throw toApiError(response.status, payload);
  return payload as T;
}

/** Accept our error envelope, and FastAPI's default `{detail}` as a fallback. */
function toApiError(status: number, payload: unknown): ApiError {
  if (isRecord(payload) && isRecord(payload.error)) {
    const { code, message, details } = payload.error;
    return new ApiError(
      status,
      typeof code === "string" ? code : `HTTP_${status}`,
      typeof message === "string" ? message : "",
      isRecord(details) ? details : {},
    );
  }
  if (isRecord(payload) && "detail" in payload) {
    const detail = payload.detail;
    return new ApiError(
      status,
      status === 422 ? "VALIDATION_ERROR" : `HTTP_${status}`,
      typeof detail === "string" ? detail : "",
    );
  }
  return new ApiError(status, `HTTP_${status}`, "");
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

const groupPath = (groupId: number) => `/groups/${encodeURIComponent(groupId)}`;

export const api = {
  listGroups: (user: string, signal?: AbortSignal) =>
    request<Group[]>(user, "/groups", { signal }),

  getGroup: (user: string, groupId: number, signal?: AbortSignal) =>
    request<GroupDetail>(user, groupPath(groupId), { signal }),

  listExpenses: (user: string, groupId: number, signal?: AbortSignal) =>
    request<Expense[]>(user, `${groupPath(groupId)}/expenses`, { signal }),

  getBalances: (user: string, groupId: number, signal?: AbortSignal) =>
    request<BalancesResponse>(user, `${groupPath(groupId)}/balances`, { signal }),

  createExpense: (
    user: string,
    groupId: number,
    expense: NewExpense,
    idempotencyKey: string,
  ) =>
    request<Expense>(user, `${groupPath(groupId)}/expenses`, {
      method: "POST",
      body: expense,
      idempotencyKey,
    }),

  deleteExpense: (user: string, groupId: number, expenseId: number) =>
    request<void>(
      user,
      `${groupPath(groupId)}/expenses/${encodeURIComponent(expenseId)}`,
      { method: "DELETE" },
    ),
};
