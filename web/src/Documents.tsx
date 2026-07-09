import { useRef, useState } from "react";
import type { Strings } from "./i18n";
import {
  ingestFile,
  ingestText,
  searchDocuments,
  type DocumentSearchResult,
} from "./api";
import { Source } from "./components";

export default function Documents({ s }: { s: Strings }) {
  // add-document state
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState("");
  const [source, setSource] = useState("");
  const [content, setContent] = useState("");
  const [dept, setDept] = useState("");
  const [docType, setDocType] = useState("");
  const [adding, setAdding] = useState(false);
  const [addMsg, setAddMsg] = useState("");
  const [addErr, setAddErr] = useState("");
  const fileInput = useRef<HTMLInputElement>(null);

  // search state
  const [query, setQuery] = useState("");
  const [searching, setSearching] = useState(false);
  const [results, setResults] = useState<DocumentSearchResult[] | null>(null);
  const [searchErr, setSearchErr] = useState("");

  function metadata(): Record<string, string> {
    const m: Record<string, string> = {};
    if (dept.trim()) m.department = dept.trim();
    if (docType.trim()) m.document_type = docType.trim();
    return m;
  }

  async function addDocument() {
    if (adding) return;
    setAddMsg("");
    setAddErr("");
    setAdding(true);
    try {
      const result = file
        ? await ingestFile(file, metadata())
        : await ingestText({
            title: title.trim(),
            source: source.trim(),
            content: content.trim(),
            metadata: metadata(),
          });
      setAddMsg(`${result.title}: ${s.indexed(result.chunks_created)}`);
      setFile(null);
      setTitle("");
      setSource("");
      setContent("");
      if (fileInput.current) fileInput.current.value = "";
    } catch (err) {
      setAddErr(err instanceof Error ? err.message : s.err_generic);
    } finally {
      setAdding(false);
    }
  }

  async function runSearch() {
    const q = query.trim();
    if (!q || searching) return;
    setSearching(true);
    setSearchErr("");
    setResults(null);
    try {
      setResults(await searchDocuments(q, 8));
    } catch (err) {
      setSearchErr(err instanceof Error ? err.message : s.err_generic);
    } finally {
      setSearching(false);
    }
  }

  const canAdd = file != null || (title.trim() && source.trim() && content.trim());

  return (
    <div className="page">
      <div className="page-head">
        <h1>{s.docs_title}</h1>
        <p>{s.docs_sub}</p>
      </div>

      <div className="panel">
        <div className="seclabel">{s.add_heading}</div>
        <div className="filerow">
          <label className="filebtn">
            <input
              ref={fileInput}
              type="file"
              accept=".txt,.md,.markdown"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            />
            {s.choose_file}
          </label>
          <span className="filehint">{file ? file.name : s.upload_hint}</span>
        </div>

        <div className="or">{s.or_paste}</div>

        <div className="fields">
          <label className="field">
            <span>{s.f_title}</span>
            <input value={title} onChange={(e) => setTitle(e.target.value)} />
          </label>
          <label className="field">
            <span>{s.f_source}</span>
            <input value={source} onChange={(e) => setSource(e.target.value)} />
          </label>
          <label className="field">
            <span>{s.f_dept}</span>
            <input value={dept} onChange={(e) => setDept(e.target.value)} placeholder="growth" />
          </label>
          <label className="field">
            <span>{s.f_type}</span>
            <input value={docType} onChange={(e) => setDocType(e.target.value)} placeholder="policy" />
          </label>
        </div>
        <label className="field">
          <span>{s.f_content}</span>
          <textarea
            className="content-area"
            value={content}
            onChange={(e) => setContent(e.target.value)}
            disabled={file != null}
          />
        </label>

        <div className="panel-actions">
          <button className="primary" disabled={!canAdd || adding} onClick={addDocument}>
            {adding ? s.adding : s.add_btn}
          </button>
          {addMsg && <span className="okmsg">{addMsg}</span>}
          {addErr && <span className="errmsg">{addErr}</span>}
        </div>
      </div>

      <div className="panel">
        <div className="seclabel">{s.search_heading}</div>
        <div className="searchline">
          <input
            className="searchinput"
            placeholder={s.doc_search_ph}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && runSearch()}
          />
          <button className="primary" disabled={searching} onClick={runSearch}>
            {searching ? s.searching : s.search_btn}
          </button>
        </div>
        {searchErr && <div className="errmsg" style={{ marginTop: 12 }}>{searchErr}</div>}
        {results != null && results.length === 0 && !searchErr && (
          <div className="muted" style={{ marginTop: 12 }}>{s.no_results}</div>
        )}
        {results != null && results.length > 0 && (
          <div className="sources" style={{ marginTop: 14 }}>
            {results.map((r) => (
              <Source key={r.chunk_id} r={r} fallback={s.document_excerpt} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
