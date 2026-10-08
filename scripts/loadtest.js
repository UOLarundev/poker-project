// k6 baseline load test for the p95 latency depth point.
//
// Deliberately modest: this is a hobby-scale deployment, not a stress test.
// The point is a real statistical sample (hundreds of requests), not
// maximum throughput — same reasoning as why the indexing depth point
// needed real row volume rather than a handful of test rows.
//
// Each virtual user loops: create a game, then fold. Folding is used
// specifically because it's ALWAYS a legal action regardless of game
// state, making every iteration deterministic and comparable — and it's
// exactly the request type that can trigger multi-street bot resolution
// in a single call, which is the actual latency story this project has
// been measuring all along.
//
// Usage:
//   k6 run scripts/loadtest.js                              # defaults to localhost:8000
//   k6 run -e BASE_URL=https://poker-project.fly.dev scripts/loadtest.js

import http from "k6/http";
import { check, sleep } from "k6";

const BASE_URL = __ENV.BASE_URL || "http://localhost:8000";

export const options = {
  vus: 5,
  duration: "30s",
};

function uuidv4() {
  // Good enough for a unique client-generated id in a load test — doesn't
  // need to be cryptographically strong, just unique per request so the
  // idempotency constraint never collides between genuinely different folds.
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === "x" ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

export default function () {
  const username = `loadtest_${__VU}_${__ITER}`;

  const createRes = http.post(
    `${BASE_URL}/api/games`,
    JSON.stringify({ username }),
    { headers: { "Content-Type": "application/json" } }
  );
  check(createRes, { "create game: 201": (r) => r.status === 201 });
  if (createRes.status !== 201) {
    return;
  }
  const handId = createRes.json("hand_id");

  const foldRes = http.post(
    `${BASE_URL}/api/hands/${handId}/actions`,
    JSON.stringify({ action_id: uuidv4(), action_type: "fold" }),
    { headers: { "Content-Type": "application/json" } }
  );
  check(foldRes, { "fold: 201": (r) => r.status === 201 });

  // A small pause between iterations — generating load, not hammering a
  // free-tier instance with zero gaps between requests.
  sleep(1);
}
