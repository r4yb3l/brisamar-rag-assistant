import { ApiError } from "../api/client";

export function describeError(error: unknown): string {
  if (error instanceof ApiError) return error.status ? `${error.message} (HTTP ${error.status})` : error.message;
  if (error instanceof Error) return error.message;
  return String(error);
}

interface ErrorMessageProps {
  title: string;
  error: unknown;
  onRetry?: () => void;
}

export function ErrorMessage({ title, error, onRetry }: ErrorMessageProps) {
  return (
    <div className="notice notice--error" role="alert">
      <p className="notice__title">{title}</p>
      <p>{describeError(error)}</p>
      {onRetry && (
        <button type="button" className="button button--secondary" onClick={onRetry}>
          Reintentar
        </button>
      )}
    </div>
  );
}
