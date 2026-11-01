# Brisamar RAG Assistant · Frontend

Minimal React client for the Brisamar procedures assistant: upload PDFs with live processing status, ask questions, and open each citation to read the original fragment.

Stack: Vite, React 18, TypeScript (strict), TanStack Query, plain CSS, Vitest + Testing Library.

## Configuration

| Variable | Default | Purpose |
|---|---|---|
| `VITE_API_URL` | `http://localhost:8000` | Backend base URL (the client calls `${VITE_API_URL}/api/...`). Read at build time. |

Copy `.env.example` to `.env` to override it locally.

## Commands

```bash
npm install
npm run dev      # http://localhost:5173
npm run build    # tsc --noEmit + vite build -> dist/
npm test         # vitest run
```

## Docker

```bash
docker build --build-arg VITE_API_URL=http://localhost:8000 -t brisamar-frontend .
docker run -p 5173:5173 brisamar-frontend
```

The image builds with `node:20-alpine` and serves `dist/` from `nginx:alpine` on port 5173 with SPA fallback (`nginx.conf`).

## Business-line isolation

The header selector switches between simulated tokens (`analyst-autos`, `analyst-hogar`, `analyst-all`), persisted in `localStorage`. Every request sends `Authorization: Bearer <token>`; the backend enforces which lines each token can read and upload to. The UI only mirrors that scope (line selectors list the user's lines) and never filters on its own.

## Structure

```
src/
  api/          typed fetch client, ApiError with the backend `detail` message
  auth/         demo users and token context
  hooks/        documents (with 2 s polling while any doc is queued/processing), ask, chunk, dialog focus, clipboard
  lib/          pure helpers: PDF validation, formatting
  components/   header, documents panel, ask panel, answer card, citations, fragment drawer
```
