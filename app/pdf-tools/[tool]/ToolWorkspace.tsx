"use client";

import Link from "next/link";
import { useState } from "react";
import { degrees, PDFDocument, rgb, StandardFonts } from "pdf-lib";
import type { PdfTool } from "../tools";

export default function ToolWorkspace({ tool }: { tool: PdfTool }) {
  const [files, setFiles] = useState<File[]>([]);
  const [message, setMessage] = useState("Choose files to begin. Nothing is uploaded.");

  async function process() {
    if (!files.length) return setMessage("Choose at least one file first.");
    if (!tool.implemented) return setMessage("This workflow is designed but not enabled until its local worker is verified. No file was uploaded.");
    try {
      const bytes = await Promise.all(files.filter((file) => file.type === "application/pdf").map((file) => file.arrayBuffer()));
      if (!bytes.length) return setMessage("Choose a PDF file for this workflow.");
      const output = await PDFDocument.create();
      if (tool.slug === "merge") {
        for (const sourceBytes of bytes) {
          const source = await PDFDocument.load(sourceBytes);
          const pages = await output.copyPages(source, source.getPageIndices());
          pages.forEach((page) => output.addPage(page));
        }
      } else {
        const source = await PDFDocument.load(bytes[0]);
        const indices = source.getPageIndices();
        const selected = tool.slug === "split" || tool.slug === "extract-pages" ? indices.slice(0, 1) : indices;
        const pages = await output.copyPages(source, selected);
        for (const [index, page] of pages.entries()) {
          if (tool.slug === "rotate") page.setRotation(degrees(90));
          output.addPage(page);
          if (tool.slug === "add-watermark" || tool.slug === "add-page-numbers") {
            const font = await output.embedFont(StandardFonts.Helvetica);
            const current = output.getPage(index);
            current.drawText(tool.slug === "add-page-numbers" ? String(index + 1) : "DhanSetu", { x: 24, y: 24, size: 10, font, color: rgb(0.1, 0.45, 0.3), opacity: 0.5 });
          }
        }
      }
      const result = await output.save({ useObjectStreams: true });
      const resultBuffer = result.buffer.slice(result.byteOffset, result.byteOffset + result.byteLength) as ArrayBuffer;
      const url = URL.createObjectURL(new Blob([resultBuffer], { type: "application/pdf" }));
      const anchor = document.createElement("a"); anchor.href = url; anchor.download = `${tool.slug}-dhansetu.pdf`; anchor.click(); URL.revokeObjectURL(url);
      setMessage("Finished locally. Your browser downloaded the result.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "The local PDF could not be processed.");
    }
  }

  return <main className="min-h-screen bg-[#0a1410] px-5 py-12 text-white sm:px-8"><section className="mx-auto max-w-3xl"><Link href="/pdf-tools" className="text-sm text-emerald-300">← All PDF tools</Link><p className="mt-12 text-xs font-bold uppercase tracking-[0.24em] text-emerald-300">{tool.implemented ? "Local browser tool" : "Planned local worker"}</p><h1 className="mt-4 text-4xl font-black tracking-tight sm:text-6xl">{tool.name}</h1><p className="mt-5 max-w-2xl text-lg leading-8 text-emerald-50/65">{tool.description} Files remain in this browser session until you download the result.</p><div className="mt-10 rounded-3xl border border-emerald-100/10 bg-white/[0.04] p-6"><label className="block cursor-pointer rounded-2xl border-2 border-dashed border-emerald-300/40 p-10 text-center hover:border-emerald-200"><span className="text-lg font-bold">Choose {tool.accepts}</span><span className="mt-2 block text-sm text-emerald-50/55">No upload endpoint is used by this page.</span><input className="sr-only" type="file" accept={tool.accepts === "images" ? "image/*" : tool.accepts} multiple={tool.slug === "merge"} onChange={(event) => setFiles(Array.from(event.target.files ?? []))} /></label><div className="mt-5 flex flex-wrap items-center justify-between gap-4"><span className="text-sm text-emerald-50/60" aria-live="polite">{message}</span><button type="button" onClick={process} className="rounded-xl bg-emerald-300 px-5 py-3 font-bold text-[#0a1410] hover:bg-emerald-200">{tool.implemented ? "Process locally" : "Check workflow"}</button></div></div></section></main>;
}
