import { STAGES } from "../stages.js";
import "./StageBar.css";

export default function StageBar({ statuses, active, busy, onPick, onRunAll }) {
  return (
    <div className="pipeline">
      <ol className="pipeline__track" aria-label="Compiler stages">
        {STAGES.map((stage, i) => {
          const st = statuses[stage.id];
          const next = STAGES[i + 1] && statuses[STAGES[i + 1].id];
          return (
            <li key={stage.id} className="station">
              <button
                className="station__btn"
                data-state={st.state}
                data-stale={st.stale || undefined}
                aria-pressed={active === stage.id}
                onClick={() => onPick(stage.id)}
                title={st.stale ? "The code changed since this ran" : stage.blurb}
              >
                <span className="station__num">{i + 1}</span>
                <span className="station__text">
                  <span className="station__label">{stage.label}</span>
                  <span className="station__badge">
                    <i className="station__dot" aria-hidden="true" />
                    {st.text}
                    {st.stale && <span className="station__stale"> · edited</span>}
                  </span>
                </span>
              </button>
              {next && <span className="station__link" data-state={st.stale ? "idle" : st.state} aria-hidden="true" />}
            </li>
          );
        })}
      </ol>

      <button className="btn btn--primary pipeline__all" onClick={onRunAll} disabled={busy !== null}>
        {busy === "all" ? "Running…" : "Run all"}
      </button>
    </div>
  );
}
