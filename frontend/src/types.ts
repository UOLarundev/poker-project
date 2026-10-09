// Mirrors api/schemas.py exactly. Keeping these hand-written rather than
// codegen'd from the OpenAPI schema for now — small enough surface that a
// generator would be more ceremony than the two structs it's replacing.

export interface LegalAction {
  type: "fold" | "check" | "call" | "raise" | "all_in";
  amount: number | null;
  min: number | null;
  max: number | null;
}

export interface ActionLogEntry {
  actor_id: string;
  action_type: "fold" | "check" | "call" | "raise" | "all_in" | "next_hand";
  amount: number | null;
}

export interface PlayerSeat {
  player_id: string;
  stack: number;
  chips_in_street: number;
  chips_in_hand: number;
  is_folded: boolean;
  is_all_in: boolean;
  hole_cards: string[] | null;
}

export interface GameView {
  game_id: string;
  hand_id: string;
  viewer_id: string;
  street: string;
  is_hand_over: boolean;
  dealer_button_index: number;
  sb_amount: number;
  bb_amount: number;
  board_cards: string[];
  pot_total: number;
  current_bet: number;
  to_act: string | null;
  is_your_turn: boolean;
  legal_actions: LegalAction[];
  players: PlayerSeat[];
  winners: Record<string, number> | null;
  action_log: ActionLogEntry[];
  your_equity: number | null;
}

export interface GameOverView {
  game_id: string;
  game_over: true;
  winner: string | null;
  final_stacks: Record<string, number>;
}

export interface HandHistoryEntry {
  hand_id: string;
  game_id: string;
  hand_number: number;
  started_at: string;
  ended_at: string | null;
  board: string[] | null;
  hero_hole: string[] | null;
  winners: Record<string, number> | null;
  pot_total: number | null;
  hero_net: number | null;
}

export interface PercentileStats {
  count: number;
  p50_ms: number | null;
  p95_ms: number | null;
  p99_ms: number | null;
}

export interface RouteStats extends PercentileStats {
  route: string;
  method: string;
}

export interface MetricsSummary {
  overall: PercentileStats;
  by_route: RouteStats[];
}

export type GameOrOver = GameView | GameOverView;

export function isGameOver(view: GameOrOver): view is GameOverView {
  return "game_over" in view;
}
