import "./results.css";

const KIND_CLASS = (token) => {
  if (token.kind === "EOF") return "tok--eof";
  switch (token.type) {
    case "KEYWORD": return "tok--keyword";
    case "OPERATOR": return "tok--operator";
    case "NUMBER": return "tok--number";
    case "STRING": return "tok--string";
    default: return "tok--identifier";
  }
};

export default function TokenTable({ tokens }) {
  return (
    <table className="grid">
      <thead>
        <tr>
          <th className="num">#</th>
          <th>Position</th>
          <th>Type</th>
          <th>Kind</th>
          <th>Lexeme</th>
        </tr>
      </thead>
      <tbody>
        {tokens.map((t, i) => (
          <tr key={i}>
            <td className="num muted">{i + 1}</td>
            <td className="muted mono">
              {t.line}:{t.col}
            </td>
            <td>{t.type}</td>
            <td className="mono">{t.kind}</td>
            <td className={`mono ${KIND_CLASS(t)}`}>{t.kind === "EOF" ? "end of input" : t.lexeme}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
