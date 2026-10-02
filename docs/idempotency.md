# Idempotent action endpoint

`POST /api/hands/{hand_id}/actions` and `POST /api/hands/{hand_id}/next` —
[api/routes/actions.py](../api/routes/actions.py),
[api/services/action_service.py](../api/services/action_service.py).

## The problem

A client submitting a poker action over HTTP can retry: a timeout, a flaky
mobile connection, a double-tap. If a retried "raise to 50" were reapplied,
the player would be raised twice. The endpoint has to guarantee that the
*same* action, submitted more than once, only ever takes effect once — while
also guaranteeing that *different* actions arriving at the same time don't
corrupt each other's view of the game.

These are two separate guarantees, and this system uses two separate
mechanisms for them. Conflating them is the most common mistake here.

## Mechanism 1 — idempotency: `UNIQUE(hand_id, action_id)`

The client generates a UUID (`action_id`) for every action and sends it in
the request body. The `actions` table has:

```sql
UNIQUE (hand_id, action_id)
```

The endpoint always tries to `INSERT` the action row *first*, via
`db.flush()` (not `db.commit()`). If `(hand_id, action_id)` already exists,
Postgres raises a uniqueness violation before anything else has happened —
that's the signal that this is a retry, not a new action. The stored
`response_body` from the first attempt is read back and returned verbatim,
with `200 OK` and an `Idempotent-Replay: true` header (the first, real
application returns `201 Created`).

**The unique constraint alone only gives *at-most-once application*.**
Returning the *same response* on replay additionally requires persisting
the result — hence the `response_body` column. Without it, a retry would
correctly avoid re-applying the action, but the client would get back
whatever the *current* game state happens to be, not what actually
happened when their action was accepted — a subtle but real bug for any
client that inspects the response (e.g. "did my raise go through, and to
how much?").

**`flush()` vs `commit()` also has a second job.** If the action turns out
to be illegal (wrong turn, hand already over, invalid move for the engine),
the whole transaction is rolled back — which un-does the flush too. So a
*rejected* action does not burn its `action_id`: the client can legitimately
retry the same id with a corrected action. Proven by test
(`test_illegal_action_returns_400_and_does_not_burn_the_action_id`): a
rejected `raise` with no amount, followed by a `fold` under the *same*
`action_id`, succeeds.

## Mechanism 2 — concurrency: `SELECT ... FOR UPDATE`

Before touching anything else, the endpoint locks the game's row:

```python
game = db.execute(
    select(models.Game).where(models.Game.id == hand.game_id).with_for_update()
).scalar_one()
```

Any other request touching the same game now blocks at this line until the
first request commits or rolls back. This is what stops two *different*
actions from both reading the same state and stepping on each other's
update — a classic lost-update race that a unique constraint alone does
nothing to prevent (two different `action_id`s never collide on the
constraint, so without the lock both would apply independently against
stale data).

## The same mechanism, reused for a second, riskier operation

`POST /api/hands/{hand_id}/next` (start the next hand) goes through the
*exact same* `actions` table and `UNIQUE(hand_id, action_id)` constraint —
scoped by the hand that just finished, with `action_type="next_hand"` —
and the same `SELECT ... FOR UPDATE` lock. This isn't reuse for its own
sake: dealing a hand involves a real shuffle, so a naive retry here
wouldn't just double-apply an action, it would deal a *different* hand
than the first attempt. That makes idempotency more important here than
for an ordinary action, not less, and the existing mechanism already
covers it with no new infrastructure.

## Evidence

Two tests fire genuinely concurrent HTTP requests — a `ThreadPoolExecutor`
with 20 workers, not a sequential loop — against the same running app and
the same Postgres, then inspect what actually landed in the database.

**20 concurrent *identical* requests** (same `action_id`, testing Mechanism 1):

```
statuses: [200] x19, [201] x1
actions rows for this hand: 1
game.version: 1
```

**20 concurrent *different* requests** (20 distinct `action_id`s, all
otherwise-legal, testing Mechanism 2):

```
statuses: 201 x1, 409 x19, zero 5xx
actions rows for this hand: 1
game.version: 1
```

In both cases: exactly one durable state transition, exactly one persisted
action row, regardless of how many requests actually arrived at once.

### This isn't a tautological test — verified by mutation

Temporarily removed `.with_for_update()` from the lock query and re-ran the
"20 concurrent different actions" test three times: **failed all three**,
consistently at the `len(rows) == 1` assertion (multiple concurrent requests
successfully inserted their own rows once nothing serialized them). Restored
the lock, re-ran three times: **passed all three**. The test genuinely
exercises the mechanism it claims to.

## Known limitations, carried forward on purpose

- **Dealer rotation through a bust isn't precise seat-remapping.** If a
  player busts between hands, the next dealer index is computed as
  `(old_index + 1) % len(survivors)` against the *old* index and the
  *new*, shorter player list — fine for a rotating marker (the only
  consequence is which of the remaining players is next to act), but not
  how a physical table with fixed seats would handle it.
- **If the human busts but bots still have chips, that's still game over**
  for this API — even though, by the generic "fewer than 2 players left"
  rule alone, two players (both bots) technically remain. There's no one
  left for this particular `Game` resource to serve, so it's treated as
  finished either way. This is stricter than `interface/cli.py`'s own
  loop, which would happily let two bots play each other forever — that
  version just always has a human at the keyboard to stop it manually.
- **Bot decision logic is reused, not modified.** `api/services/bot_service.py`
  calls `interface.cli.choose_bot_action` in a loop; the actual bot AI is
  frozen Layer 2 code. The hand-to-hand transition logic (stack carryover,
  dealer rotation, busted-player removal) mirrors `interface/cli.py`'s
  `play_game()` loop, but isn't literally imported from it — that logic is
  inline in the CLI's loop, not a callable, so it's reproduced in
  `action_service.start_next_hand` rather than shared.
