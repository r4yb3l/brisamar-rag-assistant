import { memo } from "react";
import type { DocumentOut } from "../api/types";
import { BUSINESS_LINE_LABELS } from "../auth/demoUsers";
import { isDocumentPending, useDocuments } from "../hooks/useDocuments";
import { formatDate } from "../lib/format";
import { ErrorMessage } from "./ErrorMessage";
import { StatusBadge } from "./StatusBadge";

const DocumentItem = memo(function DocumentItem({ document }: { document: DocumentOut }) {
  return (
    <li className="document-item">
      <div className="document-item__main">
        <p className="document-item__title">{document.title}</p>
        <p className="document-item__meta">
          <span className="tag">{BUSINESS_LINE_LABELS[document.business_line] ?? document.business_line}</span>
          <span>v{document.version}</span>
          <span className={document.is_current ? "tag tag--current" : "tag tag--historic"}>
            {document.is_current ? "vigente" : "histórica"}
          </span>
          {document.page_count !== null && <span>{document.page_count} págs.</span>}
          {document.chunk_count !== null && <span>{document.chunk_count} fragmentos</span>}
        </p>
        <p className="document-item__date">
          {document.doc_key} · {formatDate(document.created_at)}
        </p>
        {document.status === "failed" && document.error && <p className="field-error">{document.error}</p>}
      </div>
      <StatusBadge status={document.status} />
    </li>
  );
});

export function DocumentList() {
  const { data, isPending, isError, error, refetch, isFetching } = useDocuments();

  if (isPending) return <p className="muted" role="status">Cargando documentos…</p>;
  if (isError) return <ErrorMessage title="No se pudo cargar la lista de documentos" error={error} onRetry={() => void refetch()} />;
  if (data.items.length === 0) {
    return <p className="empty-state">Todavía no hay documentos en tus líneas. Sube el primer PDF del manual.</p>;
  }

  const pendingCount = data.items.filter(isDocumentPending).length;

  return (
    <>
      <p className="muted list-status" role="status" aria-live="polite">
        {data.items.length} documento{data.items.length === 1 ? "" : "s"}
        {pendingCount > 0 && ` · ${pendingCount} en proceso, actualizando cada 2 s`}
        {isFetching && pendingCount === 0 && " · actualizando…"}
      </p>
      <ul className="document-list">
        {data.items.map((document) => (
          <DocumentItem key={document.id} document={document} />
        ))}
      </ul>
    </>
  );
}
