export type PdfTool = {
  slug: string;
  name: string;
  description: string;
  accepts: string;
  implemented: boolean;
};

export const PDF_TOOLS: PdfTool[] = [
  { slug: "merge", name: "Merge PDFs", description: "Combine selected PDFs in order in your browser.", accepts: ".pdf", implemented: true },
  { slug: "split", name: "Split PDF", description: "Export a selected page range as a new PDF.", accepts: ".pdf", implemented: true },
  { slug: "compress", name: "Compress", description: "Re-save a PDF with object streams enabled.", accepts: ".pdf", implemented: true },
  { slug: "rotate", name: "Rotate", description: "Rotate every page by 90 degrees.", accepts: ".pdf", implemented: true },
  { slug: "extract-pages", name: "Extract Pages", description: "Create a PDF from selected pages.", accepts: ".pdf", implemented: true },
  { slug: "add-watermark", name: "Add Watermark", description: "Stamp a light local text watermark on every page.", accepts: ".pdf", implemented: true },
  { slug: "add-page-numbers", name: "Add Page Numbers", description: "Add page numbers without uploading the source.", accepts: ".pdf", implemented: true },
  { slug: "pdf-to-images", name: "PDF to Images", description: "Prepare page rendering for a local image export worker.", accepts: ".pdf", implemented: false },
  { slug: "images-to-pdf", name: "Images to PDF", description: "Combine images into a printable local PDF.", accepts: "images", implemented: false },
  { slug: "remove-pages", name: "Remove Pages", description: "Drop selected pages from a PDF.", accepts: ".pdf", implemented: true },
  { slug: "organize", name: "Organize", description: "Reorder pages using a local page plan.", accepts: ".pdf", implemented: true },
  { slug: "extract-text", name: "Extract Text", description: "Send a local document to the text extraction worker.", accepts: ".pdf", implemented: false },
  { slug: "protect", name: "Protect", description: "Prepare a protected-document workflow without storing the password.", accepts: ".pdf", implemented: false },
  { slug: "unlock", name: "Unlock", description: "Prepare a local unlock workflow for documents you own.", accepts: ".pdf", implemented: false },
  { slug: "stamp-sign", name: "Stamp / Sign", description: "Place an approval stamp in a local signing workflow.", accepts: ".pdf", implemented: false },
  { slug: "compress-100kb", name: "Compress to 100 KB", description: "Measure a bounded compression target locally.", accepts: ".pdf", implemented: false },
  { slug: "pdf-to-word", name: "PDF to Word", description: "Prepare a text-preserving office conversion job.", accepts: ".pdf", implemented: false },
  { slug: "pdf-to-excel", name: "PDF to Excel", description: "Prepare a table extraction job.", accepts: ".pdf", implemented: false },
  { slug: "pdf-to-ppt", name: "PDF to PowerPoint", description: "Prepare a slide conversion job.", accepts: ".pdf", implemented: false },
  { slug: "word-to-pdf", name: "Word to PDF", description: "Prepare an office document conversion job.", accepts: ".doc,.docx", implemented: false },
  { slug: "e-sign", name: "e-Sign", description: "Prepare a consent-aware signing step.", accepts: ".pdf", implemented: false },
  { slug: "remove-watermark", name: "Remove Watermark", description: "Inspect a document for an authorized cleanup job.", accepts: ".pdf", implemented: false },
  { slug: "ocr", name: "OCR", description: "Prepare a local OCR job for scanned pages.", accepts: ".pdf", implemented: false },
  { slug: "flatten", name: "Flatten", description: "Prepare a flattened output document.", accepts: ".pdf", implemented: false },
  { slug: "repair", name: "Repair", description: "Validate a PDF structure before repair processing.", accepts: ".pdf", implemented: false },
  { slug: "compare", name: "Compare", description: "Compare two local PDFs without uploading them.", accepts: ".pdf", implemented: false },
];

export function findPdfTool(slug: string) {
  return PDF_TOOLS.find((tool) => tool.slug === slug);
}
