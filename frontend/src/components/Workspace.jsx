import { useEffect, useRef, useState } from "react";
import { api } from "../api.js";
import { DEFAULT_SOURCE, RUN_ALL_ENDPOINT, STAGES } from "../stages.js";
import CodeEditor from "./CodeEditor.jsx";
import GrammarPanel from "./GrammarPanel.jsx";
import StageBar from "./StageBar.jsx";
import StagePanel from "./StagePanel.jsx";
import "./Workspace.css";

const plural = (n, word) => `${n} ${word}${n === 1 ? "" : "s"}`;

// Badge state for one stage: what happened, and whether the code has changed since.
function statusOf(id, entry, source, busy) {
  if (busy === id || busy === "all") return { state: "running", text: "Running" };
  if (!entry) return { state: "idle", text: "Not run" };
  const d = entry.data;
  const stale = entry.source !== source;
  if (d.status === "skipped") return { state: "skipped", text: "Skipped", stale };
  if (d.ok) return { state: "ok", text: "Passed", stale };
  if (d.blocked_by) return { state: "blocked", text: "Blocked", stale };
  return { state: "error", text: plural(d.errors.length, "error"), stale };
}

export default function Workspace({ hidden }) {
  const [source, setSource] = useState(DEFAULT_SOURCE);
  const [results, setResults] = useState({}); // stage id -> { data, source }
  const [active, setActive] = useState("lexical");
  const [busy, setBusy] = useState(null); // a stage id, "all", or null
  const [apiError, setApiError] = useState("");
  const [grammar, setGrammar] = useState(null);
  const [grammarError, setGrammarError] = useState("");
  const [grammarOpen, setGrammarOpen] = useState(() => window.matchMedia("(min-width: 861px)").matches);
  const editor = useRef(null);

  useEffect(() => {
    api.grammar().then(setGrammar).catch((e) => setGrammarError(e.message));
  }, []);

  const call = async (fn) => {
    setApiError("");
    try {
      await fn();
    } catch (err) {
      setApiError(err.message);
    } finally {
      setBusy(null);
    }
  };

  const runStage = (id, { force = false } = {}) => {
    setActive(id);
    const cached = results[id];
    if (!force && cached && cached.source === source && cached.data.status !== "skipped") return;
    setBusy(id);
    const stage = STAGES.find((s) => s.id === id);
    return call(async () => {
      const data = await api.run(stage.endpoint, source);
      setResults((r) => ({ ...r, [id]: { data, source } }));
    });
  };

  const runAll = () => {
    if (busy) return;
    setBusy("all");
    return call(async () => {
      const full = await api.run(RUN_ALL_ENDPOINT, source);
      const next = {};
      for (const s of STAGES) next[s.id] = { data: full.stages[s.id], source };
      setResults(next);
      setActive(full.stopped_at ?? "run");
    });
  };

  const statuses = Object.fromEntries(STAGES.map((s) => [s.id, statusOf(s.id, results[s.id], source, busy)]));
  const activeStage = STAGES.find((s) => s.id === active);
  const entry = results[active];
  const fresh = entry && entry.source === source && entry.data.status !== "skipped";
  const markers = fresh ? entry.data.errors : [];

  return (
    <div className="bench" hidden={hidden}>
      <StageBar statuses={statuses} active={active} busy={busy} onPick={runStage} onRunAll={runAll} />

      <div className="bench__body" data-grammar={grammarOpen ? "open" : "closed"}>
        <GrammarPanel
          open={grammarOpen}
          onToggle={() => setGrammarOpen(!grammarOpen)}
          grammar={grammar}
          error={grammarError}
          onLoadSample={setSource}
        />

        <section className="pane" aria-label="Code">
          <header className="pane__head">
            <h2>Program</h2>
            <span className="pane__hint">Ctrl + Enter runs every stage</span>
            <button className="btn btn--quiet pane__clear" onClick={() => setSource("")} disabled={!source}>
              Clear
            </button>
          </header>
          <CodeEditor ref={editor} value={source} onChange={setSource} errors={markers} onRunAll={runAll} />
        </section>

        <section className="pane pane--result" aria-label="Stage result" aria-live="polite">
          <StagePanel
            stage={activeStage}
            entry={entry}
            stale={entry && entry.source !== source}
            busy={busy === active || busy === "all"}
            apiError={apiError}
            onRerun={() => runStage(active, { force: true })}
            onGoTo={(line, col) => editor.current?.goTo(line, col)}
          />
        </section>
      </div>
    </div>
  );
}
