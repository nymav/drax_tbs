const BASE = (import.meta.env.VITE_API_URL || "/api").replace(/\/$/, "");
let workspaceKey = "";
export function setWorkspaceKey(value) {
  workspaceKey = value;
}
export function apiUrl(path) {
  return BASE + path;
}
export async function request(
  path,
  { body, signal, method = "GET", raw = false } = {},
) {
  const headers = {};
  if (workspaceKey) headers["X-DRAX-Key"] = workspaceKey;
  const form = body instanceof FormData;
  if (body && !form) headers["Content-Type"] = "application/json";
  let response;
  try {
    response = await fetch(apiUrl(path), {
      method,
      headers,
      body: body ? (form ? body : JSON.stringify(body)) : undefined,
      signal,
    });
  } catch (e) {
    if (e.name === "AbortError") throw e;
    throw new Error("Cannot reach DRAX. Start the backend and retry.");
  }
  if (!response.ok) {
    let data;
    try {
      data = await response.json();
    } catch {}
    throw new Error(
      typeof data?.detail === "string"
        ? data.detail
        : `Request failed (${response.status}).`,
    );
  }
  if (raw) return response.blob();
  return response.status === 204 ? null : response.json();
}
