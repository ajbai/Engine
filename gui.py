import chess
import pygame
import threading
import os
from coach import Coach
from engine import ChessEngine
from evaluator import evaluate

BOARD_SIZE  = 600
SQ          = BOARD_SIZE // 8
PANEL_W     = 360
WIN_W       = BOARD_SIZE + PANEL_W
WIN_H       = BOARD_SIZE
FPS         = 60

C_LIGHT       = (240, 217, 181)
C_DARK        = (181, 136,  99)
C_SELECT      = ( 20, 160, 160, 180)
C_LEGAL       = ( 20, 160, 160, 80)
C_BEST_FROM   = (255, 220,  50, 190)
C_BEST_TO     = ( 60, 200,  90, 210)
C_THREAT_ATK  = (220,  60,  60, 170)
C_THREAT_VIC  = (220, 120,  40, 170)
C_BLUNDER     = (220,  50,  50, 160)
C_MISTAKE     = (220, 140,  30, 160)
C_INACCURACY  = (200, 200,  50, 130)
C_PANEL       = ( 22,  22,  32)
C_PANEL_HDR   = ( 38,  38,  55)
C_WHITE       = (230, 230, 230)
C_DIM         = (150, 150, 165)
C_GREEN       = ( 70, 210, 110)
C_RED         = (220,  70,  70)
C_YELLOW      = (230, 200,  50)
C_ORANGE      = (220, 140,  40)
C_BLUE        = ( 80, 160, 230)
C_THINKING    = (255, 180,  50)

PIECE_LETTER = {
    chess.PAWN: "P", chess.KNIGHT: "N", chess.BISHOP: "B",
    chess.ROOK: "R", chess.QUEEN:  "Q", chess.KING:   "K",
}
PIECE_NAME = {
    chess.PAWN: "pawn", chess.KNIGHT: "knight", chess.BISHOP: "bishop",
    chess.ROOK: "rook", chess.QUEEN:  "queen",  chess.KING:   "king",
}

def _font(size, bold=False):
    for name in ["Arial", "DejaVuSans", "FreeSans", "Helvetica"]:
        f = pygame.font.match_font(name, bold=bold)
        if f:
            return pygame.font.Font(f, size)
    return pygame.font.SysFont(None, size)

def _load_pieces(pieces_dir):
    cp = {chess.WHITE: "w", chess.BLACK: "b"}
    size = SQ - 8
    imgs = {}
    for color in (chess.WHITE, chess.BLACK):
        for pt, letter in PIECE_LETTER.items():
            path = os.path.join(pieces_dir, f"{cp[color]}{letter}.png")
            if os.path.exists(path):
                try:
                    s = pygame.image.load(path).convert_alpha()
                    imgs[(pt, color)] = pygame.transform.smoothscale(s, (size, size))
                except Exception:
                    imgs[(pt, color)] = None
            else:
                imgs[(pt, color)] = None
    return imgs

def _wrap(text, font, max_w):
    words, lines, line = text.split(), [], []
    for word in words:
        if font.size(" ".join(line + [word]))[0] > max_w:
            if line:
                lines.append(" ".join(line))
            line = [word]
        else:
            line.append(word)
    if line:
        lines.append(" ".join(line))
    return lines


