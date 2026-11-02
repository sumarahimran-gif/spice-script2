import "./results.css";

export default function SymbolTable({ symbols }) {
  if (!symbols.length) return <p className="empty-note">No variables are declared in this program.</p>;
  return (
    <table className="grid">
      <thead>
        <tr>
          <th>Name</th>
          <th>Type</th>
          <th>Declared</th>
          <th className="num">Reads</th>
          <th className="num">Writes</th>
        </tr>
      </thead>
      <tbody>
        {symbols.map((s) => (
          <tr key={s.name}>
            <td className="mono">{s.name}</td>
            <td>
              <span className={`chip chip--${s.type}`}>{s.type}</span>
            </td>
            <td className="muted mono">
              line {s.line}, col {s.col}
            </td>
            <td className="num mono">{s.reads}</td>
            <td className="num mono">{s.writes}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
