import type {
  AskOut,
  AskRequest,
  BusinessLine,
  ChunkOut,
  DocumentList,
  DocumentOut,
  UploadDocumentInput,
} from "./types";

export const API_BASE_URL = (import.meta.env.VITE_API_URL || "http://localhost:8000").replace(/\/+$/, "");

export class ApiError extends Error {
  readonly status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

const STATUS_FALLBACK_MESSAGES: Record<number, string> = {
  401: "Token no válido o ausente.",
  403: "Tu usuario no tiene acceso a esta línea de negocio.",
  404: "El recurso solicitado no existe.",
  413: "El archivo supera el tamaño máximo permitido.",
  415: "Formato de archivo no admitido. Solo se aceptan PDF.",
  422: "La solicitud contiene datos no válidos.",
};

interface ValidationIssue {
  msg?: unknown;
  loc?: unknown;
}

function describeDetail(detail: unknown): string | null {
  if (typeof detail === "string" && detail.trim()) return detail;
  if (Array.isArray(detail)) {
    const messages = detail
      .map((issue: ValidationIssue) => {
        const message = typeof issue?.msg === "string" ? issue.msg : null;
        const field = Array.isArray(issue?.loc) ? issue.loc.slice(1).join(".") : "";
        if (!message) return null;
        return field ? `${field}: ${message}` : message;
      })
      .filter((message): message is string => Boolean(message));
    return messages.length ? messages.join("; ") : null;
  }
  if (detail && typeof detail === "object") {
    const nested = (detail as { message?: unknown }).message;
    if (typeof nested === "string") return nested;
  }
  return null;
}

async function toApiError(response: Response): Promise<ApiError> {
  let detail: unknown = null;
  try {
    const body: unknown = await response.json();
    detail = body && typeof body === "object" ? (body as { detail?: unknown }).detail : null;
  } catch {
    detail = null;
  }
  const message =
    describeDetail(detail) ??
    STATUS_FALLBACK_MESSAGES[response.status] ??
    `El servidor respondió ${response.status} ${response.statusText}`.trim();
  return new ApiError(response.status, message);
}

async function request<T>(token: string, path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("Authorization", `Bearer ${token}`);
  headers.set("Accept", "application/json");

  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}/api${path}`, { ...init, headers });
  } catch {
    throw new ApiError(0, `No se pudo conectar con el servidor en ${API_BASE_URL}.`);
  }

  if (!response.ok) throw await toApiError(response);
  return (await response.json()) as T;
}

export function listDocuments(token: string, businessLine?: BusinessLine): Promise<DocumentList> {
  const query = businessLine ? `?business_line=${encodeURIComponent(businessLine)}` : "";
  return request<DocumentList>(token, `/documents${query}`);
}

export function getDocument(token: string, id: string): Promise<DocumentOut> {
  return request<DocumentOut>(token, `/documents/${encodeURIComponent(id)}`);
}

export function uploadDocument(token: string, input: UploadDocumentInput): Promise<DocumentOut> {
  const form = new FormData();
  form.append("file", input.file);
  form.append("business_line", input.businessLine);
  if (input.title?.trim()) form.append("title", input.title.trim());
  if (input.docKey?.trim()) form.append("doc_key", input.docKey.trim());
  return request<DocumentOut>(token, "/documents", { method: "POST", body: form });
}

export function askQuestion(token: string, payload: AskRequest): Promise<AskOut> {
  return request<AskOut>(token, "/ask", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export function getChunk(token: string, chunkId: string): Promise<ChunkOut> {
  return request<ChunkOut>(token, `/chunks/${encodeURIComponent(chunkId)}`);
}
