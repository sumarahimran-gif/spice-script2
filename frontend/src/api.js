// All talking to the backend goes through this file.
// Empty means "same address as the page": Vite forwards /api to the backend (see vite.config.js).
const BASE = import.meta.env.VITE_API_URL ?? "";
const TOKEN_KEY = "spicescript.token";

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

export const getToken = () => localStorage.getItem(TOKEN_KEY);
export const setToken = (token) =>
  token ? localStorage.setItem(TOKEN_KEY, token) : localStorage.removeItem(TOKEN_KEY);

let onUnauthorized = () => {};
export const setUnauthorizedHandler = (fn) => {
  onUnauthorized = fn;
};

// FastAPI returns either {detail: "text"} or {detail: [{loc, msg}, ...]}.
function messageFrom(data) {
  if (!data || !data.detail) return null;
  if (typeof data.detail === "string") return data.detail;
  if (Array.isArray(data.detail)) {
    return data.detail
      .map((d) => {
        const field = String(d.loc?.at(-1) ?? "input");
        const msg = String(d.msg).replace(/^Value error, /, "");
        return field === "password" || field === "username"
          ? `${field[0].toUpperCase()}${field.slice(1)}: ${msg}`
          : msg;
      })
      .join(". ");
  }
  return null;
}

async function request(path, { method = "GET", body, auth = true } = {}) {
  const headers = {};
  if (body) headers["Content-Type"] = "application/json";
  const token = getToken();
  if (auth && token) headers.Authorization = `Bearer ${token}`;

  let res;
  try {
    res = await fetch(BASE + path, {
      method,
      headers,
      body: body ? JSON.stringify(body) : undefined,
    });
  } catch {
    throw new ApiError("Cannot reach the app server. Check that `npm run dev` is still running.", 0);
  }

  let data = null;
  try {
    data = await res.json();
  } catch {
    /* empty or non-JSON body */
  }

  if (!res.ok) {
    // An empty error reply from the dev server means it could not reach the backend.
    if (!data && res.status >= 500) {
      throw new ApiError(
        `The backend is not answering (status ${res.status}). Check that its window is still running, ` +
          "then try again.",
        res.status
      );
    }
    if (res.status === 401 && auth && token) onUnauthorized();
    throw new ApiError(messageFrom(data) || `Request failed (${res.status})`, res.status);
  }
  return data;
}

export const api = {
  register: (username, password) =>
    request("/api/auth/register", { method: "POST", body: { username, password }, auth: false }),
  login: (username, password) =>
    request("/api/auth/login", { method: "POST", body: { username, password }, auth: false }),
  logout: () => request("/api/auth/logout", { method: "POST" }),
  me: () => request("/api/auth/me"),
  grammar: () => request("/api/grammar", { auth: false }),
  run: (endpoint, source) => request(endpoint, { method: "POST", body: { source } }),
  logs: (all) => request(`/api/logs?limit=300${all ? "&all=true" : ""}`),
};
