"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { smartCopyInitiative } from "@/lib/api";

// Smart Copy (Shakthi_OS 3.1.1) -- clones an initiative as a starting
// template for a new one. The backend carries the source's title,
// milestone checklist, and this note forward as the new initiative's
// `context`, so whichever agent picks it up has the full brief without a
// separate catch-up conversation.
export function SmartCopyButton({ sourceId, sourceTitle }: { sourceId: number; sourceTitle: string }) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [title, setTitle] = useState(`${sourceTitle} (copy)`);
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit() {
    setBusy(true);
    setError(null);
    try {
      const result = await smartCopyInitiative(sourceId, title.trim() || undefined, note.trim() || undefined);
      if (result.error) {
        setError(result.error);
        return;
      }
      setOpen(false);
      router.refresh();
    } catch {
      setError("Could not reach the Shakthi API.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <button
        onClick={() => setOpen(true)}
        className="rounded-full px-2 py-0.5 border border-[var(--border)] text-xs text-[var(--muted-foreground)] hover:text-[var(--ink)] hover:border-[var(--local)] transition-colors"
        title="Clone this initiative as a starting template for a new one"
      >
        Smart Copy
      </button>

      {open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 px-4">
          <div className="w-full max-w-md rounded-xl border border-[var(--border)] bg-[var(--surface-2)] p-5 shadow-xl">
            <h3 className="text-sm font-semibold text-[var(--ink)]">Smart Copy — {sourceTitle}</h3>
            <p className="mt-1 text-xs text-[var(--muted-foreground)]">
              Creates a new initiative pre-loaded with this one&apos;s milestones as a fresh checklist and its brief
              carried forward, so the agent picking it up doesn&apos;t need a separate catch-up.
            </p>

            <label className="mt-4 block text-xs text-[var(--muted-foreground)]">New title</label>
            <input
              autoFocus
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="mt-1 w-full rounded-md border border-[var(--border)] bg-transparent px-2.5 py-1.5 text-sm text-[var(--ink)] outline-none focus:border-[var(--local)]"
            />

            <label className="mt-3 block text-xs text-[var(--muted-foreground)]">Note for the agent (optional)</label>
            <textarea
              value={note}
              onChange={(e) => setNote(e.target.value)}
              rows={3}
              placeholder="What's different this time around, if anything..."
              className="mt-1 w-full rounded-md border border-[var(--border)] bg-transparent px-2.5 py-1.5 text-sm text-[var(--ink)] outline-none focus:border-[var(--local)]"
            />

            {error && <p className="mt-2 text-xs text-red-400">{error}</p>}

            <div className="mt-4 flex justify-end gap-2">
              <button
                onClick={() => setOpen(false)}
                disabled={busy}
                className="rounded-full px-3 py-1 text-xs border border-[var(--border)] text-[var(--muted-foreground)] hover:text-[var(--ink)]"
              >
                Cancel
              </button>
              <button
                onClick={submit}
                disabled={busy || !title.trim()}
                className="rounded-full px-3 py-1 text-xs border border-[var(--local)] text-[var(--local)] disabled:opacity-50"
              >
                {busy ? "Copying…" : "Create copy"}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
