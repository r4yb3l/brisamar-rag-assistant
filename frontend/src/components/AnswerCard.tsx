import type { AskOut, Citation } from "../api/types";
import { describeRefusalReason } from "../lib/format";
import { CitationList } from "./CitationList";
import { ConfidenceMeter } from "./ConfidenceMeter";
import { TraceId } from "./TraceId";

interface AnswerCardProps {
  result: AskOut;
  activeChunkId: string | null;
  onSelectCitation: (citation: Citation) => void;
}

export function AnswerCard({ result, activeChunkId, onSelectCitation }: AnswerCardProps) {
  return (
    <article className={result.refused ? "answer answer--refused" : "answer"} aria-live="polite">
      {result.refused ? (
        <>
          <h3 className="answer__title">No hay evidencia suficiente en los documentos para responder</h3>
          {result.refusal_reason && <p className="answer__reason">{describeRefusalReason(result.refusal_reason)}</p>}
          {result.answer && <p className="answer__text">{result.answer}</p>}
        </>
      ) : (
        <>
          <h3 className="answer__title">Respuesta</h3>
          <p className="answer__text">{result.answer}</p>
        </>
      )}
      <ConfidenceMeter confidence={result.confidence} />
      <CitationList citations={result.citations} activeChunkId={activeChunkId} onSelect={onSelectCitation} />
      {result.trace_id && <TraceId traceId={result.trace_id} />}
    </article>
  );
}
