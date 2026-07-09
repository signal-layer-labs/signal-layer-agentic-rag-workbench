// Types mirror the FastAPI response schemas the UI consumes.

export interface SalesSummary {
  total_revenue: number | string;
  total_quantity: number;
  number_of_sales: number;
  unique_customers: number;
  top_region: string | null;
  top_channel: string | null;
}

export interface ExecutionPlanStep {
  step: number;
  name: string;
  status: "pending" | "completed" | "failed" | "skipped";
  details?: string | null;
}

export interface GeneratedResponse {
  content: string;
  provider: string;
  model: string;
}

export interface AgentRunResponse {
  run_id: string;
  status: string;
  business_question: string;
  execution_plan: ExecutionPlanStep[];
  trace: {
    documents_retrieved: number;
    customers_returned: number;
    sales_summary: SalesSummary;
  };
  summary: string;
  generated_response: GeneratedResponse | null;
}

export interface DocumentSearchResult {
  chunk_id: string;
  document: string;
  metadata: Record<string, string | number | boolean>;
  distance: number | null;
}

export interface RunOptions {
  region: string | null;
  channel: string | null;
  segment: string | null;
}

const DEMO_KEY_STORAGE = "sl_demo_key";

function headers(): Record<string, string> {
  const h: Record<string, string> = { "Content-Type": "application/json" };
  const key = localStorage.getItem(DEMO_KEY_STORAGE);
  if (key) h["X-Demo-API-Key"] = key;
  return h;
}

async function readError(res: Response): Promise<string> {
  try {
    const body = await res.json();
    return body?.error?.message ?? "Request failed.";
  } catch {
    return "Request failed.";
  }
}

export function getDemoKey(): string {
  return localStorage.getItem(DEMO_KEY_STORAGE) ?? "";
}

export function setDemoKey(value: string): void {
  if (value.trim()) localStorage.setItem(DEMO_KEY_STORAGE, value.trim());
  else localStorage.removeItem(DEMO_KEY_STORAGE);
}

export async function runAgent(
  question: string,
  opts: RunOptions,
): Promise<AgentRunResponse> {
  const res = await fetch("/agent/run", {
    method: "POST",
    headers: headers(),
    body: JSON.stringify({
      business_question: question,
      retrieval_query: question,
      sales_region: opts.region,
      sales_channel: opts.channel,
      customer_segment: opts.segment,
      generate_response: true,
    }),
  });
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function searchDocuments(
  query: string,
  limit = 4,
): Promise<DocumentSearchResult[]> {
  const res = await fetch("/documents/search", {
    method: "POST",
    headers: headers(),
    body: JSON.stringify({ query, limit }),
  });
  if (!res.ok) throw new Error(await readError(res));
  const body = await res.json();
  return body.results ?? [];
}

export interface IngestResult {
  document_id: string;
  title: string;
  source: string;
  chunks_created: number;
  status: string;
}

function multipartHeaders(): Record<string, string> {
  const h: Record<string, string> = {};
  const key = localStorage.getItem(DEMO_KEY_STORAGE);
  if (key) h["X-Demo-API-Key"] = key;
  return h;
}

export async function ingestText(payload: {
  title: string;
  source: string;
  content: string;
  metadata: Record<string, string>;
}): Promise<IngestResult> {
  const res = await fetch("/documents/ingest", {
    method: "POST",
    headers: headers(),
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function ingestFile(
  file: File,
  metadata: Record<string, string>,
): Promise<IngestResult> {
  const form = new FormData();
  form.append("file", file);
  if (Object.keys(metadata).length > 0) {
    form.append("metadata", JSON.stringify(metadata));
  }
  const res = await fetch("/documents/parse-ingest", {
    method: "POST",
    headers: multipartHeaders(),
    body: form,
  });
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

// Per-browser question history (there is no list-all runs endpoint).
export interface HistoryItem {
  id: string;
  question: string;
  ts: number;
  run: AgentRunResponse;
  sources: DocumentSearchResult[];
}

const HISTORY_KEY = "sl_history";

export function loadHistory(): HistoryItem[] {
  try {
    return JSON.parse(localStorage.getItem(HISTORY_KEY) ?? "[]");
  } catch {
    return [];
  }
}

export function pushHistory(item: HistoryItem): HistoryItem[] {
  const list = loadHistory().filter((h) => h.id !== item.id);
  list.unshift(item);
  const trimmed = list.slice(0, 50);
  localStorage.setItem(HISTORY_KEY, JSON.stringify(trimmed));
  return trimmed;
}

export function clearHistory(): void {
  localStorage.removeItem(HISTORY_KEY);
}