class ChessCoachApp:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIN_W, WIN_H))
        pygame.display.set_caption("Chess Coach")
        self.clock  = pygame.time.Clock()

        self.f_title  = _font(20, bold=True)
        self.f_med    = _font(16)
        self.f_sm     = _font(13)
        self.f_xs     = _font(11)
        self.f_piece  = _font(SQ - 24, bold=True)
        self.f_big    = _font(32, bold=True)

        candidates = [
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "pieces"),
            os.path.join(os.getcwd(), "pieces"),
        ]
        pieces_dir = next((p for p in candidates if os.path.isdir(p)), None)
        self._imgs = _load_pieces(pieces_dir) if pieces_dir else {}

        self.coach = Coach(depth=4)
        self.ai    = ChessEngine(depth=3)

        # AI or Human
        self.mode = None

        #HUD
        btn_w, btn_h = 280, 60
        cx = WIN_W // 2
        self._btn_vs_ai    = pygame.Rect(cx - btn_w // 2, 260, btn_w, btn_h)
        self._btn_vs_human = pygame.Rect(cx - btn_w // 2, 350, btn_w, btn_h)

        self._init_game()

    def _init_game(self):
        self.board        = chess.Board()
        self.sel          = None
        self.legal        = []
        self.overlay      = pygame.Surface((BOARD_SIZE, BOARD_SIZE), pygame.SRCALPHA)
        self.best_moves   = []
        self.threats      = []
        self.blunder_info = None
        self.sel_blunder  = None
        self.ai_thinking  = False
        self.move_history = []
        self.coach._cache.clear()

        if self.mode == "vs_ai":
            self.status_msg = "You play White. AI plays Black."
            pygame.display.set_caption("Chess Coach — vs AI")
        elif self.mode == "vs_human":
            self.status_msg = "White's turn."
            pygame.display.set_caption("Chess Coach — 2 Player")
        else:
            self.status_msg = ""

        self._btn_new  = pygame.Rect(BOARD_SIZE + 10, WIN_H - 50,  PANEL_W - 20, 36)
        self._btn_hint = pygame.Rect(BOARD_SIZE + 10, WIN_H - 95,  PANEL_W - 20, 36)
        self._btn_menu = pygame.Rect(BOARD_SIZE + 10, WIN_H - 140, PANEL_W - 20, 36)

        if self.mode:
            self._refresh_coach()

    #Main
    def run(self):
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    return
                if self.mode is None:
                    self._handle_menu(event)
                else:
                    self._handle(event)
            if self.mode is None:
                self._draw_menu()
            else:
                self._draw()
            self.clock.tick(FPS)

    #Menu
    def _handle_menu(self, event):
        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return
        x, y = event.pos
        if self._btn_vs_ai.collidepoint(x, y):
            self.mode = "vs_ai"
            self._init_game()
        elif self._btn_vs_human.collidepoint(x, y):
            self.mode = "vs_human"
            self._init_game()

    def _draw_menu(self):
        self.screen.fill(C_PANEL)
        t = self.f_big.render("♟ Chess Coach", True, C_WHITE)
        self.screen.blit(t, (WIN_W // 2 - t.get_width() // 2, 140))
        sub = self.f_med.render("Choose your game mode", True, C_DIM)
        self.screen.blit(sub, (WIN_W // 2 - sub.get_width() // 2, 200))

        for rect, label, sublabel, color in [
            (self._btn_vs_ai,    "vs AI",        "You play White, AI plays Black", (40, 90, 55)),
            (self._btn_vs_human, "2 Player",     "Play against a friend locally",  (50, 70, 120)),
        ]:
            pygame.draw.rect(self.screen, color, rect, border_radius=8)
            pygame.draw.rect(self.screen, C_DIM, rect, 1, border_radius=8)
            lbl = self.f_title.render(label, True, C_WHITE)
            self.screen.blit(lbl, (rect.centerx - lbl.get_width() // 2,
                                   rect.centery - lbl.get_height() // 2 - 6))
            sub = self.f_xs.render(sublabel, True, C_DIM)
            self.screen.blit(sub, (rect.centerx - sub.get_width() // 2,
                                   rect.centery + lbl.get_height() // 2 - 4))

        pygame.display.flip()

    def _handle(self, event):
        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return
        x, y = event.pos

        if self._btn_new.collidepoint(x, y):
            self._new_game()
            return
        if self._btn_hint.collidepoint(x, y):
            self._flash_hint()
            return
        if self._btn_menu.collidepoint(x, y):
            self.mode = None
            self._init_game()
            return

        if x >= BOARD_SIZE or self.ai_thinking:
            return

        #AI - only white
        #Human - both sides can click
        if self.mode == "vs_ai" and self.board.turn != chess.WHITE:
            return

        sq = chess.square(x // SQ, 7 - (y // SQ))
        self._click(sq)

    def _click(self, sq):
        if self.board.is_game_over():
            return

        if self.sel is not None:
            move = chess.Move(self.sel, sq)
            piece = self.board.piece_at(self.sel)
            #queen promotion
            promo_rank = 7 if self.board.turn == chess.WHITE else 0
            if piece and piece.piece_type == chess.PAWN and chess.square_rank(sq) == promo_rank:
                move = chess.Move(self.sel, sq, promotion=chess.QUEEN)

            if move in self.board.legal_moves:
                self._human_move(move)
                self.sel, self.legal, self.sel_blunder = None, [], None
                return

            if sq == self.sel:
                self.sel, self.legal, self.sel_blunder = None, [], None
                return

        piece = self.board.piece_at(sq)
        if piece and piece.color == self.board.turn:
            self.sel   = sq
            self.legal = [m.to_square for m in self.board.legal_moves if m.from_square == sq]
            self.sel_blunder = None
        else:
            self.sel, self.legal, self.sel_blunder = None, [], None

    def _human_move(self, move):
        check = self.coach.blunder_check(self.board, move)
        who   = "White" if self.board.turn == chess.WHITE else "Black"
        self.board.push(move)
        self.move_history.append((who[0], move, check))

        if check["level"] == "blunder":
            self.status_msg = f"⚠ {who}: Blunder! {check['message']}"
        elif check["level"] == "mistake":
            self.status_msg = f"⚠ {who}: Mistake. {check['message']}"
        elif check["level"] == "best":
            self.status_msg = f"✓ {who}: Best move!"
        else:
            self.status_msg = f"{who} moved."

        self.best_moves = []
        self.threats    = []

        if self.board.is_game_over():
            self._show_result()
            return

        if self.mode == "vs_ai":
            self.status_msg += " Waiting for AI..."
            self._ai_move()
        else:
            next_player = "White" if self.board.turn == chess.WHITE else "Black"
            self.status_msg += f" {next_player}'s turn."
            self.threats = self.coach.get_threats(self.board)
            self._refresh_coach()

    def _ai_move(self):
        self.ai_thinking = True

        def _worker():
            move = self.ai.best_move(self.board.copy())
            if move:
                self.board.push(move)
                self.move_history.append(("B", move, None))
            self.ai_thinking = False

            if self.board.is_game_over():
                self._show_result()
            else:
                self.status_msg = "Your turn! Check the coach panel."
                self.threats    = self.coach.get_threats(self.board)
                self._refresh_coach()

        threading.Thread(target=_worker, daemon=True).start()

    def _refresh_coach(self):
        def _worker():
            if self.board.turn == chess.WHITE and not self.board.is_game_over():
                self.best_moves = self.coach.get_best_moves(self.board, n=3)
        threading.Thread(target=_worker, daemon=True).start()

    def _show_result(self):
        if self.board.is_checkmate():
            if self.mode == "vs_ai":
                winner = "Black (AI)" if self.board.turn == chess.WHITE else "White (You!)"
            else:
                winner = "Black" if self.board.turn == chess.WHITE else "White"
            self.status_msg = f"Checkmate! {winner} wins!"
        elif self.board.is_stalemate():
            self.status_msg = "Stalemate — it's a draw."
        else:
            self.status_msg = "Game over."

    def _flash_hint(self):
        if self.best_moves:
            move, score = self.best_moves[0]
            n = PIECE_NAME.get(self.board.piece_at(move.from_square).piece_type, "Piece") if self.board.piece_at(move.from_square) else "Piece"
            self.status_msg = f"Hint: {n.capitalize()} to {chess.square_name(move.to_square)} ({score:+d}cp)"

    def _new_game(self):
        self._init_game()

    #Graphics
    def _draw(self):
        self.screen.fill(C_PANEL)
        self._draw_board()
        self._draw_overlay()
        self._draw_pieces()
        self._draw_panel()
        pygame.display.flip()

    def _draw_board(self):
        for rank in range(8):
            for file in range(8):
                col = C_LIGHT if (rank + file) % 2 == 0 else C_DARK
                pygame.draw.rect(self.screen, col,
                    pygame.Rect(file * SQ, (7 - rank) * SQ, SQ, SQ))
                if file == 0:
                    lbl = self.f_xs.render(str(rank + 1), True,
                        C_DARK if rank % 2 == 0 else C_LIGHT)
                    self.screen.blit(lbl, (2, (7 - rank) * SQ + 2))
                if rank == 0:
                    lbl = self.f_xs.render(chess.FILE_NAMES[file], True,
                        C_LIGHT if file % 2 == 0 else C_DARK)
                    self.screen.blit(lbl, (file * SQ + SQ - 10, BOARD_SIZE - 13))

    def _draw_overlay(self):
        self.overlay.fill((0, 0, 0, 0))

        def sq_rect(sq):
            return pygame.Rect(chess.square_file(sq) * SQ,
                               (7 - chess.square_rank(sq)) * SQ, SQ, SQ)

        def sq_center(sq):
            return (chess.square_file(sq) * SQ + SQ // 2,
                    (7 - chess.square_rank(sq)) * SQ + SQ // 2)

        #Highlights
        for t in self.threats:
            pygame.draw.rect(self.overlay, C_THREAT_ATK, sq_rect(t["attacker_sq"]))
            pygame.draw.rect(self.overlay, C_THREAT_VIC, sq_rect(t["victim_sq"]))
        if self.best_moves:
            bm, _ = self.best_moves[0]
            pygame.draw.rect(self.overlay, C_BEST_FROM, sq_rect(bm.from_square))
            pygame.draw.rect(self.overlay, C_BEST_TO,   sq_rect(bm.to_square))
            pygame.draw.line(self.overlay, (60, 200, 90, 220),
                sq_center(bm.from_square), sq_center(bm.to_square), 7)
            tx, ty = sq_center(bm.to_square)
            pygame.draw.circle(self.overlay, (60, 200, 90, 220), (tx, ty), 9)

        #Selected position
        if self.sel is not None:
            pygame.draw.rect(self.overlay, C_SELECT, sq_rect(self.sel))

        for tsq in self.legal:
            move = chess.Move(self.sel, tsq)
            if self.board.piece_at(self.sel) and \
               self.board.piece_at(self.sel).piece_type == chess.PAWN and \
               chess.square_rank(tsq) == 7:
                move = chess.Move(self.sel, tsq, promotion=chess.QUEEN)
            if move in self.board.legal_moves:
                check = self.coach.blunder_check(self.board, move)
                dot_col = {
                    "best":       (*C_GREEN[:3],   160),
                    "ok":         (*C_GREEN[:3],   100),
                    "inaccuracy": (*C_YELLOW[:3],  140),
                    "mistake":    (*C_ORANGE[:3],  160),
                    "blunder":    (*C_RED[:3],      180),
                }.get(check["level"], (*C_GREEN[:3], 100))
                cx, cy = sq_center(tsq)
                pygame.draw.circle(self.overlay, dot_col, (cx, cy), SQ // 6)

        self.screen.blit(self.overlay, (0, 0))

    def _draw_pieces(self):
        for sq in chess.SQUARES:
            piece = self.board.piece_at(sq)
            if not piece:
                continue
            f, r  = chess.square_file(sq), chess.square_rank(sq)
            cx    = f * SQ + SQ // 2
            cy    = (7 - r) * SQ + SQ // 2
            img   = self._imgs.get((piece.piece_type, piece.color))
            if img:
                self.screen.blit(img, (cx - img.get_width() // 2, cy - img.get_height() // 2))
            else:
                is_w   = piece.color == chess.WHITE
                fill   = (255, 255, 255) if is_w else (30, 30, 30)
                border = (50, 50, 50)    if is_w else (200, 200, 200)
                tc     = (30, 30, 30)    if is_w else (255, 255, 255)
                pygame.draw.circle(self.screen, border, (cx, cy), SQ // 2 - 3)
                pygame.draw.circle(self.screen, fill,   (cx, cy), SQ // 2 - 5)
                lbl = self.f_piece.render(PIECE_LETTER[piece.piece_type], True, tc)
                self.screen.blit(lbl, (cx - lbl.get_width() // 2, cy - lbl.get_height() // 2))

    def _draw_panel(self):
        px = BOARD_SIZE
        W  = PANEL_W
        y  = 0
        #Title
        pygame.draw.rect(self.screen, C_PANEL_HDR, pygame.Rect(px, 0, W, 48))
        self.screen.blit(self.f_title.render("♟ Chess Coach", True, C_WHITE), (px + 12, 13))

        y = 56
        status_col = C_RED if "⚠" in self.status_msg else \
                     C_GREEN if "✓" in self.status_msg else \
                     C_THINKING if self.ai_thinking else C_WHITE
        for ln in _wrap(self.status_msg, self.f_med, W - 20):
            self.screen.blit(self.f_med.render(ln, True, status_col), (px + 12, y))
            y += 22
        y += 6

        self._divider(y); y += 12

        #Advice
        self.screen.blit(self.f_med.render("Coach Suggestion", True, C_WHITE), (px + 12, y))
        y += 24

        if self.best_moves:
            for i, (move, score) in enumerate(self.best_moves[:3]):
                piece = self.board.piece_at(move.from_square)
                pname = PIECE_NAME.get(piece.piece_type, "?").capitalize() if piece else "?"
                label = ["★ BEST", "  2nd", "  3rd"][i]
                col   = [C_GREEN, C_WHITE, C_DIM][i]
                txt   = f"{label}  {pname} {chess.square_name(move.from_square)}→{chess.square_name(move.to_square)}  ({score:+d}cp)"
                self.screen.blit(self.f_sm.render(txt, True, col), (px + 12, y))
                y += 20
        elif self.ai_thinking:
            dots = "." * (int(pygame.time.get_ticks() / 400) % 4 + 1)
            self.screen.blit(self.f_sm.render(f"AI is thinking{dots}", True, C_THINKING), (px + 12, y))
            y += 20
        else:
            self.screen.blit(self.f_sm.render("Analyzing…", True, C_DIM), (px + 12, y))
            y += 20

        y += 6
        self._divider(y); y += 12

        self.screen.blit(self.f_med.render("Threat Radar", True, C_WHITE), (px + 12, y))
        y += 24

        if self.threats:
            for t in self.threats[:3]:
                aname = PIECE_NAME.get(t["attacker"].piece_type, "?")
                vname = PIECE_NAME.get(t["victim"].piece_type,   "?")
                vsq   = chess.square_name(t["victim_sq"])
                gain  = t["gain"]
                if gain > 0:
                    msg = f"⚠ {aname.capitalize()} threatens your {vname} on {vsq} (+{gain//100:.0f}pts)"
                    col = C_RED
                else:
                    msg = f"↗ {aname.capitalize()} attacks your {vname} on {vsq}"
                    col = C_ORANGE
                for ln in _wrap(msg, self.f_sm, W - 20):
                    self.screen.blit(self.f_sm.render(ln, True, col), (px + 12, y))
                    y += 18
        else:
            self.screen.blit(self.f_sm.render("No major threats detected.", True, C_DIM), (px + 12, y))
            y += 18

        y += 6
        self._divider(y); y += 12

        self.screen.blit(self.f_med.render("Move Dot Guide", True, C_WHITE), (px + 12, y))
        y += 22
        guide = [
            (C_GREEN,  "Best / good move"),
            (C_YELLOW, "Slight inaccuracy"),
            (C_ORANGE, "Mistake"),
            (C_RED,    "Blunder"),
        ]
        for color, label in guide:
            pygame.draw.circle(self.screen, color, (px + 20, y + 7), 6)
            self.screen.blit(self.f_xs.render(label, True, C_DIM), (px + 32, y + 1))
            y += 18

        y += 4
        self._divider(y); y += 10

        #Counter
        move_num = self.board.fullmove_number
        self.screen.blit(self.f_xs.render(
            f"Move {move_num}  |  {'White to move' if self.board.turn == chess.WHITE else 'Black to move'}",
            True, C_DIM), (px + 12, y))

        pygame.draw.rect(self.screen, (40, 80, 130), self._btn_hint, border_radius=5)
        hl = self.f_med.render("💡 Get Hint", True, C_WHITE)
        self.screen.blit(hl, (self._btn_hint.x + (self._btn_hint.width - hl.get_width()) // 2,
                               self._btn_hint.y + (self._btn_hint.height - hl.get_height()) // 2))

        pygame.draw.rect(self.screen, C_PANEL_HDR, self._btn_new, border_radius=5)
        nl = self.f_med.render("New Game", True, C_DIM)
        self.screen.blit(nl, (self._btn_new.x + (self._btn_new.width - nl.get_width()) // 2,
                               self._btn_new.y + (self._btn_new.height - nl.get_height()) // 2))

        pygame.draw.rect(self.screen, (50, 40, 60), self._btn_menu, border_radius=5)
        ml = self.f_med.render("⬅ Main Menu", True, C_DIM)
        self.screen.blit(ml, (self._btn_menu.x + (self._btn_menu.width - ml.get_width()) // 2,
                               self._btn_menu.y + (self._btn_menu.height - ml.get_height()) // 2))

    def _divider(self, y):
        pygame.draw.line(self.screen, C_PANEL_HDR,
            (BOARD_SIZE + 8, y), (BOARD_SIZE + PANEL_W - 8, y), 1)
