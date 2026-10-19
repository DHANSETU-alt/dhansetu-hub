import { getPaymentLinks, getGatewayActivity } from "@/lib/api";
import { Card, CardHeader, CardBody, Badge, StatTile, EmptyState } from "@/components/ui";
import { AutoRefresh } from "@/components/AutoRefresh";

const STATUS_TONE: Record<string, "good" | "warn" | "bad" | "neutral"> = {
  paid: "good", partially_paid: "warn", created: "neutral", cancelled: "bad", expired: "bad",
};

const GATEWAY_LABEL: Record<string, string> = {
  razorpay_link: "Razorpay (Payment Links)", razorpay_subscription: "Razorpay (Subscriptions)",
  stripe_checkout: "Stripe", upi: "UPI",
};

export default async function PaymentsDashboardPage() {
  const [{ payment_links, total_paid_inr }, { gateways }] = await Promise.all([getPaymentLinks(50), getGatewayActivity()]);
  const pending = payment_links.filter((p) => p.status === "created" || p.status === "partially_paid");

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold">Payments</h1>
          <p className="text-sm text-[var(--muted-foreground)] mt-1">
            Razorpay Payment Links — Offer A (Website Health Audit) and any other paid work. Status is checked on
            demand (<code>--check-payment</code>), not pushed — this system has no public webhook receiver.
          </p>
        </div>
        <AutoRefresh intervalSeconds={5} />
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatTile label="Total Collected" value={`₹${total_paid_inr.toLocaleString("en-IN")}`} tone="good" />
        <StatTile label="Links Created" value={String(payment_links.length)} />
        <StatTile label="Pending" value={String(pending.length)} tone={pending.length ? "warn" : "good"} />
        <StatTile label="Paid" value={String(payment_links.filter((p) => p.status === "paid").length)} tone="good" />
      </div>

      <Card>
        <CardHeader title="Payment Links" subtitle={`${payment_links.length} created`} />
        <CardBody className="p-0">
          {payment_links.length === 0 ? (
            <EmptyState>
              No payment links yet. Run{" "}
              <code>
                python3 -m orchestrator.cli --create-payment-link --razorpay-key-id KEY --razorpay-key-secret SECRET
                --razorpay-amount 999 --description &quot;Website Health Audit&quot;
              </code>
            </EmptyState>
          ) : (
            <div className="divide-y divide-[var(--border)]">
              {payment_links.map((p) => (
                <div key={p.id} className="px-5 py-3">
                  <div className="flex items-center justify-between gap-3">
                    <span className="text-sm font-medium">
                      #{p.id} · ₹{p.amount_inr.toLocaleString("en-IN")} · {p.description}
                    </span>
                    <Badge tone={STATUS_TONE[p.status] ?? "neutral"}>{p.status}</Badge>
                  </div>
                  <div className="mt-1.5 flex items-center gap-4 text-xs text-[var(--muted-foreground)]">
                    <span>{p.customer_name || "(no name)"}</span>
                    <a href={p.short_url} target="_blank" rel="noreferrer" className="underline">
                      {p.short_url}
                    </a>
                    <span className="font-mono-num">{p.created_at}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardBody>
      </Card>

      <Card>
        <CardHeader title="Gateway Activity" subtitle="Real usage history — no live credential check (this project never stores payment credentials, see payments.py)" />
        <CardBody className="p-0">
          {Object.keys(gateways).length === 0 ? (
            <EmptyState>No gateway activity yet — Razorpay, Stripe, and UPI all start here once used.</EmptyState>
          ) : (
            <div className="divide-y divide-[var(--border)]">
              {Object.entries(gateways).map(([gateway, g]) => (
                <div key={gateway} className="px-5 py-3 flex items-center justify-between">
                  <span className="text-sm font-medium">{GATEWAY_LABEL[gateway] ?? gateway}</span>
                  <div className="flex items-center gap-4 text-xs text-[var(--muted-foreground)]">
                    <span>{g.count} used</span>
                    <span>{g.paid_count} paid</span>
                    <span className="font-mono-num">{g.last_used || "—"}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardBody>
      </Card>
    </div>
  );
}
