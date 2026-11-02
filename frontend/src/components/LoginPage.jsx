import { useState } from "react";
import { api } from "../api.js";
import "./LoginPage.css";

export default function LoginPage({ onAuth, notice }) {
  const [mode, setMode] = useState("login"); // "login" | "register"
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const isRegister = mode === "register";

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      const call = isRegister ? api.register : api.login;
      onAuth(await call(username.trim(), password));
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const switchMode = () => {
    setMode(isRegister ? "login" : "register");
    setError("");
  };

  return (
    <div className="login">
      <section className="login__intro">
        <h1 className="login__title">SpiceScript compiler</h1>
        <p className="login__lede">
          Write a program in a cooking-themed language and see what every compiler stage does with
          it: tokens, parse tree, type checks, intermediate code and the final output.
        </p>
        <pre className="login__sample" aria-label="Sample SpiceScript program">
          <code>
            <span className="tok--keyword">mix</span> pinch <span className="tok--operator">into</span>{" "}
            <span className="tok--number">3</span>
            {"\n"}
            <span className="tok--keyword">simmer</span> pinch <span className="tok--operator">hotter</span>{" "}
            <span className="tok--number">0</span>
            {"\n  "}
            <span className="tok--keyword">serve</span> pinch
            {"\n  "}pinch <span className="tok--operator">into</span> pinch{" "}
            <span className="tok--operator">peel</span> <span className="tok--number">1</span>
            {"\n"}
            <span className="tok--keyword">done</span>
            {"\n"}
            <span className="tok--keyword">plate</span>
          </code>
        </pre>
      </section>

      <section className="login__panel">
        <form className="login__form" onSubmit={submit}>
          <h2>{isRegister ? "Create an account" : "Sign in"}</h2>

          {notice && !error && <p className="login__notice" role="status">{notice}</p>}

          <label className="field">
            <span>Username</span>
            <input
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoComplete="username"
              autoFocus
              required
              minLength={3}
              maxLength={32}
              pattern="[A-Za-z0-9_.\-]+"
              title="3 to 32 characters: letters, numbers, dot, dash or underscore"
            />
          </label>

          <label className="field">
            <span>Password</span>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete={isRegister ? "new-password" : "current-password"}
              required
              maxLength={128}
              {...(isRegister && {
                minLength: 8,
                pattern: "(?=.*[A-Za-z])(?=.*[0-9]).{8,}",
                title: "At least 8 characters, with a letter and a number",
              })}
            />
            {isRegister && <small>At least 8 characters, with a letter and a number.</small>}
          </label>

          {error && (
            <p className="login__error" role="alert">
              {error}
            </p>
          )}

          <button className="btn btn--primary login__submit" disabled={busy}>
            {busy ? "Please wait…" : isRegister ? "Create account" : "Sign in"}
          </button>

          <p className="login__switch">
            {isRegister ? "Already have an account?" : "New here?"}{" "}
            <button type="button" className="login__link" onClick={switchMode}>
              {isRegister ? "Sign in" : "Create an account"}
            </button>
          </p>
          {isRegister && (
            <p className="login__note">The first account created becomes the admin and can see every user's activity.</p>
          )}
        </form>
      </section>
    </div>
  );
}
