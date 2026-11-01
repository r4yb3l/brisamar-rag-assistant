import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { listDocuments, uploadDocument } from "../api/client";
import type { DocumentList, DocumentOut, UploadDocumentInput } from "../api/types";
import { useDemoUser } from "../auth/DemoUserContext";

export const DOCUMENT_POLL_INTERVAL_MS = 2000;

export function isDocumentPending(document: DocumentOut): boolean {
  return document.status === "queued" || document.status === "processing";
}

export function documentsPollInterval(data: DocumentList | undefined): number | false {
  return data?.items.some(isDocumentPending) ? DOCUMENT_POLL_INTERVAL_MS : false;
}

export function useDocuments() {
  const { user } = useDemoUser();
  return useQuery({
    queryKey: ["documents", user.token],
    queryFn: () => listDocuments(user.token),
    refetchInterval: (query) => documentsPollInterval(query.state.data),
  });
}

export function useUploadDocument() {
  const { user } = useDemoUser();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: UploadDocumentInput) => uploadDocument(user.token, input),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["documents", user.token] }),
  });
}
