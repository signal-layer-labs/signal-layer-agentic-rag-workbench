import type { Lang, Strings } from "./i18n";
import type { AgentRunResponse, DocumentSearchResult } from "./api";

function Hex({ size = 20, faded = false }: { size?: number; faded?: boolean }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24">
      <path d="M12 2 3 7l9 5 9-5-9-5Z" fill="#fff" />
      <path d="M3 12l9 5 9-5" stroke="#e9d5ff" strokeWidth="2" fill="none" />
      {!faded && (
        <path d="M3 17l9 5 9-5" stroke="#c4b5fd" strokeWidth="2" fill="none" />
      )}
    </svg>
  );
}

export function Header({
  lang,
  s,
  onLang,
  onKey,
}: {
  lang: Lang;
  s: Strings;
  onLang: (l: Lang) => void;
  onKey: () => void;
}) {
  return (
    <header>
      <div className="brand">
        <div className="logo">
          <Hex />
        </div>
        <div className="bname">
          Signal Layer<small>{s.tagline}</small>
        </div>
      </div>
      <nav>
        <button className="on">{s.nav_ask}</button>
        <button>{s.nav_docs}</button>
        <button>{s.nav_history}</button>
      </nav>
      <div className="spacer" />
      <div className="ctrls">
        <div className="lang">
          <button className={lang === "en" ? "on" : ""} onClick={() => onLang("en")}>
            EN
          </button>
          <button className={lang === "pt" ? "on" : ""} onClick={() => onLang("pt")}>
            PT
          </button>
        </div>
        <button className="iconbtn" title="API key" onClick={onKey}>
          <svg width="18" height="18" viewBox="0 0 24 24">
            <circle cx="8" cy="8" r="4.5" fill="none" stroke="currentColor" strokeWidth="1.7" />
            <path d="M11 11l8 8m-3 0l3-3m-6 0l2 2" stroke="currentColor" strokeWidth="1.7" fill="none" strokeLinecap="round" />
          </svg>
        </button>
        <div className="ava">
          <svg width="20" height="20" viewBox="0 0 24 24">
            <circle cx="12" cy="8.5" r="3.6" fill="#6d28d9" />
            <path d="M4.5 20c0-3.8 3.4-6 7.5-6s7.5 2.2 7.5 6" fill="#6d28d9" />
          </svg>
        </div>
      </div>
    </header>
  );
}

export function EmptyState({ s, onPick }: { s: Strings; onPick: (q: string) => void }) {
  return (
    <div className="empty">
      <h1>{s.empty_title}</h1>
      <p>{s.empty_sub}</p>
      <div className="examples">
        {s.examples.map((ex) => (
          <button key={ex} className="chip" onClick={() => onPick(ex)}>
            {ex}
          </button>
        ))}
      </div>
    </div>
  );
}

function currency(v: number | string, lang: Lang): string {
  const cfg = lang === "pt" ? { l: "pt-BR", c: "BRL" } : { l: "en-US", c: "USD" };
  return new Intl.NumberFormat(cfg.l, {
    style: "currency",
    currency: cfg.c,
    maximumFractionDigits: 0,
  }).format(Number(v || 0));
}
function num(v: number, lang: Lang): string {
  return new Intl.NumberFormat(lang === "pt" ? "pt-BR" : "en-US").format(Number(v || 0));
}

function DocIcon() {
  return (
    <svg width="19" height="19" viewBox="0 0 24 24">
      <path d="M6 3h9l4 4v14a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1Z" fill="none" stroke="#6d28d9" strokeWidth="1.5" />
      <g stroke="#6d28d9" strokeWidth="1.4">
        <line x1="8" y1="12" x2="16" y2="12" />
        <line x1="8" y1="16" x2="14" y2="16" />
      </g>
    </svg>
  );
}

