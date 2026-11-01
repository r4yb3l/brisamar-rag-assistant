import type { DocumentStatus } from "../api/types";

const STATUS_LABELS: Record<DocumentStatus, string> = {
  queued: "En cola",
  processing: "Procesando",
  ready: "Listo",
  failed: "Error",
};

export function StatusBadge({ status }: { status: DocumentStatus }) {
  return (
    <span className={`badge badge--${status}`} data-status={status}>
      {(status === "queued" || status === "processing") && <span className="badge__pulse" aria-hidden="true" />}
      {STATUS_LABELS[status]}
    </span>
  );
}
