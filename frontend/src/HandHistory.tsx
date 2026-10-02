import { Card } from "./Card";
import type { HandHistoryEntry } from "./types";

function formatWhen(iso: string): string {
  return new Date(iso).toLocaleString();
}

function HandRow({ entry }: { entry: HandHistoryEntry }) {
  const inProgress = entry.ended_at === null;
  return (
    <li className="history-row">
      <div className="history-row-header">
        <span>Hand #{entry.hand_number}</span>
        <span>{formatWhen(entry.started_at)}</span>
      </div>
      <div className="history-row-cards">
        {entry.hero_hole?.map((c) => <Card key={c} code={c} />)}
        {entry.board && entry.board.length > 0 && (
          <span className="history-board">
            {entry.board.map((c) => <Card key={c} code={c} />)}
          </span>
        )}
      </div>
      {inProgress ? (
        <p className="history-result">(in progress)</p>
      ) : (
        <p className={`history-result ${entry.hero_net !== null && entry.hero_net >= 0 ? "net-win" : "net-loss"}`}>
          {entry.hero_net !== null && entry.hero_net >= 0 ? "+" : ""}
          {entry.hero_net} &middot; pot ${entry.pot_total}
        </p>
      )}
    </li>
  );
}

export function HandHistory({ entries }: { entries: HandHistoryEntry[] }) {
  if (entries.length === 0) {
    return <p>No hands played yet.</p>;
  }
  return (
    <ul className="history-list">
      {entries.map((entry) => (
        <HandRow key={entry.hand_id} entry={entry} />
      ))}
    </ul>
  );
}
