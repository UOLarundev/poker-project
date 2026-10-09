import type { MetricsSummary, RouteStats } from "./types";

function formatMs(ms: number | null): string {
  if (ms === null) return "—";
  return ms >= 1000 ? `${(ms / 1000).toFixed(2)}s` : `${ms.toFixed(0)}ms`;
}

function RouteRow({ stats }: { stats: RouteStats }) {
  return (
    <tr>
      <td className="health-route">
        {stats.method} {stats.route}
      </td>
      <td>{stats.count}</td>
      <td>{formatMs(stats.p50_ms)}</td>
      <td>{formatMs(stats.p95_ms)}</td>
      <td>{formatMs(stats.p99_ms)}</td>
    </tr>
  );
}

export function HealthPanel({ summary }: { summary: MetricsSummary }) {
  if (summary.overall.count === 0) {
    return <p>No requests recorded yet.</p>;
  }
  return (
    <div className="health-panel">
      <p className="health-overall">
        {summary.overall.count} requests &middot; p50 {formatMs(summary.overall.p50_ms)}{" "}
        &middot; p95 {formatMs(summary.overall.p95_ms)} &middot; p99{" "}
        {formatMs(summary.overall.p99_ms)}
      </p>
      <table className="health-table">
        <thead>
          <tr>
            <th>Route</th>
            <th>n</th>
            <th>p50</th>
            <th>p95</th>
            <th>p99</th>
          </tr>
        </thead>
        <tbody>
          {summary.by_route.map((r) => (
            <RouteRow key={`${r.method} ${r.route}`} stats={r} />
          ))}
        </tbody>
      </table>
    </div>
  );
}
