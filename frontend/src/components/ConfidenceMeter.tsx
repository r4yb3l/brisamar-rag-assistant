import { CONFIDENCE_LABELS, confidenceLevel, toPercent } from "../lib/format";

export function ConfidenceMeter({ confidence }: { confidence: number }) {
  const percent = toPercent(confidence);
  const level = confidenceLevel(confidence);

  return (
    <div className={`confidence confidence--${level}`}>
      <span className="confidence__label">
        Confianza: <strong>{CONFIDENCE_LABELS[level]}</strong> ({percent} %)
      </span>
      <div
        className="confidence__track"
        role="meter"
        aria-label="Confianza de la respuesta"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={percent}
        aria-valuetext={`${CONFIDENCE_LABELS[level]}, ${percent} %`}
      >
        <span className="confidence__fill" style={{ width: `${percent}%` }} />
      </div>
    </div>
  );
}
