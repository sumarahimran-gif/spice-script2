import ErrorList from "./ErrorList.jsx";
import TokenTable from "./TokenTable.jsx";
import ParseTree from "./ParseTree.jsx";
import SymbolTable from "./SymbolTable.jsx";
import TacView from "./TacView.jsx";
import OutputView from "./OutputView.jsx";
import "./StagePanel.css";

const plural = (n, word) => `${n} ${word}${n === 1 ? "" : "s"}`;

// One line that sums up what the stage produced.
function summary(id, d) {
  switch (id) {
    case "lexical": return plural(d.token_count ?? d.tokens.length, "token");
    case "syntax": return d.ast ? plural(d.node_count, "tree node") : null;
    case "semantic": return plural(d.symbol_table.length, "variable");
    case "icg": return plural(d.instruction_count ?? d.instructions.length, "instruction");
    case "run": return plural(d.steps ?? 0, "step") + " executed";
    default: return null;
  }
}

function Body({ id, data }) {
  switch (id) {
    case "lexical": return <TokenTable tokens={data.tokens} />;
    case "syntax": return data.ast ? <ParseTree ast={data.ast} /> : null;
    case "semantic": return <SymbolTable symbols={data.symbol_table} />;
    case "icg": return <TacView instructions={data.instructions} />;
    case "run": return <OutputView output={data.output} ok={data.ok} />;
    default: return null;
  }
}

export default function StagePanel({ stage, entry, stale, busy, apiError, onRerun, onGoTo }) {
  const data = entry?.data;
  const skipped = data?.status === "skipped";
  const blocked = Boolean(data?.blocked_by);
  const errors = data?.errors ?? [];
  const line = data && !skipped && !blocked ? summary(stage.id, data) : null;

  return (
    <div className="stage">
      <header className="stage__head">
        <div>
          <h2>{stage.label}</h2>
          <p>{stage.blurb}</p>
        </div>
        <button className="btn" onClick={onRerun} disabled={busy}>
          {busy ? "Running…" : entry ? "Run again" : "Run"}
        </button>
      </header>

      <div className="stage__body">
        {apiError && <p className="notice notice--error" role="alert">{apiError}</p>}
        {stale && entry && (
          <p className="notice">The code changed after this ran. Run it again to refresh the result.</p>
        )}

        {!entry && !busy && <p className="empty-note">Not run yet. Press Run, or Run all to go through every stage.</p>}
        {!entry && busy && <p className="empty-note">Running…</p>}

        {skipped && <p className="empty-note">Skipped, because an earlier stage found errors.</p>}

        {blocked && (
          <p className="notice notice--blocked">
            This stage could not start. Fix the {data.blocked_by} errors first:
          </p>
        )}

        {data && !skipped && (
          <>
            <ErrorList errors={errors} onGoTo={onGoTo} />
            {!blocked && (
              <>
                {line && <p className="stage__summary">{line}</p>}
                <Body id={stage.id} data={data} />
              </>
            )}
          </>
        )}
      </div>
    </div>
  );
}
