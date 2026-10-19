"use client";

import { ChangeEvent, useState } from "react";

type ImageItem = { name: string; url: string };

export default function ImageToPdfPage() {
  const [images, setImages] = useState<ImageItem[]>([]);
  const [message, setMessage] = useState("Files stay in your browser until you save the PDF.");

  function onFiles(event: ChangeEvent<HTMLInputElement>) {
    const files = Array.from(event.target.files ?? []).filter((file) => file.type.startsWith("image/"));
    images.forEach((image) => URL.revokeObjectURL(image.url));
    setImages(files.map((file) => ({ name: file.name, url: URL.createObjectURL(file) })));
    setMessage(files.length ? `${files.length} image${files.length === 1 ? "" : "s"} ready. Select Save as PDF in the print dialog.` : "Choose one or more image files.");
  }

  function printPdf() {
    if (!images.length) return setMessage("Choose at least one image first.");
    setMessage("Opening print dialog. Select Save as PDF.");
    window.setTimeout(() => window.print(), 150);
  }

  return <main className="min-h-screen bg-slate-950 px-6 py-16 text-white"><section className="mx-auto max-w-5xl"><p className="text-sm font-bold uppercase tracking-[0.22em] text-emerald-400">Dhansetu Daily Tool</p><h1 className="mt-4 text-4xl font-black tracking-tight sm:text-6xl">Image to PDF</h1><p className="mt-5 max-w-2xl text-lg text-slate-300">Turn JPG, PNG, and WEBP images into a clean PDF without uploading personal documents.</p><div className="mt-10 rounded-3xl border border-slate-700 bg-slate-900 p-6 shadow-2xl"><label className="block cursor-pointer rounded-2xl border-2 border-dashed border-emerald-400/60 bg-slate-950 p-10 text-center hover:border-emerald-300"><span className="text-lg font-bold">Choose images</span><span className="mt-2 block text-sm text-slate-400">Select multiple files to combine them in order.</span><input className="sr-only" type="file" accept="image/*" multiple onChange={onFiles} /></label><div className="mt-5 flex flex-wrap items-center justify-between gap-3"><p className="text-sm text-slate-400" aria-live="polite">{message}</p><button type="button" onClick={printPdf} className="rounded-xl bg-emerald-500 px-5 py-3 font-bold text-slate-950 hover:bg-emerald-400">Print / Save PDF ({images.length})</button></div>{images.length > 0 && <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">{images.map((image) => <figure key={image.url} className="overflow-hidden rounded-2xl border border-slate-700 bg-slate-950"><img src={image.url} alt={image.name} className="aspect-[4/3] w-full object-contain" /><figcaption className="truncate px-3 py-2 text-xs text-slate-400">{image.name}</figcaption></figure>)}</div>}</div><p className="mt-6 text-xs text-slate-500">Privacy note: this tool uses local browser object URLs. No server upload or account is required.</p></section><style jsx global>{`@media print { body { background: white !important; } body > * { display: none !important; } main { display: block !important; min-height: auto !important; color: #111827 !important; background: white !important; padding: 12px !important; } main label, main button, main p, main figcaption { display: none !important; } main figure { break-inside: avoid; border: 0 !important; } main img { max-height: 255mm; object-fit: contain; } }`}</style></main>;
}
