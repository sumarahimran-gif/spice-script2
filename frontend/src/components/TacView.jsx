import "./results.css";

const PARTS = /(\$?[A-Za-z_][A-Za-z0-9_]*|\d+(?:\.\d+)?|"[^"]*"|==|[=+\-*/<>])/g;
const WORDS = new Set(["ifFalse", "goto", "print"]);

// Colour one line of three-address code.
function Line({ ins }) {
  if (ins.op === "label") return <span className="tac__label">{ins.text}</span>;
  const out = [];
  let last = 0;
  let key = 0;
  for (const m of ins.text.matchAll(PARTS)) {
    if (m.index > last) out.push(ins.text.slice(last, m.index));
    const t = m[0];
    let cls = "tok--identifier";
    if (WORDS.has(t)) cls = "tok--keyword";
    else if (t === ins.target) cls = "tac__label";
    else if (t.startsWith("$")) cls = "tac__temp";
    else if (/^\d/.test(t)) cls = "tok--number";
    else if (t.startsWith('"')) cls = "tok--string";
    else if (/^[=+\-*/<>]/.test(t)) cls = "tok--operator";
    out.push(
      <span key={key++} className={cls}>
        {t}
      </span>
    );
    last = m.index + t.length;
  }
  return <>{out}</>;
}

export default function TacView({ instructions }) {
  if (!instructions.length) return <p className="empty-note">There is no code to generate for an empty program.</p>;
  return (
    <ol className="tac" aria-label="Three-address code">
      {instructions.map((ins) => (
        <li key={ins.index} className={ins.op === "label" ? "tac__row tac__row--label" : "tac__row"}>
          <span className="tac__n">{ins.index}</span>
          <code className="tac__code">
            <Line ins={ins} />
          </code>
          <span className="tac__src">line {ins.line}</span>
        </li>
      ))}
    </ol>
  );
}
