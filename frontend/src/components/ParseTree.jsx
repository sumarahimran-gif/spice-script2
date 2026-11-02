import { useState } from "react";
import "./ParseTree.css";

// What each node shows next to its type, and which children it has (in reading order).
function label(n) {
  switch (n.type) {
    case "Declare":
    case "Assign":
    case "Var":
      return { text: n.name, cls: "tok--identifier" };
    case "BinOp":
      return { text: n.op, cls: "tok--operator" };
    case "Number":
      return { text: String(n.value), cls: "tok--number" };
    case "String":
      return { text: `"${n.value}"`, cls: "tok--string" };
    default:
      return { text: "", cls: "" };
  }
}

// Each child is {role, node} or {role, group: [nodes]} (a list of statements).
function childrenOf(n) {
  switch (n.type) {
    case "Program":
      return [{ role: "", group: n.body, flat: true }];
    case "Declare":
    case "Assign":
    case "Print":
      return [{ role: "value", node: n.value }];
    case "If":
      return [
        { role: "condition", node: n.cond },
        { role: "then", group: n.then },
        ...(n.else ? [{ role: "else", group: n.else }] : []),
      ];
    case "While":
      return [
        { role: "condition", node: n.cond },
        { role: "body", group: n.body },
      ];
    case "BinOp":
      return [
        { role: "left", node: n.left },
        { role: "right", node: n.right },
      ];
    default:
      return [];
  }
}

function Children({ kids, open }) {
  return (
    <ul>
      {kids.map((k, i) =>
        k.node ? (
          <TreeNode key={i} node={k.node} role={k.role} open={open} />
        ) : k.flat ? (
          k.group.map((child, j) => <TreeNode key={`${i}-${j}`} node={child} open={open} />)
        ) : (
          <li key={i}>
            <div className="tree__row">
              <span className="tree__group">{k.role}</span>
              <span className="tree__count">{k.group.length} statement{k.group.length === 1 ? "" : "s"}</span>
            </div>
            <Children kids={k.group.map((g) => ({ node: g, role: "" }))} open={open} />
          </li>
        )
      )}
    </ul>
  );
}

function TreeNode({ node, role, open }) {
  const kids = childrenOf(node);
  const [isOpen, setOpen] = useState(open);
  const { text, cls } = label(node);
  const expandable = kids.length > 0;

  return (
    <li>
      <div className="tree__row">
        {expandable ? (
          <button
            className="tree__toggle"
            aria-expanded={isOpen}
            aria-label={`${isOpen ? "Collapse" : "Expand"} ${node.type}`}
            onClick={() => setOpen(!isOpen)}
          >
            {isOpen ? "−" : "+"}
          </button>
        ) : (
          <span className="tree__leaf" aria-hidden="true" />
        )}
        {role && <span className="tree__role">{role}</span>}
        <span className="tree__type">{node.type}</span>
        {text && <span className={`mono ${cls}`}>{text}</span>}
        <span className="tree__pos">
          {node.line}:{node.col}
        </span>
      </div>
      {expandable && isOpen && <Children kids={kids} open={open} />}
    </li>
  );
}

export default function ParseTree({ ast }) {
  const [mode, setMode] = useState({ open: true, v: 0 });
  const set = (open) => setMode({ open, v: mode.v + 1 });
  return (
    <div className="tree">
      <div className="tree__tools">
        <button className="btn btn--quiet" onClick={() => set(true)}>Expand all</button>
        <button className="btn btn--quiet" onClick={() => set(false)}>Collapse all</button>
      </div>
      {/* Changing the key remounts the nodes so every one takes the new open state. */}
      <ul key={mode.v} className="tree__root">
        <TreeNode node={ast} open={mode.open} />
      </ul>
    </div>
  );
}
