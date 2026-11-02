import "./results.css";

export default function OutputView({ output, ok }) {
  if (!output.length) {
    return <p className="empty-note">{ok ? "The program ran and printed nothing." : "The program printed nothing before it stopped."}</p>;
  }
  return (
    <pre className="console" aria-label="Program output">
      {output.map((line, i) => (
        <div key={i}>{line}</div>
      ))}
    </pre>
  );
}
