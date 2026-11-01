import { useId, useRef } from "react";
import type { Citation } from "../api/types";
import { useChunk } from "../hooks/useAsk";
import { useDialogFocus } from "../hooks/useDialogFocus";
import { formatCitationLabel } from "../lib/format";
import { ErrorMessage } from "./ErrorMessage";

interface ChunkPanelProps {
  citation: Citation;
  onClose: () => void;
}

export function ChunkPanel({ citation, onClose }: ChunkPanelProps) {
  const panelRef = useRef<HTMLElement>(null);
  const titleId = useId();
  const { data: chunk, isPending, isError, error, refetch } = useChunk(citation.chunk_id);
  useDialogFocus(panelRef, onClose);

  return (
    <div className="drawer-backdrop" onMouseDown={(event) => event.target === event.currentTarget && onClose()}>
      <aside
        ref={panelRef}
        className="drawer"
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        tabIndex={-1}
      >
        <header className="drawer__header">
          <h2 id={titleId} className="drawer__title">
            Fragmento original
          </h2>
          <button type="button" className="button button--secondary" onClick={onClose} aria-label="Cerrar fragmento">
            Cerrar
          </button>
        </header>

        <p className="drawer__source">{formatCitationLabel(chunk ?? citation)}</p>

        {isPending && <p className="muted" role="status">Cargando fragmento…</p>}
        {isError && <ErrorMessage title="No se pudo cargar el fragmento" error={error} onRetry={() => void refetch()} />}
        {chunk && (
          <>
            {!chunk.is_current && (
              <p className="notice notice--warning" role="note">
                Esta cita procede de la versión v{chunk.version}, que ya no es la vigente. Verifica el procedimiento en la
                versión actual antes de aplicarlo.
              </p>
            )}
            <dl className="drawer__meta">
              <div>
                <dt>Documento</dt>
                <dd>{chunk.title}</dd>
              </div>
              <div>
                <dt>Clave</dt>
                <dd>{chunk.doc_key}</dd>
              </div>
              <div>
                <dt>Versión</dt>
                <dd>
                  v{chunk.version} · {chunk.is_current ? "vigente" : "histórica"}
                </dd>
              </div>
              <div>
                <dt>Página</dt>
                <dd>{chunk.page ?? "—"}</dd>
              </div>
            </dl>
            <div className="drawer__text" tabIndex={0} aria-label="Texto del fragmento">
              {chunk.text}
            </div>
          </>
        )}
        <p className="field-hint">Pulsa Esc para cerrar.</p>
      </aside>
    </div>
  );
}
