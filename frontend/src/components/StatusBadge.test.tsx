import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { documentsPollInterval } from "../hooks/useDocuments";
import type { DocumentOut } from "../api/types";
import { StatusBadge } from "./StatusBadge";

function documentWithStatus(status: DocumentOut["status"]): DocumentOut {
  return {
    id: status,
    doc_key: "manual-autos",
    title: "Manual Autos",
    business_line: "autos",
    version: 1,
    is_current: true,
    status,
    error: null,
    page_count: null,
    chunk_count: null,
    created_at: "2026-11-01T10:00:00Z",
  };
}

describe("StatusBadge", () => {
  it.each([
    ["queued", "En cola"],
    ["processing", "Procesando"],
    ["ready", "Listo"],
    ["failed", "Error"],
  ] as const)("renders %s as %s", (status, label) => {
    render(<StatusBadge status={status} />);
    expect(screen.getByText(label)).toHaveAttribute("data-status", status);
  });
});

describe("documentsPollInterval", () => {
  it("polls while any document is still queued or processing", () => {
    expect(documentsPollInterval({ items: [documentWithStatus("ready"), documentWithStatus("processing")] })).toBe(2000);
  });

  it("stops polling once every document is settled", () => {
    expect(documentsPollInterval({ items: [documentWithStatus("ready"), documentWithStatus("failed")] })).toBe(false);
    expect(documentsPollInterval(undefined)).toBe(false);
  });
});
