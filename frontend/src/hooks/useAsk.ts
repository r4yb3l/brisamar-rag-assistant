import { useMutation, useQuery } from "@tanstack/react-query";
import { askQuestion, getChunk } from "../api/client";
import type { AskRequest } from "../api/types";
import { useDemoUser } from "../auth/DemoUserContext";

export function useAsk() {
  const { user } = useDemoUser();
  return useMutation({
    mutationFn: (payload: AskRequest) => askQuestion(user.token, payload),
  });
}

export function useChunk(chunkId: string | null) {
  const { user } = useDemoUser();
  return useQuery({
    queryKey: ["chunk", user.token, chunkId],
    queryFn: () => getChunk(user.token, chunkId as string),
    enabled: chunkId !== null,
    staleTime: Infinity,
  });
}
