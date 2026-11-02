import "./results.css";

export default function ErrorList({ errors, onGoTo }) {
  if (!errors.length) return null;
  return (
    <ul className="errors" aria-label="Errors">
      {errors.map((e, i) => (
        <li key={i}>
          <button className="errors__item" onClick={() => onGoTo(e.line, e.col)}>
            <span className="errors__where">
              Line {e.line}
              {e.col ? `, col ${e.col}` : ""}
            </span>
            <span className="errors__msg">{e.message}</span>
            {e.stage && <span className="errors__stage">{e.stage}</span>}
          </button>
        </li>
      ))}
    </ul>
  );
}
