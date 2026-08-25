"use client";

import { useState, useEffect, useCallback } from "react";
import { Card, CardHeader, CardBody, Badge, EmptyState } from "@/components/ui";
import { getPeopledeskStaff, getPeopledeskPayroll } from "@/lib/api";
import type { PeopledeskStaff, PeopledeskPayrollRow } from "@/lib/api";

// Real, live PayU checkout link, created directly in the founder's own
// PayU merchant dashboard -- same one used everywhere else in this
// project. Founder's own instruction, 2026-08-24: keep it as the stand-in
// checkout for PeopleDesk too, for now.
const REAL_PAYU_LINK = "https://u.payu.in/xJYCpF9eG4sc";

const ATTENDANCE_OPTIONS: { value: "present" | "absent" | "half_day" | "leave"; label: string }[] = [
  { value: "present", label: "Present" },
  { value: "half_day", label: "Half day" },
  { value: "leave", label: "Leave" },
  { value: "absent", label: "Absent" },
];

function todayStr() {
  return new Date().toISOString().slice(0, 10);
}
function monthStartStr() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-01`;
}

export default function PeopleDeskPage() {
  const [email, setEmail] = useState("");
  const [emailInput, setEmailInput] = useState("");
  const [access, setAccess] = useState<{ allowed: boolean; price_inr?: number; label?: string } | null>(null);

  const [staff, setStaff] = useState<PeopledeskStaff[]>([]);
  const [payroll, setPayroll] = useState<PeopledeskPayrollRow[]>([]);
  const [dateFrom, setDateFrom] = useState(monthStartStr());
  const [dateTo, setDateTo] = useState(todayStr());

  const [name, setName] = useState("");
  const [role, setRole] = useState("");
  const [phone, setPhone] = useState("");
  const [payType, setPayType] = useState<"daily" | "monthly">("daily");
  const [wage, setWage] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const [gateway, setGateway] = useState<"razorpay" | "payu">("razorpay");
  const [razorpayKeyId, setRazorpayKeyId] = useState("");
  const [razorpaySecret, setRazorpaySecret] = useState("");
  const [payuKey, setPayuKey] = useState("");
  const [payuSalt, setPayuSalt] = useState("");
  const [checkoutStatus, setCheckoutStatus] = useState<"idle" | "loading" | "error">("idle");
  const [checkoutResult, setCheckoutResult] = useState<{ checkout?: string | object } | null>(null);

  useEffect(() => {
    const saved = window.localStorage.getItem("peopledesk_email");
    if (saved) { setEmailInput(saved); setEmail(saved); }
  }, []);

  const checkAccess = useCallback(async (addr: string) => {
    const res = await fetch(`/api/peopledesk/access?email=${encodeURIComponent(addr)}`);
    const data = await res.json();
    setAccess(data);
  }, []);

  const loadStaff = useCallback(async (addr: string) => {
    const data = await getPeopledeskStaff(addr).catch(() => ({ staff: [] }));
    setStaff(data.staff || []);
  }, []);

  const loadPayroll = useCallback(async (addr: string) => {
    const data = await getPeopledeskPayroll(addr, dateFrom, dateTo).catch(() => ({ summary: [] }));
    setPayroll(data.summary || []);
  }, [dateFrom, dateTo]);

  useEffect(() => {
    if (!email) return;
    checkAccess(email);
    loadStaff(email);
    loadPayroll(email);
  }, [email, checkAccess, loadStaff, loadPayroll]);

  function submitEmail(e: React.FormEvent) {
    e.preventDefault();
    const addr = emailInput.trim().toLowerCase();
    if (!addr) return;
    window.localStorage.setItem("peopledesk_email", addr);
    setEmail(addr);
  }

  async function addStaff(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) { setError("Staff name is required."); return; }
    if (!wage.trim()) { setError(payType === "daily" ? "Daily wage is required." : "Monthly salary is required."); return; }
    setBusy(true); setError("");
    try {
      const res = await fetch("/api/peopledesk/staff", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ownerEmail: email, name, role, phone, payType,
          dailyWageInr: payType === "daily" ? wage : undefined,
          monthlySalaryInr: payType === "monthly" ? wage : undefined,
        }),
      });
      const data = await res.json();
      if (!res.ok) { setError(data.error || "Failed to add staff."); return; }
      setName(""); setRole(""); setPhone(""); setWage("");
      await loadStaff(email);
    } catch {
      setError("Something went wrong.");
    } finally {
      setBusy(false);
    }
  }

  async function mark(staffId: number, status: string) {
    await fetch("/api/peopledesk/attendance", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ownerEmail: email, staffId, attendanceDate: todayStr(), status }),
    });
    await loadPayroll(email);
  }

  async function buyAccess() {
    setCheckoutStatus("loading"); setCheckoutResult(null);
    try {
      const res = await fetch("/api/blackboxops/subscribe", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, product: "peopledesk", gateway, razorpayKeyId, razorpaySecret, payuKey, payuSalt }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Failed to create payment link");
      setCheckoutResult(data);
      setCheckoutStatus("idle");
    } catch {
      setCheckoutStatus("error");
    }
  }

  if (!email) {
    return (
      <div className="space-y-6 max-w-md">
        <div>
          <h1 className="text-xl font-semibold">Dhansetu PeopleDesk</h1>
          <p className="text-sm text-[var(--muted-foreground)] mt-1">
            Staff directory, daily attendance, and real payroll math — for local small businesses and small
            industrial units. Enter your email to get started.
          </p>
        </div>
        <Card>
          <CardBody>
            <form onSubmit={submitEmail} className="flex gap-2">
              <input
                type="email" required placeholder="you@example.com" value={emailInput}
                onChange={(e) => setEmailInput(e.target.value)}
                className="flex-1 rounded-lg border border-[var(--border)] bg-[var(--surface-2)] px-3 py-2 text-sm text-[var(--ink)]"
              />
              <button type="submit" className="rounded-lg bg-[var(--local)] px-4 py-2 text-sm font-medium text-[var(--bg)]">
                Continue
              </button>
            </form>
          </CardBody>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div>
          <h1 className="text-xl font-semibold">Dhansetu PeopleDesk</h1>
          <p className="text-sm text-[var(--muted-foreground)] mt-1">{email}</p>
        </div>
        <Badge tone="local">₹99/month</Badge>
      </div>

      {access && !access.allowed && (
        <>
          <Card>
            <CardBody className="flex items-center justify-between gap-6 flex-wrap">
              <div>
                <div className="flex items-center gap-2 mb-1.5">
                  <span className="w-1.5 h-1.5 rounded-full" style={{ background: "#4ade80" }} />
                  <span className="text-xs font-mono uppercase tracking-wide" style={{ color: "#4ade80" }}>Live · Real PayU checkout</span>
                </div>
                <div className="text-sm font-medium text-[var(--ink)]">Quick Pay Now</div>
                <p className="text-xs text-[var(--muted-foreground)] mt-1">Real payment link. Fixed amount, kept separate from the ₹99/month price.</p>
              </div>
              <a href={REAL_PAYU_LINK} target="_blank" rel="noreferrer"
                 className="shrink-0 rounded-lg px-5 py-2.5 text-sm font-semibold" style={{ background: "#4ade80", color: "#0a0c10" }}>
                Pay Now →
              </a>
            </CardBody>
          </Card>

          <Card>
            <CardHeader title="Get monthly access — ₹99/month" subtitle="No free tier for PeopleDesk — real staff data needs a real subscription" />
            <CardBody>
              <div className="max-w-lg space-y-3">
                <div className="flex gap-2">
                  <button onClick={() => setGateway("razorpay")} className={`text-xs px-3 py-1.5 rounded-full border ${gateway === "razorpay" ? "border-[var(--local)] text-[var(--local)]" : "border-[var(--border)] text-[var(--muted-foreground)]"}`}>Razorpay</button>
                  <button onClick={() => setGateway("payu")} className={`text-xs px-3 py-1.5 rounded-full border ${gateway === "payu" ? "border-[var(--local)] text-[var(--local)]" : "border-[var(--border)] text-[var(--muted-foreground)]"}`}>PayU</button>
                </div>
                {gateway === "razorpay" ? (
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                    <input placeholder="Razorpay Key ID" value={razorpayKeyId} onChange={(e) => setRazorpayKeyId(e.target.value)} className="rounded-lg border border-[var(--border)] bg-[var(--surface-2)] px-3 py-2 text-xs" />
                    <input placeholder="Razorpay Key Secret" type="password" value={razorpaySecret} onChange={(e) => setRazorpaySecret(e.target.value)} className="rounded-lg border border-[var(--border)] bg-[var(--surface-2)] px-3 py-2 text-xs" />
                  </div>
                ) : (
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                    <input placeholder="PayU Merchant Key" value={payuKey} onChange={(e) => setPayuKey(e.target.value)} className="rounded-lg border border-[var(--border)] bg-[var(--surface-2)] px-3 py-2 text-xs" />
                    <input placeholder="PayU Merchant Salt" type="password" value={payuSalt} onChange={(e) => setPayuSalt(e.target.value)} className="rounded-lg border border-[var(--border)] bg-[var(--surface-2)] px-3 py-2 text-xs" />
                  </div>
                )}
                <button onClick={buyAccess} disabled={checkoutStatus === "loading"} className="rounded-lg bg-[var(--local)] px-4 py-2 text-sm font-medium text-[var(--bg)] disabled:opacity-50">
                  {checkoutStatus === "loading" ? "Creating payment link…" : "Create payment link"}
                </button>
                {checkoutResult?.checkout && typeof checkoutResult.checkout === "string" && (
                  <p className="text-xs" style={{ color: "#4ade80" }}>
                    Payment link created: <a href={checkoutResult.checkout} target="_blank" rel="noreferrer" className="underline">{checkoutResult.checkout}</a>
                  </p>
                )}
              </div>
            </CardBody>
          </Card>
        </>
      )}

      {access?.allowed && (
        <>
          <Card>
            <CardHeader title="Add staff" />
            <CardBody>
              <form onSubmit={addStaff} className="grid grid-cols-1 sm:grid-cols-2 gap-3 max-w-xl">
                <input placeholder="Name" value={name} onChange={(e) => setName(e.target.value)} className="rounded-lg border border-[var(--border)] bg-[var(--surface-2)] px-3 py-2 text-sm" />
                <input placeholder="Role (optional)" value={role} onChange={(e) => setRole(e.target.value)} className="rounded-lg border border-[var(--border)] bg-[var(--surface-2)] px-3 py-2 text-sm" />
                <input placeholder="Phone (optional)" value={phone} onChange={(e) => setPhone(e.target.value)} className="rounded-lg border border-[var(--border)] bg-[var(--surface-2)] px-3 py-2 text-sm" />
                <select value={payType} onChange={(e) => setPayType(e.target.value as "daily" | "monthly")} className="rounded-lg border border-[var(--border)] bg-[var(--surface-2)] px-3 py-2 text-sm">
                  <option value="daily">Daily wage</option>
                  <option value="monthly">Monthly salary</option>
                </select>
                <input
                  placeholder={payType === "daily" ? "Daily wage (₹)" : "Monthly salary (₹)"} type="number" value={wage}
                  onChange={(e) => setWage(e.target.value)} className="rounded-lg border border-[var(--border)] bg-[var(--surface-2)] px-3 py-2 text-sm sm:col-span-2"
                />
                {error && <p className="text-xs text-[var(--bad)] sm:col-span-2">{error}</p>}
                <button type="submit" disabled={busy} className="rounded-lg bg-[var(--local)] px-4 py-2 text-sm font-medium text-[var(--bg)] disabled:opacity-50 sm:col-span-2">
                  {busy ? "Adding…" : "Add staff member"}
                </button>
              </form>
            </CardBody>
          </Card>

          <Card>
            <CardHeader title="Staff & today's attendance" subtitle={todayStr()} />
            <CardBody className="space-y-3">
              {staff.length === 0 ? (
                <EmptyState>No staff added yet.</EmptyState>
              ) : (
                staff.map((s) => (
                  <div key={s.id} className="rounded-lg border border-[var(--border)] p-3">
                    <div className="flex items-center justify-between flex-wrap gap-2 mb-2">
                      <div>
                        <div className="text-sm font-medium">{s.name}</div>
                        <div className="text-xs text-[var(--muted-foreground)]">
                          {s.role || "—"} · {s.pay_type === "daily" ? `₹${s.daily_wage_inr}/day` : `₹${s.monthly_salary_inr}/month`}
                        </div>
                      </div>
                    </div>
                    <div className="flex gap-1.5 flex-wrap">
                      {ATTENDANCE_OPTIONS.map((opt) => (
                        <button
                          key={opt.value} onClick={() => mark(s.id, opt.value)}
                          className="text-xs px-2.5 py-1.5 rounded-full border border-[var(--border)] text-[var(--muted-foreground)] hover:text-[var(--ink)] hover:border-[var(--local)]"
                        >
                          {opt.label}
                        </button>
                      ))}
                    </div>
                  </div>
                ))
              )}
            </CardBody>
          </Card>

          <Card>
            <CardHeader
              title="Payroll summary"
              subtitle="Daily-wage: present + half-day × wage. Monthly: flat salary, regardless of attendance."
              action={
                <div className="flex gap-2 items-center">
                  <input type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} className="rounded-lg border border-[var(--border)] bg-[var(--surface-2)] px-2 py-1 text-xs" />
                  <span className="text-xs text-[var(--muted-foreground)]">to</span>
                  <input type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} className="rounded-lg border border-[var(--border)] bg-[var(--surface-2)] px-2 py-1 text-xs" />
                  <button onClick={() => loadPayroll(email)} className="text-xs px-2.5 py-1.5 rounded-full border border-[var(--local)] text-[var(--local)]">Refresh</button>
                </div>
              }
            />
            <CardBody className="p-0">
              {payroll.length === 0 ? (
                <div className="p-5"><EmptyState>No staff to summarize yet.</EmptyState></div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="text-left text-[11px] uppercase tracking-wide text-[var(--muted-foreground)] border-b border-[var(--border)]">
                        <th className="px-4 py-2 font-medium">Name</th>
                        <th className="px-4 py-2 font-medium">Present</th>
                        <th className="px-4 py-2 font-medium">Half</th>
                        <th className="px-4 py-2 font-medium">Leave</th>
                        <th className="px-4 py-2 font-medium">Absent</th>
                        <th className="px-4 py-2 font-medium">Amount</th>
                      </tr>
                    </thead>
                    <tbody>
                      {payroll.map((p) => (
                        <tr key={p.staff_id} className="border-b border-[var(--border)] last:border-0">
                          <td className="px-4 py-2">{p.name}</td>
                          <td className="px-4 py-2 font-mono-num">{p.present_days}</td>
                          <td className="px-4 py-2 font-mono-num">{p.half_days}</td>
                          <td className="px-4 py-2 font-mono-num">{p.leave_days}</td>
                          <td className="px-4 py-2 font-mono-num">{p.absent_days}</td>
                          <td className="px-4 py-2 font-mono-num font-medium">₹{p.amount_inr.toLocaleString("en-IN")}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </CardBody>
          </Card>
        </>
      )}
    </div>
  );
}
