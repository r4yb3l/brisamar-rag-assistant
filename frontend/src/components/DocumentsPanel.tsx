import { DocumentList } from "./DocumentList";
import { UploadForm } from "./UploadForm";

export function DocumentsPanel() {
  return (
    <section className="panel" aria-labelledby="documents-heading">
      <h2 id="documents-heading" className="panel__title">
        Documentos
      </h2>
      <UploadForm />
      <h3 className="panel__subtitle">Documentos indexados</h3>
      <DocumentList />
    </section>
  );
}
