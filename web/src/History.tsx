import type { Lang, Strings } from "./i18n";
import type { HistoryItem } from "./api";

function relTime(ts: number, lang: Lang): string {
  return new Intl.DateTimeFormat(lang === "pt" ? "pt-BR" : "en-US", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(ts));
}

export default function History({
  s,
  lang,
  items,
  onOpen,
  onClear,
}: {
  s: Strings;
  lang: Lang;
  items: HistoryItem[];
  onOpen: (item: HistoryItem) => void;
  onClear: () => void;
}) {
  return (
    <div className="page">
      <div className="page-head">
        <h1>{s.hist_title}</h1>
        <p>{s.hist_sub}</p>
      </div>

      {items.length === 0 ? (
        <div className="panel muted">{s.hist_empty}</div>
      ) : (
        <>
          <div className="hist-actions">
            <button className="ghost" onClick={onClear}>
              {s.hist_clear}
            </button>
          </div>
          <div className="hist-list">
            {items.map((item) => {
              const answer =
                item.run.generated_response?.content || item.run.summary || "";
              return (
                <button
                  key={item.id}
                  className="hist-item"
                  onClick={() => onOpen(item)}
                >
                  <div className="hist-top">
                    <span className="hist-q">{item.question}</span>
                    <span className="hist-open">{s.hist_open} →</span>
                  </div>
                  <div className="hist-ans">{answer.slice(0, 160)}
                    {answer.length > 160 ? "…" : ""}</div>
                  <div className="hist-meta">{relTime(item.ts, lang)}</div>
                </button>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
}
