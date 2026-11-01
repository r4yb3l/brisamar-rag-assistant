import { useCallback, useId, useState, type FormEvent, type KeyboardEvent } from "react";
import type { BusinessLine, Citation } from "../api/types";
import { useDemoUser } from "../auth/DemoUserContext";
import { BUSINESS_LINE_LABELS } from "../auth/demoUsers";
import { useAsk } from "../hooks/useAsk";
import { AnswerCard } from "./AnswerCard";
import { ChunkPanel } from "./ChunkPanel";
import { ErrorMessage } from "./ErrorMessage";

const MIN_QUESTION_LENGTH = 3;
const ALL_LINES = "";

export function AskPanel() {
  const { user } = useDemoUser();
  const ask = useAsk();
  const [question, setQuestion] = useState("");
  const [lineFilter, setLineFilter] = useState<BusinessLine | typeof ALL_LINES>(ALL_LINES);
  const [activeCitation, setActiveCitation] = useState<Citation | null>(null);
  const questionId = useId();
  const filterId = useId();
  const hintId = useId();

  const trimmed = question.trim();
  const canSubmit = trimmed.length >= MIN_QUESTION_LENGTH && !ask.isPending;

  function submit() {
    if (!canSubmit) return;
    setActiveCitation(null);
    ask.mutate({ question: trimmed, business_line: lineFilter || null });
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    submit();
  }

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) {
      event.preventDefault();
      submit();
    }
  }

  const closePanel = useCallback(() => setActiveCitation(null), []);

  return (
    <section className="panel" aria-labelledby="ask-heading">
      <h2 id="ask-heading" className="panel__title">
        Preguntar al manual
      </h2>
      <form className="ask-form" onSubmit={handleSubmit}>
        <div className="field">
          <label htmlFor={questionId} className="field-label">
            Pregunta
          </label>
          <textarea
            id={questionId}
            rows={4}
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            onKeyDown={handleKeyDown}
            aria-describedby={hintId}
            placeholder="¿Cuál es el plazo para declarar un siniestro de lunas en Autos?"
          />
          <p id={hintId} className="field-hint">
            Ctrl + Enter para enviar. La respuesta solo usa documentos de tus líneas.
          </p>
        </div>
        <div className="ask-form__actions">
          <div className="field">
            <label htmlFor={filterId} className="field-label">
              Filtrar por línea
            </label>
            <select
              id={filterId}
              value={lineFilter}
              onChange={(event) => setLineFilter(event.target.value as BusinessLine | typeof ALL_LINES)}
            >
              <option value={ALL_LINES}>Todas mis líneas</option>
              {user.lines.map((line) => (
                <option key={line} value={line}>
                  {BUSINESS_LINE_LABELS[line]}
                </option>
              ))}
            </select>
          </div>
          <button type="submit" className="button" disabled={!canSubmit}>
            {ask.isPending ? "Buscando en el manual…" : "Preguntar"}
          </button>
        </div>
      </form>

      <div className="ask-result">
        {ask.isPending && (
          <p className="muted" role="status">
            Buscando fragmentos relevantes y redactando la respuesta…
          </p>
        )}
        {ask.isError && <ErrorMessage title="No se pudo obtener una respuesta" error={ask.error} onRetry={submit} />}
        {ask.isSuccess && (
          <AnswerCard
            result={ask.data}
            activeChunkId={activeCitation?.chunk_id ?? null}
            onSelectCitation={setActiveCitation}
          />
        )}
        {ask.isIdle && (
          <p className="empty-state">
            Escribe una pregunta sobre un procedimiento. Cada afirmación de la respuesta enlaza al fragmento del manual
            del que procede.
          </p>
        )}
      </div>

      {activeCitation && <ChunkPanel citation={activeCitation} onClose={closePanel} />}
    </section>
  );
}
