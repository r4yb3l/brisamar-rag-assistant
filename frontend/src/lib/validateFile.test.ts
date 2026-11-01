import { describe, expect, it } from "vitest";
import { MAX_UPLOAD_BYTES, validatePdfFile } from "./validateFile";

function fileOfSize(name: string, type: string, size: number): File {
  const file = new File(["x"], name, { type });
  Object.defineProperty(file, "size", { value: size });
  return file;
}

describe("validatePdfFile", () => {
  it("accepts a PDF under the size limit", () => {
    expect(validatePdfFile(fileOfSize("manual.pdf", "application/pdf", 1024))).toBeNull();
  });

  it("rejects non-PDF files with the file name in the message", () => {
    expect(validatePdfFile(fileOfSize("notas.docx", "application/msword", 1024))).toMatch(/notas\.docx.*no es un PDF/);
  });

  it("rejects files over 20 MB", () => {
    expect(validatePdfFile(fileOfSize("grande.pdf", "application/pdf", MAX_UPLOAD_BYTES + 1))).toMatch(/máximo es 20 MB/);
  });

  it("asks for a file when none is selected", () => {
    expect(validatePdfFile(null)).toBe("Selecciona un archivo PDF.");
  });
});
