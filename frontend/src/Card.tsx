// Web equivalent of interface/cli.py's format_card — same 2-char wire
// format ("AS", "TH"), same red/black suit convention, different rendering
// target (a styled <span>, not an ANSI escape code).

const SUIT_SYMBOL: Record<string, string> = { H: "♥", D: "♦", C: "♣", S: "♠" };
const RANK_DISPLAY: Record<string, string> = { T: "10" };

export function Card({ code }: { code: string }) {
  const rank = code[0];
  const suit = code[1];
  const red = suit === "H" || suit === "D";
  return (
    <span className={`card ${red ? "card-red" : "card-black"}`}>
      {(RANK_DISPLAY[rank] ?? rank) + SUIT_SYMBOL[suit]}
    </span>
  );
}

export function FaceDownCard() {
  return <span className="card card-back">🂠</span>;
}
