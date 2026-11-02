import { Fragment, useCallback, useEffect, useState } from "react";
import { api } from "../api.js";
import "./LogsPage.css";

const ACTION = { register: "Registered", login: "Signed in", logout: "Signed out", run_stage: "Ran" };
const STAGE = {
  lexical: "Lexical", syntax: "Syntax", semantic: "Semantic",
  icg: "Intermediate code", run: "Output", full: "All stages",
};

const when = (iso) =>
  new Date(iso.endsWith("Z") || iso.includes("+") ? iso : iso + "Z").toLocaleString([], {
    dateStyle: "medium",
    timeStyle: "medium",
  });

const firstLine = (text) => (text ? text.split("\n").find((l) => l.trim()) ?? "" : "");

export default function LogsPage({ user }) {
  const isAdmin = user.role === "admin";
  const [everyone, setEveryone] = useState(false);
  const [rows, setRows] = useState(null);
  const [error, setError] = useState("");
  const [openId, setOpenId] = useState(null);

  const load = useCallback(async () => {
    setError("");
    try {
      setRows(await api.logs(everyone));
    } catch (err) {
      setError(err.message);
    }
  }, [everyone]);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <div className="logs">
      <header className="logs__head">
        <div>
          <h1>Activity log</h1>
          <p>Who did what, and on which program.</p>
        </div>
        <div className="logs__tools">
          {isAdmin && (
            <div className="seg" role="group" aria-label="Whose activity">
              <button aria-pressed={!everyone} onClick={() => setEveryone(false)}>Mine</button>
              <button aria-pressed={everyone} onClick={() => setEveryone(true)}>Everyone</button>
            </div>
          )}
          <button className="btn" onClick={load}>Refresh</button>
        </div>
      </header>

      <div className="logs__scroll">
        {error && <p className="notice notice--error" role="alert">{error}</p>}
        {!rows && !error && <p className="logs__empty">Loading…</p>}
        {rows && rows.length === 0 && <p className="logs__empty">No activity yet. Run a program and it will appear here.</p>}

        {rows && rows.length > 0 && (
          <table className="logs__table">
            <thead>
              <tr>
                <th>When</th>
                {everyone && <th>User</th>}
                <th>Action</th>
                <th>Result</th>
                <th>Program</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => {
                const expandable = Boolean(r.input_snapshot || r.detail);
                const open = openId === r.id;
                return (
                  <Fragment key={r.id}>
                    <tr className={expandable ? "is-expandable" : undefined} onClick={() => expandable && setOpenId(open ? null : r.id)}>
                      <td className="muted">{when(r.created_at)}</td>
                      {everyone && <td>{r.username}</td>}
                      <td>
                        {ACTION[r.action] ?? r.action}
                        {r.stage && <span className="logs__stage"> {STAGE[r.stage] ?? r.stage}</span>}
                      </td>
                      <td>
                        <span className={`pill pill--${r.status}`}>{r.status === "success" ? "Passed" : "Errors"}</span>
                      </td>
                      <td className="logs__program mono">
                        {expandable ? (
                          <button className="logs__expand" aria-expanded={open}>
                            {firstLine(r.input_snapshot) || r.detail}
                          </button>
                        ) : (
                          <span className="muted">—</span>
                        )}
                      </td>
                    </tr>
                    {open && (
                      <tr className="logs__detail">
                        <td colSpan={everyone ? 5 : 4}>
                          {r.detail && <p className="logs__note">{r.detail}</p>}
                          {r.input_snapshot && <pre>{r.input_snapshot}</pre>}
                        </td>
                      </tr>
                    )}
                  </Fragment>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
