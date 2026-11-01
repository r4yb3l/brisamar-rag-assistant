import { useId, useRef, useState, type FormEvent } from "react";
import type { BusinessLine, DocumentOut } from "../api/types";
import { useDemoUser } from "../auth/DemoUserContext";
import { BUSINESS_LINE_LABELS } from "../auth/demoUsers";
import { useUploadDocument } from "../hooks/useDocuments";
import { validatePdfFile } from "../lib/validateFile";
import { ErrorMessage } from "./ErrorMessage";

export function UploadForm() {
  const { user } = useDemoUser();
  const upload = useUploadDocument();
  const formRef = useRef<HTMLFormElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [selectedLine, setSelectedLine] = useState<BusinessLine | null>(null);
  const [title, setTitle] = useState("");
  const [docKey, setDocKey] = useState("");
  const [validationError, setValidationError] = useState<string | null>(null);
  const [lastUploaded, setLastUploaded] = useState<DocumentOut | null>(null);

  const businessLine = selectedLine && user.lines.includes(selectedLine) ? selectedLine : user.lines[0];
  const fileId = useId();
  const lineId = useId();
  const titleId = useId();
  const docKeyId = useId();
  const docKeyHintId = useId();
  const fileErrorId = useId();

  function handleFileChange(next: File | null) {
    setFile(next);
    setLastUploaded(null);
    setValidationError(next ? validatePdfFile(next) : null);
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const error = validatePdfFile(file);
    setValidationError(error);
    if (error || !file || !businessLine) return;
    upload.mutate(
      { file, businessLine, title, docKey },
      {
        onSuccess: (document) => {
          setLastUploaded(document);
          setFile(null);
          setTitle("");
          setDocKey("");
          formRef.current?.reset();
        },
      },
    );
  }

  return (
    <form ref={formRef} className="upload-form" onSubmit={handleSubmit} noValidate>
      <div className="field">
        <label htmlFor={fileId} className="field-label">
          Documento PDF
        </label>
        <input
          id={fileId}
          type="file"
          accept="application/pdf,.pdf"
          onChange={(event) => handleFileChange(event.target.files?.[0] ?? null)}
          aria-invalid={validationError ? true : undefined}
          aria-describedby={validationError ? fileErrorId : undefined}
        />
        {validationError && (
          <p id={fileErrorId} className="field-error" role="alert">
            {validationError}
          </p>
        )}
        <p className="field-hint">Máximo 20 MB.</p>
      </div>

      <div className="field-row">
        <div className="field">
          <label htmlFor={lineId} className="field-label">
            Línea de negocio
          </label>
          <select
            id={lineId}
            value={businessLine}
            onChange={(event) => setSelectedLine(event.target.value as BusinessLine)}
          >
            {user.lines.map((line) => (
              <option key={line} value={line}>
                {BUSINESS_LINE_LABELS[line]}
              </option>
            ))}
          </select>
        </div>
        <div className="field">
          <label htmlFor={titleId} className="field-label">
            Título (opcional)
          </label>
          <input id={titleId} type="text" value={title} onChange={(event) => setTitle(event.target.value)} />
        </div>
      </div>

      <div className="field">
        <label htmlFor={docKeyId} className="field-label">
          Clave del documento (opcional)
        </label>
        <input
          id={docKeyId}
          type="text"
          value={docKey}
          onChange={(event) => setDocKey(event.target.value)}
          aria-describedby={docKeyHintId}
          placeholder="p. ej. manual-siniestros-autos"
        />
        <p id={docKeyHintId} className="field-hint">
          Reutiliza la clave de un documento existente para subir una nueva versión.
        </p>
      </div>

      <button type="submit" className="button" disabled={upload.isPending}>
        {upload.isPending ? "Subiendo…" : "Subir documento"}
      </button>

      {upload.isError && <ErrorMessage title="No se pudo subir el documento" error={upload.error} />}
      {lastUploaded && !upload.isError && (
        <p className="notice notice--success" role="status">
          "{lastUploaded.title}" (v{lastUploaded.version}) se ha recibido y está en cola de procesamiento.
        </p>
      )}
    </form>
  );
}
