import { useState } from "react";
import { I18N, type Lang } from "./i18n";
import {
  runAgent,
  searchDocuments,
  getDemoKey,
  setDemoKey,
  type AgentRunResponse,
  type DocumentSearchResult,
} from "./api";
import { Header, EmptyState, Results } from "./components";

interface Filters {
  region: string;
  channel: string;
  segment: string;
}

export default function App() {
  const [lang, setLang] = useState<Lang>(
    (localStorage.getItem("sl_lang") as Lang) || "en",
  );
  const s = I18N[lang];

  const [input, setInput] = useState("");
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [run, setRun] = useState<AgentRunResponse | null>(null);
  const [sources, setSources] = useState<DocumentSearchResult[]>([]);
  const [refineOpen, setRefineOpen] = useState(false);
  const [filters, setFilters] = useState<Filters>({
    region: "",
    channel: "",
    segment: "",
  });

  function changeLang(next: Lang) {
    setLang(next);
    localStorage.setItem("sl_lang", next);
  }

  function editKey() {
    const value = window.prompt(s.key_prompt, getDemoKey());
    if (value === null) return;
    setDemoKey(value);
  }

  async function submit(text?: string) {
    const q = (text ?? input).trim();
    if (!q || loading) return;
    setInput(q);
    setQuestion(q);
    setLoading(true);
    setError("");
    setRun(null);
    try {
      const [runResult, docs] = await Promise.all([
        runAgent(q, {
          region: filters.region.trim() || null,
          channel: filters.channel.trim() || null,
          segment: filters.segment.trim() || null,
        }),
        searchDocuments(q),
      ]);
      setRun(runResult);
      setSources(docs);
    } catch (err) {
      setError(err instanceof Error ? err.message : s.err_generic);
    } finally {
      setLoading(false);
    }
  }

  const showEmpty = !loading && !run && !error;

  return (
    <>
      <Header lang={lang} s={s} onLang={changeLang} onKey={editKey} />

      <main>
        {showEmpty && <EmptyState s={s} onPick={(q) => submit(q)} />}

        {loading && (
          <div className="loading">
            <div className="spinner" />
            <span>{s.loading}</span>
          </div>
        )}

        {error && !loading && <div className="errbox">{error}</div>}

        {run && !loading && (
          <Results
            s={s}
            lang={lang}
            question={question}
            run={run}
            sources={sources}
            onFollow={(q) => submit(q)}
          />
        )}
      </main>

      <div className="askwrap">
        {refineOpen && (
          <div className="refine">
            <label>
              <span>{s.region}</span>
              <input
                placeholder="east"
                value={filters.region}
                onChange={(e) => setFilters({ ...filters, region: e.target.value })}
              />
            </label>
            <label>
              <span>{s.channel}</span>
              <input
                placeholder="online"
                value={filters.channel}
                onChange={(e) => setFilters({ ...filters, channel: e.target.value })}
              />
            </label>
            <label>
              <span>{s.segment}</span>
              <input
                placeholder="enterprise"
                value={filters.segment}
                onChange={(e) => setFilters({ ...filters, segment: e.target.value })}
              />
            </label>
          </div>
        )}
        <div className="askinner">
          <div className="ask">
            <button
              className={"fbtn" + (refineOpen ? " on" : "")}
              title="Refine"
              onClick={() => setRefineOpen((v) => !v)}
            >
              <svg width="19" height="19" viewBox="0 0 24 24">
                <path d="M4 6h16M7 12h10M10 18h4" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" />
              </svg>
            </button>
            <textarea
              rows={1}
              placeholder={s.ask_placeholder}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  submit();
                }
              }}
            />
            <button className="send" disabled={loading} onClick={() => submit()}>
              <svg width="20" height="20" viewBox="0 0 24 24">
                <path d="M4 12l16-8-6 16-3-6-7-2Z" fill="#fff" />
              </svg>
            </button>
          </div>
        </div>
      </div>
    </>
  );
}
