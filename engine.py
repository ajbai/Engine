import chess
import time
from evaluator import evaluate, PIECE_VALUES

INF = float("inf")
DEFAULT_DEPTH = 4
MAX_THINK_SECS = 5.0

class ChessEngine:
    def __init__(self, depth: int = DEFAULT_DEPTH):
        self.depth = depth
        self.nodes_searched = 0
        self._start_time = 0.0

    def best_move(self, board: chess.Board) -> chess.Move | None:
        legal = list(board.legal_moves)
        if not legal:
            return None
        self.nodes_searched = 0
        self._start_time = time.time()
        best = None
        best_score = -INF if board.turn == chess.WHITE else INF
        ordered = self._order_moves(board, legal)
        for move in ordered:
            board.push(move)
            score = self._minimax(board, self.depth - 1, -INF, INF, board.turn == chess.WHITE)
            board.pop()
            if board.turn == chess.WHITE and score > best_score:
                best_score, best = score, move
            elif board.turn == chess.BLACK and score < best_score:
                best_score, best = score, move
        return best

    def top_moves(self, board: chess.Board, n: int = 3) -> list[tuple[chess.Move, int]]:
        legal = list(board.legal_moves)
        if not legal:
            return []
        self.nodes_searched = 0
        self._start_time = time.time()
        scored = []
        ordered = self._order_moves(board, legal)
        for move in ordered:
            board.push(move)
            score = self._minimax(board, self.depth - 1, -INF, INF, board.turn == chess.WHITE)
            board.pop()
            scored.append((move, score))
        reverse = board.turn == chess.WHITE
        scored.sort(key=lambda x: x[1], reverse=reverse)
        return scored[:n]

    def _minimax(self, board: chess.Board, depth: int, alpha: float, beta: float, maximizing: bool) -> float:
        self.nodes_searched += 1
        if time.time() - self._start_time > MAX_THINK_SECS:
            return evaluate(board)
        if depth == 0 or board.is_game_over():
            return evaluate(board)
        legal = list(board.legal_moves)
        ordered = self._order_moves(board, legal)
        if maximizing:
            value = -INF
            for move in ordered:
                board.push(move)
                value = max(value, self._minimax(board, depth - 1, alpha, beta, False))
                board.pop()
                alpha = max(alpha, value)
                if alpha >= beta:
                    break
            return value
        else:
            value = INF
            for move in ordered:
                board.push(move)
                value = min(value, self._minimax(board, depth - 1, alpha, beta, True))
                board.pop()
                beta = min(beta, value)
                if alpha >= beta:
                    break
            return value

    def _order_moves(self, board: chess.Board, moves: list[chess.Move]) -> list[chess.Move]:
        def score(move: chess.Move) -> int:
            s = 0
            if board.is_capture(move):
                victim = board.piece_at(move.to_square)
                attacker = board.piece_at(move.from_square)
                if victim and attacker:
                    s += 10 * PIECE_VALUES.get(victim.piece_type, 0) - PIECE_VALUES.get(attacker.piece_type, 0)
                else:
                    s += 500
            if move.promotion:
                s += 800
            board.push(move)
            if board.is_check():
                s += 50
            board.pop()
            return s
        return sorted(moves, key=score, reverse=True)
