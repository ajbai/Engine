import chess
from engine import ChessEngine
from evaluator import evaluate

BLUNDER_THRESHOLD  = 150  #could possibly be a costly mistake
MISTAKE_THRESHOLD  = 400  #is a costly mistake, avoid!

class Coach:
    def __init__(self, depth: int = 4):
        self.engine = ChessEngine(depth=depth)
        self._cache: dict[str, list] = {}

    def get_best_moves(self, board: chess.Board, n: int = 3) -> list[tuple[chess.Move, int]]:
        key = board.fen()
        if key not in self._cache:
            self._cache[key] = self.engine.top_moves(board, n=n)
        return self._cache[key]

    def blunder_check(self, board: chess.Board, move: chess.Move) -> dict:
        best = self.get_best_moves(board, n=1)
        if not best:
            return {"level": "ok", "message": "", "delta": 0}

        best_move, best_score = best[0]

        #Score move
        board.push(move)
        move_score = evaluate(board)
        board.pop()

        # lower score = worse position
        delta = best_score - move_score   #positive = bad move

        if move.uci() == best_move.uci():
            return {"level": "best", "message": "Best move!", "delta": 0}
        elif delta < 30:
            return {"level": "ok", "message": "Good move.", "delta": delta}
        elif delta < BLUNDER_THRESHOLD:
            return {"level": "inaccuracy", "message": f"Slight inaccuracy (−{delta}cp). Consider the suggestion.", "delta": delta}
        elif delta < MISTAKE_THRESHOLD:
            return {"level": "mistake", "message": f"Mistake! You lose ~{delta//100:.1f} pawns of advantage.", "delta": delta}
        else:
            return {"level": "blunder", "message": f"Blunder! This loses {delta//100:.1f} pawns. Check the arrow!", "delta": delta}

    def get_threats(self, board: chess.Board) -> list[dict]:
        threats = []
        if board.turn != chess.WHITE:
            return threats

        for sq in chess.SQUARES:
            piece = board.piece_at(sq)
            if piece is None or piece.color != chess.BLACK:
                continue

            attacks = board.attacks(sq)
            for target_sq in attacks:
                target = board.piece_at(target_sq)
                if target and target.color == chess.WHITE:
                    from evaluator import PIECE_VALUES
                    attacker_val = PIECE_VALUES.get(piece.piece_type, 0)
                    target_val   = PIECE_VALUES.get(target.piece_type, 0)
                    if target_val >= attacker_val - 50 or target.piece_type == chess.KING:
                        threats.append({
                            "attacker_sq":  sq,
                            "victim_sq":    target_sq,
                            "attacker":     piece,
                            "victim":       target,
                            "gain":         target_val - attacker_val,
                        })

        #Sort here
        threats.sort(key=lambda t: t["gain"], reverse=True)
        return threats[:4]   #capped at 4
