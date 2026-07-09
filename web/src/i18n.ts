export type Lang = "en" | "pt";

export interface Strings {
  tagline: string;
  nav_ask: string;
  nav_docs: string;
  nav_history: string;
  region: string;
  channel: string;
  segment: string;
  ask_placeholder: string;
  empty_title: string;
  empty_sub: string;
  loading: string;
  your_question: string;
  answer: string;
  answer_sub: string;
  controlled: string;
  sources: string;
  related: string;
  how: string;
  revenue: string;
  sales: string;
  customers: string;
  topmix: string;
  overall: string;
  err_generic: string;
  key_prompt: string;
  document_excerpt: string;
  docsRetrieved: (n: number) => string;
  examples: string[];
  follow: string[];
  // Documents page
  docs_title: string;
  docs_sub: string;
  add_heading: string;
  search_heading: string;
  upload_hint: string;
  choose_file: string;
  or_paste: string;
  f_title: string;
  f_source: string;
  f_content: string;
  f_dept: string;
  f_type: string;
  add_btn: string;
  adding: string;
  indexed: (n: number) => string;
  doc_search_ph: string;
  search_btn: string;
  searching: string;
  no_results: string;
  // History page
  hist_title: string;
  hist_sub: string;
  hist_empty: string;
  hist_clear: string;
  hist_open: string;
}

export const I18N: Record<Lang, Strings> = {
  en: {
    tagline: "Business data assistant",
    nav_ask: "Ask",
    nav_docs: "Documents",
    nav_history: "History",
    region: "Region",
    channel: "Channel",
    segment: "Segment",
    ask_placeholder: "Ask about sales, customers or policies…",
    empty_title: "Ask about your sales and policies",
    empty_sub:
      "Get a clear answer grounded in your business data and documents.",
    loading: "Analyzing your data…",
    your_question: "Your question",
    answer: "Answer",
    answer_sub: "Grounded in your sales data and policy documents",
    controlled: "controlled",
    sources: "Sources consulted",
    related: "Related questions",
    how: "How this was produced",
    revenue: "Revenue",
    sales: "Sales",
    customers: "Unique customers",
    topmix: "Top region · channel",
    overall: "across all sales",
    err_generic: "Something went wrong. Please try again.",
    key_prompt: "Enter demo API key (leave blank to clear):",
    document_excerpt: "Document excerpt",
    docsRetrieved: (n) =>
      `${n} document${n === 1 ? "" : "s"} retrieved · deterministic 5-step plan`,
    examples: [
      "How are online sales doing in the enterprise segment?",
      "What do our policies say about discount approval?",
      "Which regions and channels lead revenue?",
    ],
    follow: [
      "Which deals exceed the 15% discount rule?",
      "Compare east vs west online",
      "Who approves enterprise contracts?",
    ],
    docs_title: "Documents",
    docs_sub: "Add documents to the knowledge base and search across them.",
    add_heading: "Add a document",
    search_heading: "Search documents",
    upload_hint: "Upload a .txt or .md file",
    choose_file: "Choose file",
    or_paste: "or paste text",
    f_title: "Title",
    f_source: "Source",
    f_content: "Content",
    f_dept: "Department",
    f_type: "Type",
    add_btn: "Add document",
    adding: "Adding…",
    indexed: (n) => `Indexed — ${n} chunk${n === 1 ? "" : "s"} created`,
    doc_search_ph: "Search your documents…",
    search_btn: "Search",
    searching: "Searching…",
    no_results: "No matching passages found.",
    hist_title: "History",
    hist_sub: "Your recent questions on this device.",
    hist_empty: "You haven't asked anything yet.",
    hist_clear: "Clear history",
    hist_open: "Open",
  },
  pt: {
    tagline: "Assistente de dados comerciais",
    nav_ask: "Perguntar",
    nav_docs: "Documentos",
    nav_history: "Histórico",
    region: "Região",
    channel: "Canal",
    segment: "Segmento",
    ask_placeholder: "Pergunte sobre vendas, clientes ou políticas…",
    empty_title: "Pergunte sobre suas vendas e políticas",
    empty_sub:
      "Receba uma resposta clara baseada nos seus dados e documentos.",
    loading: "Analisando seus dados…",
    your_question: "Sua pergunta",
    answer: "Resposta",
    answer_sub: "Baseada nos seus dados de vendas e documentos de política",
    controlled: "controlada",
    sources: "Fontes consultadas",
    related: "Perguntas relacionadas",
    how: "Como isso foi produzido",
    revenue: "Receita",
    sales: "Vendas",
    customers: "Clientes únicos",
    topmix: "Top região · canal",
    overall: "em todas as vendas",
    err_generic: "Algo deu errado. Tente novamente.",
    key_prompt: "Informe a API key da demo (deixe em branco para remover):",
    document_excerpt: "Trecho do documento",
    docsRetrieved: (n) =>
      `${n} documento${n === 1 ? "" : "s"} recuperado${n === 1 ? "" : "s"} · plano determinístico de 5 passos`,
    examples: [
      "Como estão as vendas online no segmento enterprise?",
      "O que as políticas dizem sobre aprovação de desconto?",
      "Quais regiões e canais lideram a receita?",
    ],
    follow: [
      "Quais negócios passam da regra de 15% de desconto?",
      "Comparar leste x oeste no online",
      "Quem aprova contratos enterprise?",
    ],
    docs_title: "Documentos",
    docs_sub: "Adicione documentos à base de conhecimento e pesquise neles.",
    add_heading: "Adicionar um documento",
    search_heading: "Pesquisar documentos",
    upload_hint: "Envie um arquivo .txt ou .md",
    choose_file: "Escolher arquivo",
    or_paste: "ou cole o texto",
    f_title: "Título",
    f_source: "Origem",
    f_content: "Conteúdo",
    f_dept: "Departamento",
    f_type: "Tipo",
    add_btn: "Adicionar documento",
    adding: "Adicionando…",
    indexed: (n) => `Indexado — ${n} trecho${n === 1 ? "" : "s"} criado${n === 1 ? "" : "s"}`,
    doc_search_ph: "Pesquise seus documentos…",
    search_btn: "Pesquisar",
    searching: "Pesquisando…",
    no_results: "Nenhum trecho correspondente encontrado.",
    hist_title: "Histórico",
    hist_sub: "Suas perguntas recentes neste dispositivo.",
    hist_empty: "Você ainda não perguntou nada.",
    hist_clear: "Limpar histórico",
    hist_open: "Abrir",
  },
};
