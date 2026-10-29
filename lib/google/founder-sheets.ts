import { google } from "googleapis";
import type { FounderDashboardData } from "@/lib/founder/dashboard-data";

const TAB_NAMES = ["Plan", "Revenue", "Goals", "Trading", "Marketing", "Audit"] as const;

export type FounderSheetSyncResult = {
  spreadsheetId: string;
  tabs: string[];
  rowsWritten: number;
};

type ServiceAccountCredentials = {
  client_email: string;
  private_key: string;
};

function parseCredentials(raw: string | undefined): ServiceAccountCredentials {
  if (!raw) throw new Error("Founder Sheets service account is not configured");
  let parsed: unknown;
  try {
    parsed = JSON.parse(Buffer.from(raw, "base64url").toString("utf8"));
  } catch {
    throw new Error("Founder Sheets service account configuration is invalid");
  }
  if (!parsed || typeof parsed !== "object") throw new Error("Founder Sheets service account configuration is invalid");
  const record = parsed as Record<string, unknown>;
  if (typeof record.client_email !== "string" || typeof record.private_key !== "string") {
    throw new Error("Founder Sheets service account configuration is incomplete");
  }
  return { client_email: record.client_email, private_key: record.private_key };
}

function quoteTab(tab: string) {
  return `'${tab.replaceAll("'", "''")}'`;
}

function buildRows(data: FounderDashboardData, syncedAt: string) {
  return {
    Plan: [
      ["Metric", "Value", "Updated at"],
      ["System", "DhanSetu Hub", syncedAt],
      ["Authentication boundary", "Supabase customer login", syncedAt],
      ["Founder boundary", "Server-only service account", syncedAt],
    ],
    Revenue: [
      ["Metric", "Amount (paise)", "Count", "Updated at"],
      ["Gross paid", data.gross, data.paidOrders, syncedAt],
      ["Recorded costs", data.cost, "", syncedAt],
      ["Commission accrued", data.commission, "", syncedAt],
      ["Net after recorded costs", data.net, "", syncedAt],
    ],
    Goals: [
      ["Goal", "Status", "Updated at"],
      ["DhanSetu ₹1 crore mission", "Tracked from server-derived revenue only", syncedAt],
      ["Customer data ownership", "Customer data is not copied to founder ledger", syncedAt],
    ],
    Trading: [
      ["Metric", "Value", "Updated at"],
      ["Trading records", "Not synced by this endpoint", syncedAt],
      ["Safety boundary", "Paper-only unless separately approved", syncedAt],
    ],
    Marketing: [
      ["Metric", "Value", "Updated at"],
      ["Marketing records", "Not synced by this endpoint", syncedAt],
      ["Consent boundary", "No customer contact data exported", syncedAt],
    ],
    Audit: [
      ["Check", "Result", "Updated at"],
      ["Founder dashboard sync", "Completed", syncedAt],
      ["Customer sheet access", "Not requested or stored", syncedAt],
      ["Data source warnings", data.warnings.length ? data.warnings.join(" | ") : "None", syncedAt],
    ],
  } satisfies Record<(typeof TAB_NAMES)[number], Array<Array<string | number>>>;
}

export async function syncFounderSheet(data: FounderDashboardData): Promise<FounderSheetSyncResult> {
  const spreadsheetId = process.env.GOOGLE_SHEETS_SPREADSHEET_ID?.trim();
  if (!spreadsheetId) throw new Error("Founder Sheets spreadsheet ID is not configured");

  const credentials = parseCredentials(process.env.GOOGLE_SERVICE_ACCOUNT_JSON_B64);
  const auth = new google.auth.JWT({
    email: credentials.client_email,
    key: credentials.private_key,
    scopes: ["https://www.googleapis.com/auth/spreadsheets"],
  });
  const sheets = google.sheets({ version: "v4", auth });
  const metadata = await sheets.spreadsheets.get({ spreadsheetId, fields: "sheets.properties" });
  const existing = new Set((metadata.data.sheets ?? []).map((sheet) => sheet.properties?.title).filter((title): title is string => Boolean(title)));
  const missing = TAB_NAMES.filter((tab) => !existing.has(tab));
  if (missing.length) {
    await sheets.spreadsheets.batchUpdate({
      spreadsheetId,
      requestBody: { requests: missing.map((title) => ({ addSheet: { properties: { title } } })) },
    });
  }

  const syncedAt = new Date().toISOString();
  const rows = buildRows(data, syncedAt);
  const valueRanges = TAB_NAMES.map((tab) => ({
    range: `${quoteTab(tab)}!A1`,
    values: rows[tab],
  }));
  await sheets.spreadsheets.values.batchUpdate({
    spreadsheetId,
    requestBody: { valueInputOption: "USER_ENTERED", data: valueRanges },
  });
  return { spreadsheetId, tabs: [...TAB_NAMES], rowsWritten: valueRanges.reduce((sum, range) => sum + range.values.length, 0) };
}

export const founderSheetTabs = TAB_NAMES;
