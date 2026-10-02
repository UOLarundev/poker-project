import { useState } from "react";
import { createGame, getHandHistory, nextHand, submitAction } from "./api";
import { Card, FaceDownCard } from "./Card";
import { HandHistory } from "./HandHistory";
import { isGameOver, type ActionLogEntry, type GameOrOver, type HandHistoryEntry } from "./types";

// Phrasing mirrors interface/cli.py's own print statements for each action
// type — same narration the CLI player sees, rendered as list items here
// instead of printed lines.
function describeAction(entry: ActionLogEntry): string {
  switch (entry.action_type) {
    case "fold":
      return `${entry.actor_id} folds`;
    case "check":
      return `${entry.actor_id} checks`;
    case "call":
      return `${entry.actor_id} calls`;
    case "raise":
      return `${entry.actor_id} raises to $${entry.amount}`;
    case "all_in":
      return `${entry.actor_id} goes ALL-IN!`;
    default:
      return `${entry.actor_id}: ${entry.action_type}`;
  }
}

export default function App() {
  const [username, setUsername] = useState("");
  const [view, setView] = useState<GameOrOver | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [raiseTo, setRaiseTo] = useState("");
  const [history, setHistory] = useState<HandHistoryEntry[] | null>(null);

  async function run(fn: () => Promise<GameOrOver>) {
    setBusy(true);
    setError(null);
    try {
      setView(await fn());
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  function startGame() {
    if (!username.trim()) return;
    run(() => createGame(username.trim()));
  }

  async function openHistory() {
    setError(null);
    try {
      setHistory(await getHandHistory(username.trim()));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }

  if (history !== null) {
    return (
      <div className="screen">
        <h1>Hand History</h1>
        <HandHistory entries={history} />
        <button onClick={() => setHistory(null)}>Back</button>
      </div>
    );
  }

  if (!view) {
    return (
      <div className="screen">
        <h1>Poker</h1>
        <input
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && startGame()}
          placeholder="Your name"
        />
        <button onClick={startGame} disabled={busy}>
          New Game
        </button>
        {error && <p className="error">{error}</p>}
      </div>
    );
  }

  if (isGameOver(view)) {
    return (
      <div className="screen">
        <h1>Game Over</h1>
        <p>{view.winner ? `${view.winner} wins!` : "No one left with chips."}</p>
        <ul className="stacks">
          {Object.entries(view.final_stacks).map(([pid, stack]) => (
            <li key={pid}>
              {pid}: ${stack}
            </li>
          ))}
        </ul>
        <button onClick={startGame} disabled={busy}>
          Play Again
        </button>
        <button onClick={openHistory}>Hand History</button>
      </div>
    );
  }

  const hero = view.players.find((p) => p.player_id === view.viewer_id);

  return (
    <div className="screen">
      <div className="table-header">
        <span>{view.street}</span>
        <span>Pot: ${view.pot_total}</span>
        <button className="history-link" onClick={openHistory}>
          Hand History
        </button>
      </div>

      <div className="board">
        {view.board_cards.map((c) => (
          <Card key={c} code={c} />
        ))}
      </div>

      <ul className="seats">
        {view.players.map((p) => (
          <li key={p.player_id} className={p.player_id === view.to_act ? "seat seat-active" : "seat"}>
            <div className="seat-name">
              {p.player_id}
              {p.is_folded && " (folded)"}
              {p.is_all_in && " (all-in)"}
            </div>
            <div className="seat-stack">${p.stack}</div>
            <div className="seat-cards">
              {p.hole_cards
                ? p.hole_cards.map((c) => <Card key={c} code={c} />)
                : !p.is_folded && (
                    <>
                      <FaceDownCard />
                      <FaceDownCard />
                    </>
                  )}
            </div>
          </li>
        ))}
      </ul>

      {view.winners && (
        <p className="winners">
          {Object.entries(view.winners)
            .map(([pid, amt]) => `${pid} wins $${amt}`)
            .join(", ")}
        </p>
      )}

      {view.action_log.length > 0 && (
        <ul className="action-log">
          {view.action_log.map((entry, i) => (
            <li key={i}>{describeAction(entry)}</li>
          ))}
        </ul>
      )}

      {view.is_hand_over ? (
        <button onClick={() => run(() => nextHand(view.hand_id))} disabled={busy}>
          Next Hand
        </button>
      ) : view.is_your_turn ? (
        <div className="actions">
          {view.legal_actions.map((a) => {
            if (a.type === "raise") {
              return (
                <span key="raise" className="raise-control">
                  <input
                    type="number"
                    min={a.min ?? undefined}
                    max={a.max ?? undefined}
                    value={raiseTo}
                    onChange={(e) => setRaiseTo(e.target.value)}
                    placeholder={`${a.min}-${a.max}`}
                  />
                  <button
                    disabled={busy || !raiseTo}
                    onClick={() => run(() => submitAction(view.hand_id, "raise", Number(raiseTo)))}
                  >
                    Raise
                  </button>
                </span>
              );
            }
            const label =
              a.type === "call" || a.type === "all_in" ? `${a.type} $${a.amount}` : a.type;
            return (
              <button
                key={a.type}
                disabled={busy}
                onClick={() => run(() => submitAction(view.hand_id, a.type))}
              >
                {label}
              </button>
            );
          })}
        </div>
      ) : (
        <p>Waiting for {view.to_act}...</p>
      )}

      {hero && <p className="your-stack">Your stack: ${hero.stack}</p>}
      {error && <p className="error">{error}</p>}
    </div>
  );
}
