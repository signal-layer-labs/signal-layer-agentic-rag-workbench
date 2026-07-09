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
): Promise<DocumentSearchResult[]> {
  try {
    const res = await fetch("/documents/search", {
      method: "POST",
      headers: headers(),
      body: JSON.stringify({ query, limit: 4 }),
    });
    if (!res.ok) return [];
    const body = await res.json();
    return body.results ?? [];
  } catch {
    return [];
  }
}
