import { describe, expect, it, vi } from "vitest";
import { jsonResponse } from "../test/renderWithProviders";
import { ApiError, askQuestion, listDocuments, uploadDocument } from "./client";

describe("api client", () => {
  it("sends the demo token as a bearer header on every request", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ items: [] }));
    vi.stubGlobal("fetch", fetchMock);

    await listDocuments("analyst-hogar", "hogar");

    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("http://localhost:8000/api/documents?business_line=hogar");
    expect(new Headers(init.headers).get("Authorization")).toBe("Bearer analyst-hogar");
  });

  it("posts multipart form data without forcing a content type", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ id: "doc-1" }, 202));
    vi.stubGlobal("fetch", fetchMock);
    const file = new File(["%PDF-1.7"], "manual.pdf", { type: "application/pdf" });

    await uploadDocument("analyst-all", { file, businessLine: "vida", title: " Manual vida ", docKey: "" });

    const init = fetchMock.mock.calls[0]?.[1] as RequestInit;
    const body = init.body as FormData;
    expect(init.method).toBe("POST");
    expect(new Headers(init.headers).has("Content-Type")).toBe(false);
    expect(body.get("business_line")).toBe("vida");
    expect(body.get("title")).toBe("Manual vida");
    expect(body.has("doc_key")).toBe(false);
  });

  it("surfaces the backend detail message instead of a generic error", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(jsonResponse({ detail: "La línea 'vida' no está permitida para este usuario" }, 403)),
    );

    const error = await askQuestion("analyst-autos", { question: "¿Plazo?", business_line: "vida" }).catch(
      (caught: unknown) => caught,
    );

    expect(error).toBeInstanceOf(ApiError);
    expect((error as ApiError).status).toBe(403);
    expect((error as ApiError).message).toBe("La línea 'vida' no está permitida para este usuario");
  });

  it("flattens FastAPI validation details into a readable message", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        jsonResponse({ detail: [{ loc: ["body", "question"], msg: "String should have at least 3 characters" }] }, 422),
      ),
    );

    await expect(askQuestion("analyst-all", { question: "a", business_line: null })).rejects.toThrow(
      "question: String should have at least 3 characters",
    );
  });
});
