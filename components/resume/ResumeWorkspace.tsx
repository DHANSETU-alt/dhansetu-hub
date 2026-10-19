"use client";

import { useState } from "react";

export function ResumeWorkspace() {
  const [file, setFile] = useState<File | null>(null);
  const [jobDescription, setJobDescription] = useState("");
  const [text, setText] = useState("");
  const [gaps, setGaps] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function extract() {
    if (!file) return setError("Choose a PDF or DOCX resume first.");
    setBusy(true); setError(""); setText("");
    const form = new FormData();
    form.set("resume", file);
    form.set("jobDescription", jobDescription);
    try {
      const response = await fetch("/api/resume/extract", { method: "POST", body: form });
      const result = await response.json() as { text?: string; keywordGaps?: string[]; error?: string };
      if (!response.ok) throw new Error(result.error ?? "Extraction failed");
      setText(result.text ?? ""); setGaps(result.keywordGaps ?? []);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Extraction failed");
    } finally { setBusy(false); }
  }

  return <section className="space-y-5 rounded-2xl border bg-white p-5 shadow-sm">
    <div><h2 className="text-xl font-semibold text-slate-950">Private resume workspace</h2><p className="mt-1 text-sm text-slate-600">Upload up to 5 MB. Text is extracted in memory and is not persisted by this feature.</p></div>
    <label className="block text-sm font-medium text-slate-800">Resume (PDF or DOCX)<input className="mt-2 block w-full rounded-xl border p-3" type="file" accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document" onChange={(event) => setFile(event.target.files?.[0] ?? null)} /></label>
    <label className="block text-sm font-medium text-slate-800">Optional job description for keyword comparison<textarea className="mt-2 min-h-28 w-full rounded-xl border p-3" value={jobDescription} onChange={(event) => setJobDescription(event.target.value)} placeholder="Paste the job description here" /></label>
    <button className="rounded-xl bg-slate-950 px-5 py-3 font-semibold text-white disabled:opacity-50" type="button" disabled={busy} onClick={extract}>{busy ? "Extracting securely…" : "Extract and review"}</button>
    {error && <p className="text-sm text-rose-700" role="alert">{error}</p>}
    {text && <div className="space-y-4"><div><h3 className="font-semibold text-slate-950">Editable ATS text</h3><textarea className="mt-2 min-h-72 w-full rounded-xl border p-3 text-sm" value={text} onChange={(event) => setText(event.target.value)} /></div><div><h3 className="font-semibold text-slate-950">Keyword gaps</h3>{gaps.length ? <ul className="mt-2 flex flex-wrap gap-2">{gaps.map((gap) => <li className="rounded-full bg-amber-100 px-3 py-1 text-sm text-amber-900" key={gap}>{gap}</li>)}</ul> : <p className="mt-2 text-sm text-emerald-700">No missing terms detected from the supplied job description.</p>}</div></div>}
  </section>;
}
