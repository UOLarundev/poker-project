import type { GameOrOver, GameView, HandHistoryEntry, LegalAction, MetricsSummary } from "./types";

// Relative paths only — the Vite dev server proxies /api to the backend
// (see vite.config.ts), and in production the same FastAPI process serves
// both the API and this built frontend from one origin. Never a hardcoded
// host here, in either environment.

async function getJson<T>(url: string): Promise<T> {
  const res = await fetch(url);
  if (!res.ok) {
    const detail = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(detail.detail ?? `Request failed: ${res.status}`);
  }
  return res.json() as Promise<T>;
}

async function postJson<T>(url: string, body: unknown): Promise<T> {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(detail.detail ?? `Request failed: ${res.status}`);
  }
  return res.json() as Promise<T>;
}

export function createGame(username: string): Promise<GameView> {
  return postJson<GameView>("/api/games", { username });
}

export function getGame(gameId: string): Promise<GameView> {
  return getJson<GameView>(`/api/games/${gameId}`);
}

export function getHandHistory(username: string): Promise<HandHistoryEntry[]> {
  return getJson<HandHistoryEntry[]>(`/api/players/${encodeURIComponent(username)}/hands`);
}

export function submitAction(
  handId: string,
  actionType: LegalAction["type"],
  amount?: number,
): Promise<GameView> {
  return postJson<GameView>(`/api/hands/${handId}/actions`, {
    action_id: crypto.randomUUID(),
    action_type: actionType,
    amount: amount ?? null,
  });
}

export function nextHand(handId: string): Promise<GameOrOver> {
  return postJson<GameOrOver>(`/api/hands/${handId}/next`, {
    action_id: crypto.randomUUID(),
  });
}

export function getMetricsSummary(): Promise<MetricsSummary> {
  return getJson<MetricsSummary>("/api/metrics/summary");
}
