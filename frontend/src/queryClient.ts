import { QueryClient } from "@tanstack/react-query";
import { ApiError } from "./api/client";

const MAX_RETRIES = 2;

export function createQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        refetchOnWindowFocus: false,
        retry: (failureCount, error) => {
          const isClientError = error instanceof ApiError && error.status >= 400 && error.status < 500;
          return !isClientError && failureCount < MAX_RETRIES;
        },
      },
      mutations: { retry: false },
    },
  });
}
