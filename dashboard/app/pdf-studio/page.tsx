"use client";

import { useState, useEffect } from "react";
import { Card, CardHeader, CardBody, Badge } from "@/components/ui";
import { SUPPORT_EMAIL } from "@/lib/brand";

// Real, live PayU checkout link, created directly in the founder's own
// PayU merchant dashboard -- same link already used on blackboxOps_OS
// Pricing. Founder's own instruction, 2026-08-24: keep this as the
// stand-in checkout for both Dhansetu products (PDF Studio, PeopleDesk)
// "for now" -- fixed amount, not tied to this page's real Rs.99/year
// price, same honest gap already stated there.
const REAL_PAYU_LINK = "https://u.payu.in/xJYCpF9eG4sc";

type Operation = "merge" | "split" | "compress" | "images-to-pdf" | "rotate" | "extract" | "protect" | "unprotect";

const OPERATIONS: { id: Operation; label: string; multi: boolean; accept: string; needsPassword?: boolean; needsDegrees?: boolean; needsPages?: boolean; pagesRequired?: boolean }[] = [
  { id: "merge", label: "Merge PDF", multi: true, accept: "application/pdf" },
  { id: "split", label: "Split PDF", multi: false, accept: "application/pdf" },
  { id: "compress", label: "Compress PDF", multi: false, accept: "application/pdf" },
  { id: "images-to-pdf", label: "Images to PDF", multi: true, accept: "image/*" },
  { id: "rotate", label: "Rotate PDF", multi: false, accept: "application/pdf", needsDegrees: true, needsPages: true },
  { id: "extract", label: "Extract Pages", multi: false, accept: "application/pdf", needsPages: true, pagesRequired: true },
  { id: "protect", label: "Password Protect", multi: false, accept: "application/pdf", needsPassword: true },
  { id: "unprotect", label: "Remove Password", multi: false, accept: "application/pdf", needsPassword: true },
];

