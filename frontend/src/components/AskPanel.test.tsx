import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { AskOut, ChunkOut } from "../api/types";
import { jsonResponse, renderWithProviders } from "../test/renderWithProviders";
import { AskPanel } from "./AskPanel";

const answer: AskOut = {
  answer: "El asegurado dispone de 7 días para comunicar el siniestro [1].",
  refused: false,
  refusal_reason: null,
  confidence: 0.82,
  citations: [
    {
      chunk_id: "chunk-42",
      document_id: "doc-1",
      title: "Manual de siniestros Autos",
      version: 2,
      page: 4,
      quote: "dispone de 7 días",
    },
  ],
  trace_id: "trace-abc",
};

const supersededChunk: ChunkOut = {
  id: "chunk-42",
  document_id: "doc-1",
  title: "Manual de siniestros Autos",
  doc_key: "manual-siniestros-autos",
  version: 2,
  is_current: false,
  page: 4,
  text: "El asegurado dispone de 7 días naturales para comunicar el siniestro a la compañía.",
};

function routeFetch(refusal?: Partial<AskOut>) {
  return vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input);
    if (url.endsWith("/api/ask")) return jsonResponse({ ...answer, ...refusal });
    if (url.endsWith("/api/chunks/chunk-42")) return jsonResponse(supersededChunk);
    return jsonResponse({ detail: "not mocked" }, 404);
  });
}

async function askSomething() {
  const user = userEvent.setup();
  await user.type(screen.getByLabelText("Pregunta"), "¿Plazo para comunicar un siniestro?");
  await user.click(screen.getByRole("button", { name: "Preguntar" }));
  return user;
}

describe("AskPanel", () => {
  it("opens the original fragment from a citation and closes it with Escape", async () => {
    vi.stubGlobal("fetch", routeFetch());
    renderWithProviders(<AskPanel />);
    const user = await askSomething();

    const citation = await screen.findByRole("button", { name: /\[1\]\s*Manual de siniestros Autos · v2 · pág\. 4/ });
    expect(screen.getByRole("meter", { name: "Confianza de la respuesta" })).toHaveAttribute("aria-valuenow", "82");

    await user.click(citation);

    const dialog = await screen.findByRole("dialog", { name: "Fragmento original" });
    expect(await screen.findByText(supersededChunk.text)).toBeInTheDocument();
    expect(dialog).toHaveTextContent("ya no es la vigente");

    await user.keyboard("{Escape}");
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(citation).toHaveFocus();
  });

  it("renders a refusal distinctly with its reason", async () => {
    vi.stubGlobal(
      "fetch",
      routeFetch({ refused: true, answer: "", refusal_reason: "no_relevant_evidence", citations: [], confidence: 0.1 }),
    );
    renderWithProviders(<AskPanel />);
    await askSomething();

    expect(await screen.findByText(/No hay evidencia suficiente/)).toBeInTheDocument();
    expect(screen.getByText(/Ningún fragmento de los documentos a los que tienes acceso/)).toBeInTheDocument();
    expect(screen.queryByText("Fuentes")).not.toBeInTheDocument();
  });
});
