"use client";

import { useState, useEffect, useCallback } from "react";
import { Card, CardHeader, CardBody, Badge, EmptyState } from "@/components/ui";
import {
  getTradingStrategies, getTradingPositions, getTradingJournal, getTradingPrice,
  type TradingStrategy, type PaperPosition, type TradingJournalEntry,
} from "@/lib/api";

const RULE_LABEL: Record<string, string> = { sma_crossover: "SMA Crossover", rsi_threshold: "RSI Threshold" };

export default function TradingPage() {
  const [strategies, setStrategies] = useState<TradingStrategy[]>([]);
  const [positions, setPositions] = useState<PaperPosition[]>([]);
  const [journal, setJournal] = useState<TradingJournalEntry[]>([]);
  const [prices, setPrices] = useState<Record<string, number>>({});
  const [checking, setChecking] = useState(false);
  const [checkResult, setCheckResult] = useState<string>("");

  const [name, setName] = useState("");
  const [symbol, setSymbol] = useState("BTCUSDT");
  const [ruleType, setRuleType] = useState<"sma_crossover" | "rsi_threshold">("sma_crossover");
  const [fastPeriod, setFastPeriod] = useState("10");
  const [slowPeriod, setSlowPeriod] = useState("30");
  const [rsiPeriod, setRsiPeriod] = useState("14");
  const [oversold, setOversold] = useState("30");
  const [overbought, setOverbought] = useState("70");
  const [quantity, setQuantity] = useState("0.001");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const loadAll = useCallback(async () => {
    const [s, p, j] = await Promise.all([
      getTradingStrategies().catch(() => ({ strategies: [] })),
      getTradingPositions().catch(() => ({ positions: [] })),
      getTradingJournal(50).catch(() => ({ journal: [] })),
    ]);
    setStrategies(s.strategies);
    setPositions(p.positions);
    setJournal(j.journal);

    const symbols = [...new Set(s.strategies.map((st) => st.symbol))];
    const priceEntries = await Promise.all(
      symbols.map((sym) => getTradingPrice(sym).catch(() => ({ symbol: sym, price: NaN })))
    );
    setPrices(Object.fromEntries(priceEntries.map((pe) => [pe.symbol, pe.price])));
  }, []);

  useEffect(() => {
    loadAll();
    // 3s -- fast enough to feel live, safely under Binance's public API
    // rate limits (a much faster interval risks the whole feed getting
    // temporarily rate-limited, not just this page slowing down).
    const id = setInterval(loadAll, 3000);
    return () => clearInterval(id);
  }, [loadAll]);

  async function addStrategy(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) { setError("Strategy name is required."); return; }
    const params =
      ruleType === "sma_crossover"
        ? { fast_period: Number(fastPeriod), slow_period: Number(slowPeriod), trade_quantity: Number(quantity) }
        : { period: Number(rsiPeriod), oversold: Number(oversold), overbought: Number(overbought), trade_quantity: Number(quantity) };

    setBusy(true); setError("");
    try {
      const res = await fetch("/api/trading/strategy", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, symbol, ruleType, params }),
      });
      const data = await res.json();
      if (!res.ok) { setError(data.error || "Failed to create strategy."); return; }
      setName("");
      await loadAll();
    } catch {
      setError("Something went wrong.");
    } finally {
      setBusy(false);
    }
  }

  async function toggleStrategy(strategyId: number, current: string) {
    await fetch("/api/trading/strategy-status", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ strategyId, status: current === "active" ? "paused" : "active" }),
    });
    await loadAll();
  }

  async function runCheck() {
    setChecking(true); setCheckResult("");
    try {
      const res = await fetch("/api/trading/check", { method: "POST" });
      const data = await res.json();
      const actions = (data.results || []).filter((r: { action: string }) => r.action !== "hold");
      setCheckResult(actions.length ? `${actions.length} action(s) taken -- see journal below` : "Checked -- no signals crossed, no action taken");
      await loadAll();
    } catch {
      setCheckResult("Check failed.");
    } finally {
      setChecking(false);
    }
  }

  const openPositions = positions.filter((p) => p.status === "open");
  const closedTrades = journal.filter((j) => j.action === "exit");
  const totalPnl = closedTrades.reduce((sum, j) => sum + (j.pnl || 0), 0);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div>
          <h1 className="text-xl font-semibold">Trading OS — Paper Trading</h1>
          <p className="text-sm text-[var(--muted-foreground)] mt-1">
            Crypto spot, simulated fills only — no real broker orders, no real money. Real market data (Binance
            public API), real SMA/RSI math, every fill auto-journaled below.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Badge tone="warn">Paper trading</Badge>
          <span className="text-xs px-2.5 py-1.5 rounded-full border border-[var(--local)] text-[var(--local)]">live (3s)</span>
          <button onClick={runCheck} disabled={checking} className="rounded-lg bg-[var(--local)] px-4 py-2 text-sm font-medium text-[var(--bg)] disabled:opacity-50">
            {checking ? "Checking…" : "Run Signal Check"}
          </button>
        </div>
      </div>

      {checkResult && <p className="text-xs text-[var(--muted-foreground)]">{checkResult}</p>}

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="glass rounded-xl p-4">
          <div className="text-[11px] uppercase tracking-wide text-[var(--muted-foreground)]">Active Strategies</div>
          <div className="text-2xl font-semibold font-mono-num mt-1">{strategies.filter((s) => s.status === "active").length}</div>
        </div>
        <div className="glass rounded-xl p-4">
          <div className="text-[11px] uppercase tracking-wide text-[var(--muted-foreground)]">Open Positions</div>
          <div className="text-2xl font-semibold font-mono-num mt-1">{openPositions.length}</div>
        </div>
        <div className="glass rounded-xl p-4">
          <div className="text-[11px] uppercase tracking-wide text-[var(--muted-foreground)]">Closed Trades</div>
          <div className="text-2xl font-semibold font-mono-num mt-1">{closedTrades.length}</div>
        </div>
        <div className="glass rounded-xl p-4">
          <div className="text-[11px] uppercase tracking-wide text-[var(--muted-foreground)]">Total P&amp;L (simulated)</div>
          <div className="text-2xl font-semibold font-mono-num mt-1" style={{ color: totalPnl >= 0 ? "var(--good)" : "var(--bad)" }}>
            {totalPnl >= 0 ? "+" : ""}{totalPnl.toFixed(2)}
          </div>
        </div>
      </div>

      <Card>
        <CardHeader title="Add strategy" subtitle="Two real, standard rules for Phase 1 — not an open-ended DSL yet" />
        <CardBody>
          <form onSubmit={addStrategy} className="grid grid-cols-1 sm:grid-cols-2 gap-3 max-w-2xl">
            <input placeholder="Strategy name" value={name} onChange={(e) => setName(e.target.value)} className="rounded-lg border border-[var(--border)] bg-[var(--surface-2)] px-3 py-2 text-sm" />
            <input placeholder="Symbol (e.g. BTCUSDT)" value={symbol} onChange={(e) => setSymbol(e.target.value.toUpperCase())} className="rounded-lg border border-[var(--border)] bg-[var(--surface-2)] px-3 py-2 text-sm font-mono" />
            <select value={ruleType} onChange={(e) => setRuleType(e.target.value as "sma_crossover" | "rsi_threshold")} className="rounded-lg border border-[var(--border)] bg-[var(--surface-2)] px-3 py-2 text-sm sm:col-span-2">
              <option value="sma_crossover">SMA Crossover</option>
              <option value="rsi_threshold">RSI Threshold</option>
            </select>

            {ruleType === "sma_crossover" ? (
              <>
                <input placeholder="Fast period" type="number" value={fastPeriod} onChange={(e) => setFastPeriod(e.target.value)} className="rounded-lg border border-[var(--border)] bg-[var(--surface-2)] px-3 py-2 text-sm" />
                <input placeholder="Slow period" type="number" value={slowPeriod} onChange={(e) => setSlowPeriod(e.target.value)} className="rounded-lg border border-[var(--border)] bg-[var(--surface-2)] px-3 py-2 text-sm" />
              </>
            ) : (
              <>
                <input placeholder="RSI period" type="number" value={rsiPeriod} onChange={(e) => setRsiPeriod(e.target.value)} className="rounded-lg border border-[var(--border)] bg-[var(--surface-2)] px-3 py-2 text-sm" />
                <div className="grid grid-cols-2 gap-2">
                  <input placeholder="Oversold" type="number" value={oversold} onChange={(e) => setOversold(e.target.value)} className="rounded-lg border border-[var(--border)] bg-[var(--surface-2)] px-3 py-2 text-sm" />
                  <input placeholder="Overbought" type="number" value={overbought} onChange={(e) => setOverbought(e.target.value)} className="rounded-lg border border-[var(--border)] bg-[var(--surface-2)] px-3 py-2 text-sm" />
                </div>
              </>
            )}
            <input placeholder="Trade quantity (e.g. 0.001)" type="number" step="any" value={quantity} onChange={(e) => setQuantity(e.target.value)} className="rounded-lg border border-[var(--border)] bg-[var(--surface-2)] px-3 py-2 text-sm sm:col-span-2" />

            {error && <p className="text-xs text-[var(--bad)] sm:col-span-2">{error}</p>}
            <button type="submit" disabled={busy} className="rounded-lg bg-[var(--local)] px-4 py-2 text-sm font-medium text-[var(--bg)] disabled:opacity-50 sm:col-span-2">
              {busy ? "Creating…" : "Create strategy"}
            </button>
          </form>
        </CardBody>
      </Card>

      <Card>
        <CardHeader title="Strategies" />
        <CardBody className="space-y-2">
          {strategies.length === 0 ? (
            <EmptyState>No strategies yet.</EmptyState>
          ) : (
            strategies.map((s) => (
              <div key={s.id} className="flex items-center justify-between flex-wrap gap-2 rounded-lg border border-[var(--border)] p-3">
                <div>
                  <div className="text-sm font-medium">{s.name} <span className="text-[var(--muted-foreground)] font-mono text-xs">{s.symbol}</span></div>
                  <div className="text-xs text-[var(--muted-foreground)] mt-0.5">
                    {RULE_LABEL[s.rule_type]} · {JSON.stringify(s.params)}
                    {!isNaN(prices[s.symbol]) && <span className="ml-2 font-mono-num">· live: {prices[s.symbol]}</span>}
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <Badge tone={s.status === "active" ? "good" : "neutral"}>{s.status}</Badge>
                  <button onClick={() => toggleStrategy(s.id, s.status)} className="text-xs px-2.5 py-1.5 rounded-full border border-[var(--border)] text-[var(--muted-foreground)] hover:text-[var(--ink)]">
                    {s.status === "active" ? "Pause" : "Resume"}
                  </button>
                </div>
              </div>
            ))
          )}
        </CardBody>
      </Card>

      <Card>
        <CardHeader title="Open positions" />
        <CardBody className="p-0">
          {openPositions.length === 0 ? (
            <div className="p-5"><EmptyState>No open positions.</EmptyState></div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-[11px] uppercase tracking-wide text-[var(--muted-foreground)] border-b border-[var(--border)]">
                    <th className="px-4 py-2 font-medium">Symbol</th>
                    <th className="px-4 py-2 font-medium">Quantity</th>
                    <th className="px-4 py-2 font-medium">Entry price</th>
                    <th className="px-4 py-2 font-medium">Live price</th>
                    <th className="px-4 py-2 font-medium">Unrealized P&amp;L</th>
                    <th className="px-4 py-2 font-medium">Opened</th>
                  </tr>
                </thead>
                <tbody>
                  {openPositions.map((p) => {
                    const live = prices[p.symbol];
                    const upnl = !isNaN(live) ? (live - p.entry_price) * p.quantity : null;
                    return (
                      <tr key={p.id} className="border-b border-[var(--border)] last:border-0">
                        <td className="px-4 py-2 font-mono">{p.symbol}</td>
                        <td className="px-4 py-2 font-mono-num">{p.quantity}</td>
                        <td className="px-4 py-2 font-mono-num">{p.entry_price.toFixed(2)}</td>
                        <td className="px-4 py-2 font-mono-num">{!isNaN(live) ? live.toFixed(2) : "—"}</td>
                        <td className="px-4 py-2 font-mono-num" style={{ color: upnl == null ? undefined : upnl >= 0 ? "var(--good)" : "var(--bad)" }}>
                          {upnl == null ? "—" : `${upnl >= 0 ? "+" : ""}${upnl.toFixed(2)}`}
                        </td>
                        <td className="px-4 py-2 text-[var(--muted-foreground)]">{p.opened_at}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </CardBody>
      </Card>

      <Card>
        <CardHeader title="Trading journal" subtitle="Every simulated fill, auto-saved — append-only" />
        <CardBody className="p-0">
          {journal.length === 0 ? (
            <div className="p-5"><EmptyState>No trades yet. Add a strategy and run a signal check.</EmptyState></div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-[11px] uppercase tracking-wide text-[var(--muted-foreground)] border-b border-[var(--border)]">
                    <th className="px-4 py-2 font-medium">Time</th>
                    <th className="px-4 py-2 font-medium">Symbol</th>
                    <th className="px-4 py-2 font-medium">Action</th>
                    <th className="px-4 py-2 font-medium">Quantity</th>
                    <th className="px-4 py-2 font-medium">Price</th>
                    <th className="px-4 py-2 font-medium">P&amp;L</th>
                    <th className="px-4 py-2 font-medium">Reason</th>
                  </tr>
                </thead>
                <tbody>
                  {journal.map((j) => (
                    <tr key={j.id} className="border-b border-[var(--border)] last:border-0">
                      <td className="px-4 py-2 text-[var(--muted-foreground)] font-mono-num">{j.executed_at}</td>
                      <td className="px-4 py-2 font-mono">{j.symbol}</td>
                      <td className="px-4 py-2"><Badge tone={j.action === "entry" ? "local" : "neutral"}>{j.action}</Badge></td>
                      <td className="px-4 py-2 font-mono-num">{j.quantity}</td>
                      <td className="px-4 py-2 font-mono-num">{j.price.toFixed(2)}</td>
                      <td className="px-4 py-2 font-mono-num" style={{ color: j.pnl == null ? undefined : j.pnl >= 0 ? "var(--good)" : "var(--bad)" }}>
                        {j.pnl == null ? "—" : `${j.pnl >= 0 ? "+" : ""}${j.pnl.toFixed(2)}`}
                      </td>
                      <td className="px-4 py-2 text-[var(--muted-foreground)] text-xs">{j.reason}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardBody>
      </Card>
    </div>
  );
}
