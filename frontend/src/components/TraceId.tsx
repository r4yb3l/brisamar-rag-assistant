import { useCopyToClipboard } from "../hooks/useCopyToClipboard";

const COPY_FEEDBACK = {
  idle: "Copiar",
  copied: "Copiado",
  failed: "No se pudo copiar",
} as const;

export function TraceId({ traceId }: { traceId: string }) {
  const { state, copy } = useCopyToClipboard();

  return (
    <p className="trace-id">
      <span>Trace ID:</span> <code>{traceId}</code>
      <button
        type="button"
        className="button button--link"
        onClick={() => void copy(traceId)}
        aria-label={`Copiar trace ID ${traceId}`}
      >
        {COPY_FEEDBACK[state]}
      </button>
      <span className="visually-hidden" aria-live="polite">
        {state === "copied" ? "Trace ID copiado" : ""}
      </span>
    </p>
  );
}
