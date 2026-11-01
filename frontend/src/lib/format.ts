import type { Citation } from "../api/types";

const dateFormatter = new Intl.DateTimeFormat("es-ES", { dateStyle: "short", timeStyle: "short" });

export function formatDate(iso: string): string {
  const date = new Date(iso);
  return Number.isNaN(date.getTime()) ? iso : dateFormatter.format(date);
}

export function formatCitationLabel(citation: Pick<Citation, "title" | "version" | "page">): string {
  const parts = [citation.title, `v${citation.version}`];
  if (citation.page !== null) parts.push(`pág. ${citation.page}`);
  return parts.join(" · ");
}

export type ConfidenceLevel = "high" | "medium" | "low";

export function confidenceLevel(confidence: number): ConfidenceLevel {
  if (confidence >= 0.75) return "high";
  if (confidence >= 0.5) return "medium";
  return "low";
}

export const CONFIDENCE_LABELS: Record<ConfidenceLevel, string> = {
  high: "Alta",
  medium: "Media",
  low: "Baja",
};

const REFUSAL_REASON_LABELS: Record<string, string> = {
  no_relevant_evidence: "Ningún fragmento de los documentos a los que tienes acceso es lo bastante relevante para esta pregunta.",
  model_insufficient_evidence: "Los fragmentos encontrados no contienen la información necesaria para responder.",
  ungrounded_answer: "La respuesta generada no se apoyaba en citas verificables, así que se descartó.",
  invalid_model_output: "El modelo devolvió una respuesta con un formato no válido, incluso tras reintentarlo.",
};

export function describeRefusalReason(reason: string): string {
  return REFUSAL_REASON_LABELS[reason] ?? reason;
}

export function toPercent(value: number): number {
  return Math.round(Math.min(1, Math.max(0, value)) * 100);
}
