import { forwardRef, useImperativeHandle, useMemo, useRef } from "react";
import "./CodeEditor.css";

const BLOCK_OPENERS = /^\s*(taste|simmer|bland)\b/;

// How wide the highlighted span should be for an error that starts at `col`.
function spanLength(lineText, col) {
  const rest = lineText.slice(col - 1);
  if (!rest) return 1;
  const pattern = rest[0] === '"' ? /^"[^"]*"?/ : /^[A-Za-z0-9_.]+/;
  const m = rest.match(pattern);
  return m ? m[0].length : 1;
}

/**
 * A plain textarea with a line-number gutter and error markers. The textarea is
 * sized to its content and the whole editor scrolls as one, so the gutter and the
 * markers never drift out of line with the text.
 */
const CodeEditor = forwardRef(function CodeEditor({ value, onChange, errors, onRunAll }, ref) {
  const scrollRef = useRef(null);
  const areaRef = useRef(null);

  const lines = useMemo(() => value.split("\n"), [value]);
  const widest = useMemo(() => Math.max(20, ...lines.map((l) => l.length)), [lines]);

  const errorLines = useMemo(() => new Set(errors.map((e) => e.line)), [errors]);

  useImperativeHandle(ref, () => ({
    goTo(line, col = 1) {
      const ta = areaRef.current;
      if (!ta) return;
      const before = lines.slice(0, line - 1).reduce((n, l) => n + l.length + 1, 0);
      const start = before + Math.min(col - 1, (lines[line - 1] || "").length);
      const end = start + spanLength(lines[line - 1] || "", col);
      ta.focus();
      ta.setSelectionRange(start, end);
      const lh = ta.offsetHeight / lines.length;
      scrollRef.current.scrollTop = Math.max(0, (line - 3) * lh);
    },
  }));

  const handleKeyDown = (e) => {
    const ta = e.target;
    const { selectionStart: s, selectionEnd: end } = ta;

    if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
      e.preventDefault();
      onRunAll();
      return;
    }

    if (e.key === "Tab") {
      e.preventDefault();
      onChange(value.slice(0, s) + "  " + value.slice(end));
      requestAnimationFrame(() => ta.setSelectionRange(s + 2, s + 2));
      return;
    }

    // Keep the indentation of the current line, and indent one level after an opener.
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      const lineStart = value.lastIndexOf("\n", s - 1) + 1;
      const currentLine = value.slice(lineStart, s);
      const indent = currentLine.match(/^ */)[0] + (BLOCK_OPENERS.test(currentLine) ? "  " : "");
      const insert = "\n" + indent;
      onChange(value.slice(0, s) + insert + value.slice(end));
      requestAnimationFrame(() => ta.setSelectionRange(s + insert.length, s + insert.length));
    }
  };

  return (
    <div className="editor" ref={scrollRef}>
      <div className="editor__gutter" aria-hidden="true">
        {lines.map((_, i) => (
          <div key={i} className={errorLines.has(i + 1) ? "has-error" : undefined}>
            {i + 1}
          </div>
        ))}
      </div>

      <div className="editor__body" style={{ minWidth: `${widest + 6}ch` }}>
        <div className="editor__marks" aria-hidden="true">
          {errors.map((err, i) => (
            <div key={i} className="editor__mark" style={{ "--line": err.line - 1 }}>
              <span
                className="editor__squiggle"
                style={{
                  "--col": err.col - 1,
                  "--len": spanLength(lines[err.line - 1] || "", err.col),
                }}
              />
            </div>
          ))}
        </div>

        <textarea
          ref={areaRef}
          className="editor__input"
          style={{ "--rows": lines.length }}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={handleKeyDown}
          spellCheck={false}
          autoCapitalize="off"
          autoCorrect="off"
          wrap="off"
          aria-label="SpiceScript source code"
        />
      </div>
    </div>
  );
});

export default CodeEditor;
