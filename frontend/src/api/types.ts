export type BusinessLine = "autos" | "hogar" | "vida";

export type DocumentStatus = "queued" | "processing" | "ready" | "failed";

export interface DocumentOut {
  id: string;
  doc_key: string;
  title: string;
  business_line: BusinessLine;
  version: number;
  is_current: boolean;
  status: DocumentStatus;
  error: string | null;
  page_count: number | null;
  chunk_count: number | null;
  created_at: string;
}

export interface DocumentList {
  items: DocumentOut[];
}

export interface Citation {
  chunk_id: string;
  document_id: string;
  title: string;
  version: number;
  page: number | null;
  quote: string;
}

export interface AskOut {
  answer: string;
  refused: boolean;
  refusal_reason: string | null;
  confidence: number;
  citations: Citation[];
  trace_id: string | null;
}

export interface AskRequest {
  question: string;
  business_line: BusinessLine | null;
}

export interface ChunkOut {
  id: string;
  document_id: string;
  title: string;
  doc_key: string;
  version: number;
  is_current: boolean;
  page: number | null;
  text: string;
}

export interface UploadDocumentInput {
  file: File;
  businessLine: BusinessLine;
  title?: string;
  docKey?: string;
}
