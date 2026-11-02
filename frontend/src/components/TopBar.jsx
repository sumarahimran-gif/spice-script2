import "./TopBar.css";

const VIEWS = [
  { id: "workspace", label: "Workbench" },
  { id: "logs", label: "Activity log" },
];

export default function TopBar({ user, view, onView, onSignOut }) {
  return (
    <header className="topbar">
      <div className="topbar__brand">
        <span className="topbar__mark" aria-hidden="true" />
        <span className="topbar__name">SpiceScript</span>
        <span className="topbar__sub">compiler</span>
      </div>

      <nav className="topbar__nav" aria-label="Pages">
        {VIEWS.map((v) => (
          <button
            key={v.id}
            className="topbar__link"
            aria-current={view === v.id ? "page" : undefined}
            onClick={() => onView(v.id)}
          >
            {v.label}
          </button>
        ))}
      </nav>

      <div className="topbar__user">
        <span className="topbar__who">
          {user.username}
          {user.role === "admin" && <span className="topbar__role">admin</span>}
        </span>
        <button className="btn btn--quiet topbar__out" onClick={onSignOut}>
          Sign out
        </button>
      </div>
    </header>
  );
}
