export const MAX_UPLOAD_BYTES = 20 * 1024 * 1024;

export function validatePdfFile(file: File | null): string | null {
  if (!file) return "Selecciona un archivo PDF.";
  const isPdf = file.type === "application/pdf" || file.name.toLowerCase().endsWith(".pdf");
  if (!isPdf) return `"${file.name}" no es un PDF. Solo se admiten archivos .pdf.`;
  if (file.size === 0) return `"${file.name}" está vacío.`;
  if (file.size > MAX_UPLOAD_BYTES) {
    return `"${file.name}" pesa ${formatMegabytes(file.size)}; el máximo es 20 MB.`;
  }
  return null;
}

export function formatMegabytes(bytes: number): string {
  return `${(bytes / (1024 * 1024)).toFixed(1).replace(".", ",")} MB`;
}