export function Results({
  s,
  lang,
  question,
  run,
  sources,
  onFollow,
}: {
  s: Strings;
  lang: Lang;
  question: string;
  run: AgentRunResponse;
  sources: DocumentSearchResult[];
  onFollow: (q: string) => void;
}) {
  const sum = run.trace?.sales_summary;
  const answer = run.generated_response?.content || run.summary || "";
  const topmix = [sum?.top_region, sum?.top_channel].filter(Boolean).join(" · ") || "—";

  return (
    <div>
      <section>
        <div className="qlabel">{s.your_question}</div>
        <div className="question">{question}</div>
      </section>

      <section>
        <div className="answer">
          <div className="ahead">
            <div className="aicon">
              <Hex size={21} faded />
            </div>
            <div>
              <div className="t">{s.answer}</div>
              <div className="s">{s.answer_sub}</div>
            </div>
            <div className="badge">{s.controlled}</div>
          </div>
          <div className="atext">{answer}</div>
        </div>
      </section>

      <section className="kpis">
        <Kpi label={s.revenue} value={currency(sum?.total_revenue ?? 0, lang)} caption={s.overall} />
        <Kpi label={s.sales} value={num(sum?.number_of_sales ?? 0, lang)} caption={s.overall} />
        <Kpi label={s.customers} value={num(sum?.unique_customers ?? 0, lang)} caption={s.overall} />
        <Kpi label={s.topmix} value={topmix} />
      </section>

      {sources.length > 0 && (
        <section>
          <div className="seclabel">
            <svg width="16" height="16" viewBox="0 0 24 24">
              <path d="M4 4h11l5 5v11a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V5a1 1 0 0 1 1-1Z" fill="none" stroke="#475467" strokeWidth="1.6" />
            </svg>
            <span>{s.sources}</span>
          </div>
          <div className="sources">
            {sources.map((r) => (
              <Source key={r.chunk_id} r={r} fallback={s.document_excerpt} />
            ))}
          </div>
        </section>
      )}

      <section>
        <div className="seclabel">{s.related}</div>
        <div className="followups">
          {s.follow.map((f) => (
            <button key={f} className="chip" onClick={() => onFollow(f)}>
              {f}
            </button>
          ))}
        </div>
      </section>

      <section>
        <details className="trace">
          <summary>
            <svg width="15" height="15" viewBox="0 0 24 24">
              <circle cx="12" cy="12" r="9" fill="none" stroke="#475467" strokeWidth="1.6" />
              <path d="M12 7v5l3 2" stroke="#475467" strokeWidth="1.6" fill="none" strokeLinecap="round" />
            </svg>
            <span>{s.how}</span>
          </summary>
          <div className="tracenote">{s.docsRetrieved(run.trace?.documents_retrieved ?? 0)}</div>
          <div className="steps">
            {(run.execution_plan ?? []).map((step) => (
              <div className="step" key={step.name}>
                <div className={"dot" + (step.status === "skipped" ? " skip" : "")}>
                  {step.status === "skipped" ? (
                    <svg width="10" height="10" viewBox="0 0 24 24">
                      <line x1="6" y1="12" x2="18" y2="12" stroke="#94a3b8" strokeWidth="3" strokeLinecap="round" />
                    </svg>
                  ) : (
                    <svg width="10" height="10" viewBox="0 0 24 24">
                      <path d="M5 12l4 4 10-11" stroke="#16a34a" strokeWidth="3" fill="none" strokeLinecap="round" strokeLinejoin="round" />
                    </svg>
                  )}
                </div>
                <div className="nm">{step.name}</div>
                <div className="du">{step.status}</div>
              </div>
            ))}
          </div>
        </details>
      </section>
    </div>
  );
}

function Kpi({ label, value, caption }: { label: string; value: string; caption?: string }) {
  return (
    <div className="kpi">
      <div className="kl">{label}</div>
      <div className="kv">{value}</div>
      {caption && <div className="kc">{caption}</div>}
    </div>
  );
}

function Source({ r, fallback }: { r: DocumentSearchResult; fallback: string }) {
  const m = r.metadata || {};
  const title = String(m.title || m.source || fallback);
  const doc = r.document || "";
  const snippet = doc.slice(0, 150).trim() + (doc.length > 150 ? "…" : "");
  const tags = [m.department, m.document_type].filter(Boolean).map(String);
  return (
    <div className="src">
      <div className="fic">
        <DocIcon />
      </div>
      <div>
        <div className="st">{title}</div>
        <div className="ss">{snippet}</div>
        {tags.length > 0 && (
          <div className="tags">
            {tags.map((t) => (
              <span className="tag" key={t}>
                {t}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
