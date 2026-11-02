import "./GrammarPanel.css";

// Colour the EBNF so rules, quoted words and punctuation read differently.
const EBNF_PARTS = /(\(\*[\s\S]*?\*\))|("[^"\n]*"|'[^'\n]*')|([=|;{}[\]()])|([A-Za-z_]+)/g;

function EbnfText({ text }) {
  const out = [];
  let last = 0;
  let key = 0;
  for (const m of text.matchAll(EBNF_PARTS)) {
    if (m.index > last) out.push(text.slice(last, m.index));
    const cls = m[1] ? "ebnf--comment" : m[2] ? "ebnf--terminal" : m[3] ? "ebnf--punct" : "ebnf--rule";
    out.push(
      <span key={key++} className={cls}>
        {m[0]}
      </span>
    );
    last = m.index + m[0].length;
  }
  out.push(text.slice(last));
  return <>{out}</>;
}

export default function GrammarPanel({ open, onToggle, grammar, error, onLoadSample }) {
  if (!open) {
    return (
      <aside className="grammar grammar--closed">
        <button className="grammar__rail" onClick={onToggle} aria-expanded="false" aria-label="Open grammar panel">
          <span>Grammar</span>
        </button>
      </aside>
    );
  }

  return (
    <aside className="grammar" aria-label="Language grammar">
      <header className="grammar__head">
        <h2>Grammar</h2>
        <button className="btn btn--quiet grammar__close" onClick={onToggle} aria-expanded="true">
          Hide
        </button>
      </header>

      <div className="grammar__scroll">
        {error && <p className="grammar__error">Could not load the grammar: {error}</p>}
        {!grammar && !error && <p className="grammar__muted">Loading…</p>}

        {grammar && (
          <>
            <section>
              <h3>Samples</h3>
              <p className="grammar__muted">Load a program into the editor.</p>
              <ul className="grammar__samples">
                {grammar.samples.map((s) => (
                  <li key={s.name}>
                    <button onClick={() => onLoadSample(s.code)}>{s.name}</button>
                  </li>
                ))}
              </ul>
            </section>

            <section>
              <h3>Rules (EBNF)</h3>
              <pre className="grammar__ebnf">
                <code>
                  <EbnfText text={grammar.ebnf} />
                </code>
              </pre>
            </section>

            <section>
              <h3>Keywords</h3>
              <table className="grammar__table">
                <tbody>
                  {grammar.keywords.map((k) => (
                    <tr key={k.word}>
                      <th className="tok--keyword mono">{k.word}</th>
                      <td>{k.meaning}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </section>

            <section>
              <h3>Operators</h3>
              <table className="grammar__table">
                <tbody>
                  {grammar.operators.map((o) => (
                    <tr key={o.word}>
                      <th className="tok--operator mono">{o.word}</th>
                      <td className="mono grammar__symbol">{o.symbol}</td>
                      <td>{o.meaning}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </section>

            <section>
              <h3>Basics</h3>
              <ul className="grammar__basics">
                <li>Names start with a letter or underscore.</li>
                <li>Numbers can be whole or decimal.</li>
                <li>Strings sit in double quotes on one line.</li>
                <li>Comments start with # and run to the end of the line.</li>
                <li>Keywords are lowercase and case-sensitive.</li>
              </ul>
            </section>
          </>
        )}
      </div>
    </aside>
  );
}
