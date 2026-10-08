# Hand-history index

`GET /api/players/{username}/hands` — [api/services/history_service.py](../api/services/history_service.py),
migration [a24717ca8b64](../migrations/versions/a24717ca8b64_add_index_on_hands_player_id_started_at.py).

## The query

```sql
SELECT * FROM hands WHERE player_id = $1 ORDER BY started_at DESC LIMIT 20;
```

This is the real, load-bearing query behind the hand-history screen — not a
synthetic example invented for this doc.

## Seeding realistic volume

A small local table lies about whether an index matters: Postgres's planner
can reasonably choose a sequential scan over an index on a tiny table, since
the index lookup itself has overhead. Real evidence needs real volume.

[scripts/seed_hands.py](../scripts/seed_hands.py) generated **1,000 synthetic
players, 298,217 `hands` rows** (84MB) — run against local Postgres only,
never the live deployment. None of the seeded data is a *valid* poker hand
(random card codes, random outcomes); the query planner doesn't care about
game correctness, only row shape and volume.

## Before: no index

`EXPLAIN (ANALYZE, BUFFERS)`, same query, same player, run three times
(first run cold, next two warm):

```
Limit (actual time=26.625..34.634 rows=20 loops=1)
  Buffers: shared hit=9328
  -> Gather Merge (actual time=26.621..34.626 rows=20 loops=1)
       Workers Planned: 2  Workers Launched: 2
       -> Sort (actual time=19.204..19.207 rows=9 loops=3)
            Sort Key: started_at DESC
            Sort Method: top-N heapsort  Memory: 34kB
            -> Parallel Seq Scan on hands (actual time=12.192..18.989 rows=55 loops=3)
                 Filter: (player_id = '9913f2ca-...'::uuid)
                 Rows Removed by Filter: 99350
Execution Time: 34.788 ms
```

**`Parallel Seq Scan`, removing 99,350 non-matching rows per worker** —
effectively the entire table, every single call, regardless of how many
hands this one player actually has. A separate **`Sort`** node orders the
matches afterward. Warm execution time stabilized at **~34.7–34.9ms**,
touching **9,328 buffer pages**.

## After: `CREATE INDEX idx_hands_player_started ON hands (player_id, started_at DESC)`

Same query, same player, same warm-up pattern:

```
Limit (actual time=0.040..0.062 rows=20 loops=1)
  Buffers: shared hit=22
  -> Index Scan using idx_hands_player_started on hands (actual time=0.038..0.058 rows=20 loops=1)
       Index Cond: (player_id = '9913f2ca-...'::uuid)
Execution Time: 0.111 ms
```

`Parallel Seq Scan` + `Sort` collapses into a single `Index Scan` — **no
separate sort step at all**, because the index already stores this player's
rows in `started_at DESC` order. Warm execution time: **~0.11–0.12ms**.
Buffer pages touched: **22**, down from 9,328.

| | Before | After | Change |
|---|---|---|---|
| Execution time (warm) | ~34.8ms | ~0.12ms | **~290x** |
| Buffer pages touched | 9,328 | 22 | **~424x** |
| Query plan | `Parallel Seq Scan` + `Sort` | `Index Scan` | sort eliminated entirely |

## Composite + `DESC` specifically — proved by mutation, not asserted

It would be easy to claim "a `player_id` index would do basically the same
thing." Tested it directly instead: dropped the composite index, created
`idx_hands_player_only ON hands (player_id)` alone, ran the identical query:

```
Limit (actual time=0.335..0.340 rows=20 loops=1)
  -> Sort (actual time=0.333..0.335 rows=20 loops=1)
       Sort Key: started_at DESC
       -> Bitmap Heap Scan on hands (actual time=0.102..0.144 rows=166 loops=1)
            -> Bitmap Index Scan on idx_hands_player_only (actual time=0.064..0.064 rows=166 loops=1)
Execution Time: 0.416 ms
```

The `Sort` node comes back. Still far faster than no index at all (166
candidate rows to sort instead of ~298k), but it's a measurably different,
strictly worse plan than the composite index's single `Index Scan` — proving
the column order and `DESC` direction are themselves load-bearing design
choices, not incidental. Restored the real composite index afterward and
re-ran to confirm: `Index Scan`, no `Sort`, 0.150ms — back to the "after"
result above.

## Known limitations

- **Measured on local Postgres, not the live Neon deployment.** The
  *relative* improvement (sequential scan → index scan, sort eliminated) is
  what this evidence is about; absolute millisecond figures would differ on
  different hardware. Re-running this against Neon directly was deliberately
  not done — no reason to load 300k synthetic rows into the real production
  database for a demonstration already proven locally.
- **Seeded data has an artificial, uniform distribution** (100–500 hands per
  player, evenly randomized timestamps across the last 180 days) — real
  usage would be far more skewed (most players with very few hands, a long
  tail of none at all). The index's advantage only grows with real-world
  skew, not shrinks, so this is a conservative test, not an optimistic one.
