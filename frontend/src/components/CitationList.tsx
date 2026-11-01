import type { Citation } from "../api/types";
import { formatCitationLabel } from "../lib/format";

interface CitationListProps {
  citations: Citation[];
  activeChunkId: string | null;
  onSelect: (citation: Citation) => void;
}

export function CitationList({ citations, activeChunkId, onSelect }: CitationListProps) {
  if (citations.length === 0) return null;

  return (
    <div className="citations">
      <h4 className="citations__title">Fuentes</h4>
      <ol className="citations__list">
        {citations.map((citation, index) => (
          <li key={`${citation.chunk_id}-${index}`}>
            <button
              type="button"
              className="citation"
              aria-pressed={activeChunkId === citation.chunk_id}
              aria-haspopup="dialog"
              onClick={() => onSelect(citation)}
            >
              <span className="citation__index">[{index + 1}]</span>
              <span className="citation__label">{formatCitationLabel(citation)}</span>
            </button>
            {citation.quote && <blockquote className="citation__quote">"{citation.quote}"</blockquote>}
          </li>
        ))}
      </ol>
    </div>
  );
}