export default function PdfStudioPage() {
  const [operation, setOperation] = useState<Operation>("merge");
  const [files, setFiles] = useState<FileList | null>(null);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [degrees, setDegrees] = useState("90");
  const [pages, setPages] = useState("");
  const [status, setStatus] = useState<"idle" | "processing" | "error">("idle");
  const [error, setError] = useState("");
  const [requiresPayment, setRequiresPayment] = useState(false);
  const [remainingFree, setRemainingFree] = useState<number | null>(null);
  const [gateway, setGateway] = useState<"razorpay" | "payu">("razorpay");
  const [razorpayKeyId, setRazorpayKeyId] = useState("");
  const [razorpaySecret, setRazorpaySecret] = useState("");
  const [payuKey, setPayuKey] = useState("");
  const [payuSalt, setPayuSalt] = useState("");
  const [checkoutStatus, setCheckoutStatus] = useState<"idle" | "loading" | "error">("idle");
  const [checkoutError, setCheckoutError] = useState("");
  const [checkoutResult, setCheckoutResult] = useState<{ checkout?: string | { action_url: string; fields: Record<string, string> } } | null>(null);

  async function buyAccess() {
    if (!email.trim()) { setCheckoutError("Enter your email above first."); setCheckoutStatus("error"); return; }
    setCheckoutStatus("loading"); setCheckoutError(""); setCheckoutResult(null);
    try {
      const res = await fetch("/api/blackboxops/subscribe", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: email.trim(), product: "pdf_studio", gateway, razorpayKeyId, razorpaySecret, payuKey, payuSalt }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Failed to create payment link");
      setCheckoutResult(data);
      setCheckoutStatus("idle");
    } catch (e) {
      setCheckoutError(e instanceof Error ? e.message : "Something went wrong.");
      setCheckoutStatus("error");
    }
  }

  useEffect(() => {
    const saved = window.localStorage.getItem("pdf_studio_email");
    if (saved) setEmail(saved);
  }, []);

  const config = OPERATIONS.find((o) => o.id === operation)!;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setRequiresPayment(false);
    if (!email.trim() || !email.includes("@")) {
      setError("Enter a valid email — it's how your 10 free uses are tracked.");
      setStatus("error");
      return;
    }
    if (!files || files.length === 0) {
      setError("Choose at least one file.");
      setStatus("error");
      return;
    }
    if (config.pagesRequired && !pages.trim()) {
      setError("Extract needs page numbers, e.g. 1,3,5.");
      setStatus("error");
      return;
    }

    setStatus("processing");
    setError("");
    window.localStorage.setItem("pdf_studio_email", email.trim());

    const formData = new FormData();
    formData.append("operation", operation);
    formData.append("email", email.trim());
    for (const f of Array.from(files)) formData.append("files", f);
    if (config.needsPassword) formData.append("password", password);
    if (config.needsDegrees) formData.append("degrees", degrees);
    if (config.needsPages && pages.trim()) formData.append("pages", pages.trim());

    try {
      const res = await fetch("/api/pdf/process", { method: "POST", body: formData });
      if (!res.ok) {
        const body = await res.json().catch(() => ({ error: `Request failed (${res.status})` }));
        if (res.status === 402) setRequiresPayment(true);
        throw new Error(body.error || `Request failed (${res.status})`);
      }
      const remainingHeader = res.headers.get("X-PDF-Free-Remaining");
      setRemainingFree(remainingHeader && remainingHeader !== "unlimited" ? Number(remainingHeader) : null);

      const blob = await res.blob();
      const cd = res.headers.get("Content-Disposition") || "";
      const match = cd.match(/filename="(.+)"/);
      const filename = match ? match[1] : `dhansetu_${operation}.pdf`;

      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);

      setStatus("idle");
      setFiles(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong.");
      setStatus("error");
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold">Dhansetu PDF Studio</h1>
          <p className="text-sm text-[var(--muted-foreground)] mt-1">
            Merge, split, compress, rotate, extract, and password-protect PDFs — real processing (pypdf), runs
            locally, nothing uploaded leaves this machine. Styled to match this dashboard&apos;s design system —
            not a copy of Dhansetu Hub&apos;s, since I&apos;ve only ever seen that site&apos;s rendered output, never its source.
          </p>
        </div>
        <Badge tone="local">MVP</Badge>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-8 gap-2">
        {OPERATIONS.map((op) => (
          <button
            key={op.id}
            onClick={() => { setOperation(op.id); setFiles(null); setError(""); setStatus("idle"); }}
            className={`rounded-lg border px-3 py-2.5 text-xs font-medium text-center transition-colors ${
              operation === op.id
                ? "border-[var(--local)] bg-[var(--local-soft)] text-[var(--local)]"
                : "border-[var(--border)] text-[var(--muted-foreground)] hover:text-[var(--ink)]"
            }`}
          >
            {op.label}
          </button>
        ))}
      </div>

      <Card>
        <CardHeader title={config.label} subtitle={config.multi ? "Select multiple files" : "Select one file"} />
        <CardBody>
          <form onSubmit={handleSubmit} className="space-y-4 max-w-lg">
            <div>
              <label className="block text-xs uppercase tracking-wide text-[var(--muted-foreground)] mb-1.5">Email</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
                className="w-full rounded-lg border border-[var(--border)] bg-[var(--surface-2)] px-3 py-2 text-sm text-[var(--ink)]"
              />
              <p className="mt-1.5 text-xs text-[var(--muted-foreground)]">
                {remainingFree !== null ? `${remainingFree} free use(s) left` : "10 free uses, then ₹99/year — tracked by email, nothing stored beyond that"}
              </p>
            </div>

            <div>
              <label className="block text-xs uppercase tracking-wide text-[var(--muted-foreground)] mb-1.5">
                {config.accept === "image/*" ? "Images" : "PDF file" + (config.multi ? "s" : "")}
              </label>
              <input
                type="file"
                multiple={config.multi}
                accept={config.accept}
                onChange={(e) => setFiles(e.target.files)}
                className="block w-full text-sm text-[var(--muted-foreground)] file:mr-3 file:rounded-lg file:border-0 file:bg-[var(--local-soft)] file:px-3 file:py-2 file:text-xs file:font-medium file:text-[var(--local)] hover:file:opacity-80"
              />
              {files && files.length > 0 && (
                <p className="mt-1.5 text-xs text-[var(--muted-foreground)]">{files.length} file(s) selected</p>
              )}
            </div>

            {config.needsPassword && (
              <div>
                <label className="block text-xs uppercase tracking-wide text-[var(--muted-foreground)] mb-1.5">Password</label>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full rounded-lg border border-[var(--border)] bg-[var(--surface-2)] px-3 py-2 text-sm text-[var(--ink)]"
                  placeholder={operation === "protect" ? "Set a password" : "Enter the current password"}
                />
              </div>
            )}

            {config.needsDegrees && (
              <div>
                <label className="block text-xs uppercase tracking-wide text-[var(--muted-foreground)] mb-1.5">Rotation</label>
                <select
                  value={degrees}
                  onChange={(e) => setDegrees(e.target.value)}
                  className="w-full rounded-lg border border-[var(--border)] bg-[var(--surface-2)] px-3 py-2 text-sm text-[var(--ink)]"
                >
                  <option value="90">90°</option>
                  <option value="180">180°</option>
                  <option value="270">270°</option>
                </select>
              </div>
            )}

            {config.needsPages && (
              <div>
                <label className="block text-xs uppercase tracking-wide text-[var(--muted-foreground)] mb-1.5">
                  Pages {config.pagesRequired ? "(required)" : "(optional — blank means all pages)"}
                </label>
                <input
                  type="text"
                  value={pages}
                  onChange={(e) => setPages(e.target.value)}
                  placeholder="e.g. 1,3,5"
                  className="w-full rounded-lg border border-[var(--border)] bg-[var(--surface-2)] px-3 py-2 text-sm text-[var(--ink)]"
                />
              </div>
            )}

            {error && <p className="text-xs text-[var(--bad)]">{error}</p>}

            <button
              type="submit"
              disabled={status === "processing"}
              className="rounded-lg bg-[var(--local)] px-4 py-2 text-sm font-medium text-[var(--bg)] disabled:opacity-50"
            >
              {status === "processing" ? "Processing…" : `Process & Download`}
            </button>
          </form>
        </CardBody>
      </Card>

      {requiresPayment && (
        <Card className="mb-4">
          <CardBody className="flex items-center justify-between gap-6">
            <div>
              <div className="flex items-center gap-2 mb-1.5">
                <span className="w-1.5 h-1.5 rounded-full" style={{ background: "#4ade80" }} />
                <span className="text-xs font-mono uppercase tracking-wide" style={{ color: "#4ade80" }}>Live · Real PayU checkout</span>
              </div>
              <div className="text-sm font-medium text-[var(--ink)]">Quick Pay Now</div>
              <p className="text-xs text-[var(--muted-foreground)] mt-1">Real payment link — opens the actual PayU checkout. Fixed amount, kept separate from the ₹99/year price below.</p>
            </div>
            <a
              href={REAL_PAYU_LINK} target="_blank" rel="noreferrer"
              className="shrink-0 rounded-lg px-5 py-2.5 text-sm font-semibold"
              style={{ background: "#4ade80", color: "#0a0c10" }}
            >
              Pay Now →
            </a>
          </CardBody>
        </Card>
      )}

      {requiresPayment && (
        <Card>
          <CardHeader title="Get annual access — ₹99/year" subtitle="Real checkout, same Razorpay/PayU integration used everywhere else in this project" />
          <CardBody>
            <div className="max-w-lg space-y-3">
              <div className="flex gap-2">
                <button onClick={() => setGateway("razorpay")} className={`text-xs px-3 py-1.5 rounded-full border ${gateway === "razorpay" ? "border-[var(--local)] text-[var(--local)]" : "border-[var(--border)] text-[var(--muted-foreground)]"}`}>Razorpay</button>
                <button onClick={() => setGateway("payu")} className={`text-xs px-3 py-1.5 rounded-full border ${gateway === "payu" ? "border-[var(--local)] text-[var(--local)]" : "border-[var(--border)] text-[var(--muted-foreground)]"}`}>PayU</button>
              </div>

              {gateway === "razorpay" ? (
                <div className="grid grid-cols-2 gap-2">
                  <input placeholder="Razorpay Key ID" value={razorpayKeyId} onChange={(e) => setRazorpayKeyId(e.target.value)} className="rounded-lg border border-[var(--border)] bg-[var(--surface-2)] px-3 py-2 text-xs" />
                  <input placeholder="Razorpay Key Secret" type="password" value={razorpaySecret} onChange={(e) => setRazorpaySecret(e.target.value)} className="rounded-lg border border-[var(--border)] bg-[var(--surface-2)] px-3 py-2 text-xs" />
                </div>
              ) : (
                <div className="grid grid-cols-2 gap-2">
                  <input placeholder="PayU Merchant Key" value={payuKey} onChange={(e) => setPayuKey(e.target.value)} className="rounded-lg border border-[var(--border)] bg-[var(--surface-2)] px-3 py-2 text-xs" />
                  <input placeholder="PayU Merchant Salt" type="password" value={payuSalt} onChange={(e) => setPayuSalt(e.target.value)} className="rounded-lg border border-[var(--border)] bg-[var(--surface-2)] px-3 py-2 text-xs" />
                </div>
              )}

              <p className="text-xs text-[var(--muted-foreground)]">
                Real (even test-mode) merchant keys only — never stored, sent fresh on every click. Test-mode Razorpay
                keys (rzp_test_…) are free and instant to generate, no KYC, and produce a real payment link with no
                real money moving.
              </p>

              <button
                onClick={buyAccess}
                disabled={checkoutStatus === "loading"}
                className="rounded-lg bg-[var(--local)] px-4 py-2 text-sm font-medium text-[var(--bg)] disabled:opacity-50"
              >
                {checkoutStatus === "loading" ? "Creating payment link…" : "Create payment link"}
              </button>

              {checkoutError && <p className="text-xs text-[var(--bad)]">{checkoutError}</p>}
              {checkoutResult?.checkout && typeof checkoutResult.checkout === "string" && (
                <p className="text-xs" style={{ color: "#4ade80" }}>
                  Payment link created: <a href={checkoutResult.checkout} target="_blank" rel="noreferrer" className="underline">{checkoutResult.checkout}</a>
                </p>
              )}
              {checkoutResult?.checkout && typeof checkoutResult.checkout === "object" && (
                <p className="text-xs" style={{ color: "#4ade80" }}>PayU checkout form prepared (txnid ready).</p>
              )}
            </div>
          </CardBody>
        </Card>
      )}

      <p className="text-xs text-[var(--muted-foreground)]">
        File didn&apos;t come out right, or a charge looks wrong? Email{" "}
        <a href={`mailto:${SUPPORT_EMAIL}`} className="text-[var(--local)] hover:underline">{SUPPORT_EMAIL}</a> — a real
        person reads it.
      </p>
    </div>
  );
}
