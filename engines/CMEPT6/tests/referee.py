"""Small independent standard-chess rules referee for CMEPT6 match testing.

Board indexing: a1=0, h8=63. Never calls CMEPT6 for validation.
Standard chess only (not Chess960). Written for this project, MIT licensed.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Iterator

FILES = 'abcdefgh'
KNIGHT = ((1, 2), (2, 1), (-1, 2), (-2, 1), (1, -2), (2, -1), (-1, -2), (-2, -1))
KING = ((df, dr) for df in range(-1, 2) for dr in range(-1, 2) if df or dr)
KING = tuple(KING)
BISHOP = ((1, 1), (1, -1), (-1, 1), (-1, -1))
ROOK = ((1, 0), (-1, 0), (0, 1), (0, -1))


def square(txt: str) -> int:
    if len(txt) != 2 or txt[0] not in FILES or txt[1] not in '12345678':
        raise ValueError('bad square: ' + txt)
    return FILES.index(txt[0]) + 8 * (int(txt[1]) - 1)


def name(sq: int) -> str:
    return FILES[sq % 8] + str(sq // 8 + 1)


def at(f: int, r: int) -> int | None:
    return r * 8 + f if 0 <= f < 8 and 0 <= r < 8 else None


def friend(piece: str, white: bool) -> bool:
    return piece != '.' and piece.isupper() == white


@dataclass
class Position:
    board: list[str]
    white: bool = True
    rights: str = 'KQkq'
    ep: int | None = None
    halfmove: int = 0
    fullmove: int = 1

    @classmethod
    def start(cls) -> 'Position':
        return cls.from_fen('rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1')

    @classmethod
    def from_fen(cls, fen: str) -> 'Position':
        parts = fen.strip().split()
        if len(parts) != 6:
            raise ValueError('FEN must contain 6 fields')
        b = ['.'] * 64
        ranks = parts[0].split('/')
        if len(ranks) != 8:
            raise ValueError('bad FEN ranks')
        for r, row in zip(range(7, -1, -1), ranks):
            f = 0
            for ch in row:
                if ch.isdigit(): f += int(ch)
                else:
                    if ch not in 'PNBRQKpnbrqk' or f >= 8: raise ValueError('bad FEN piece')
                    b[r * 8 + f] = ch; f += 1
            if f != 8: raise ValueError('bad FEN row')
        if b.count('K') != 1 or b.count('k') != 1 or parts[1] not in ('w', 'b'):
            raise ValueError('invalid kings or side')
        return cls(b, parts[1] == 'w', '' if parts[2] == '-' else parts[2],
                   None if parts[3] == '-' else square(parts[3]), int(parts[4]), int(parts[5]))

    def key(self) -> tuple:
        # En-passant is relevant to repetition only if capture is possible.
        ep = self.ep
        if ep is not None:
            pawn_rank = ep // 8 - (1 if self.white else -1)
            pawn = 'P' if self.white else 'p'
            if not any(at(ep % 8 + f, pawn_rank) is not None and
                       self.board[at(ep % 8 + f, pawn_rank)] == pawn for f in (-1, 1)):
                ep = None
        return (''.join(self.board), self.white, ''.join(sorted(self.rights)), ep)

    def attacked(self, dest: int, by_white: bool) -> bool:
        f, r = dest % 8, dest // 8
        pawn = 'P' if by_white else 'p'
        pr = r - (1 if by_white else -1)
        for df in (-1, 1):
            sq = at(f + df, pr)
            if sq is not None and self.board[sq] == pawn: return True
        for df, dr in KNIGHT:
            sq = at(f + df, r + dr)
            if sq is not None and self.board[sq] == ('N' if by_white else 'n'): return True
        for df, dr in KING:
            sq = at(f + df, r + dr)
            if sq is not None and self.board[sq] == ('K' if by_white else 'k'): return True
        for directions, attackers in ((BISHOP, 'BQ'), (ROOK, 'RQ')):
            for df, dr in directions:
                nf, nr = f + df, r + dr
                while (sq := at(nf, nr)) is not None:
                    p = self.board[sq]
                    if p != '.':
                        if friend(p, by_white) and p.upper() in attackers: return True
                        break
                    nf += df; nr += dr
        return False

    def check(self, white: bool) -> bool:
        king = 'K' if white else 'k'
        if king not in self.board:
            raise ValueError('king missing')
        return self.attacked(self.board.index(king), not white)

    def pseudo(self) -> Iterator[str]:
        side = self.white
        for src, p in enumerate(self.board):
            if not friend(p, side): continue
            f, r, kind = src % 8, src // 8, p.upper()
            if kind == 'P':
                step = 1 if side else -1
                final_rank = 7 if side else 0
                for df in (-1, 0, 1):
                    nf, nr = f + df, r + step
                    dest = at(nf, nr)
                    if dest is None: continue
                    target = self.board[dest]
                    if df == 0:
                        if target != '.': continue
                    elif (target == '.' and dest != self.ep) or (target != '.' and friend(target, side)):
                        continue
                    # Cannot capture a king.
                    if target.upper() == 'K': continue
                    base = name(src) + name(dest)
                    if nr == final_rank:
                        for promo in 'qrbn': yield base + promo
                    else: yield base
                if r == (1 if side else 6):
                    mid = at(f, r + step)
                    dst = at(f, r + step * 2)
                    if self.board[mid] == self.board[dst] == '.': yield name(src) + name(dst)
            elif kind in ('N', 'K'):
                for df, dr in (KNIGHT if kind == 'N' else KING):
                    dst = at(f + df, r + dr)
                    if dst is not None and not friend(self.board[dst], side) and self.board[dst].upper() != 'K':
                        yield name(src) + name(dst)
                if kind == 'K' and src == (4 if side else 60) and not self.check(side):
                    rank = 0 if side else 7
                    for flag, king_dest, rook_src, empty, safe in (
                        ('K' if side else 'k', 6 + 8 * rank, 7 + 8 * rank, [5,6], [5,6]),
                        ('Q' if side else 'q', 2 + 8 * rank, 8 * rank, [1,2,3], [3,2])):
                        rook = 'R' if side else 'r'
                        if flag in self.rights and self.board[rook_src] == rook and \
                           all(self.board[x + 8 * rank] == '.' for x in empty) and \
                           all(not self.attacked(x + 8 * rank, not side) for x in safe):
                            yield name(src) + name(king_dest)
            else:
                dirs = BISHOP if kind == 'B' else ROOK if kind == 'R' else BISHOP + ROOK
                for df, dr in dirs:
                    nf, nr = f + df, r + dr
                    while (dst := at(nf, nr)) is not None:
                        target = self.board[dst]
                        if friend(target, side) or target.upper() == 'K': break
                        yield name(src) + name(dst)
                        if target != '.': break
                        nf += df; nr += dr

    def make(self, move: str) -> 'Position':
        src, dst = square(move[:2]), square(move[2:4])
        piece = self.board[src]
        if piece == '.': raise ValueError('no piece on ' + name(src))
        side = self.white
        if not friend(piece, side): raise ValueError('wrong side')
        new = Position(self.board.copy(), not side, self.rights, None,
                       self.halfmove + 1, self.fullmove + (not side))
        taken = new.board[dst]
        new.board[src] = '.'
        if piece.upper() == 'P' and dst == self.ep and taken == '.' and src % 8 != dst % 8:
            new.board[dst + (-8 if side else 8)] = '.'
            taken = 'p' if side else 'P'
        new.board[dst] = (move[4].upper() if side else move[4].lower()) if len(move) == 5 else piece
        if piece.upper() == 'K' and abs(dst - src) == 2:
            rook_from, rook_to = ((7, 5) if dst > src else (0, 3))
            rook_from += (0 if side else 56)
            rook_to += (0 if side else 56)
            new.board[rook_to] = new.board[rook_from]
            new.board[rook_from] = '.'
        if piece.upper() == 'P' and abs(dst - src) == 16:
            new.ep = (src + dst) // 2
        if piece.upper() == 'P' or taken != '.': new.halfmove = 0
        for sq, flag in ((0, 'Q'), (7, 'K'), (56, 'q'), (63, 'k')):
            if src == sq or dst == sq: new.rights = new.rights.replace(flag, '')
        if piece == 'K': new.rights = new.rights.replace('K', '').replace('Q', '')
        if piece == 'k': new.rights = new.rights.replace('k', '').replace('q', '')
        return new

    def legal(self) -> list[str]:
        return [m for m in self.pseudo() if not self.make(m).check(self.white)]

    def san(self, move: str, known_legal: list[str] | None = None) -> str:
        possible = known_legal if known_legal is not None else self.legal()
        if move not in possible: raise ValueError('illegal move: ' + move)
        src, dst = square(move[:2]), square(move[2:4]); p = self.board[src]
        piece = p.upper()
        if piece == 'K' and abs(dst - src) == 2:
            word = 'O-O' if dst > src else 'O-O-O'
        else:
            captured = (self.board[dst] != '.' or piece == 'P' and dst == self.ep and src % 8 != dst % 8)
            disambig = ''
            if piece == 'P':
                if captured: disambig = FILES[src % 8]
            else:
                rivals = [square(m[:2]) for m in possible if m != move and m[2:4] == move[2:4] and
                          self.board[square(m[:2])].upper() == piece]
                if rivals:
                    if all(x % 8 != src % 8 for x in rivals): disambig = FILES[src % 8]
                    elif all(x // 8 != src // 8 for x in rivals): disambig = str(src // 8 + 1)
                    else: disambig = name(src)
            word = ('' if piece == 'P' else piece) + disambig + ('x' if captured else '') + name(dst)
            if len(move) == 5: word += '=' + move[4].upper()
        next_pos = self.make(move)
        if next_pos.check(next_pos.white):
            word += '#' if not next_pos.legal() else '+'
        return word

    def result(self, repetitions: dict[tuple, int]) -> tuple[str, str] | None:
        # Returns chess PGN result and reason, not a made-up draw on ply limit.
        legal = self.legal()
        if not legal:
            if self.check(self.white): return ('0-1' if self.white else '1-0', 'checkmate')
            return ('1/2-1/2', 'stalemate')
        # Claimable draws are claimed automatically by this match harness.
        if self.halfmove >= 100: return ('1/2-1/2', '50-move claim')
        if repetitions.get(self.key(), 0) >= 3: return ('1/2-1/2', 'threefold claim')
        pieces = [(i, p) for i, p in enumerate(self.board) if p != '.' and p.upper() != 'K']
        if not pieces or (len(pieces) == 1 and pieces[0][1].upper() in ('B', 'N')):
            return ('1/2-1/2', 'insufficient material')
        if pieces and all(p.upper() == 'B' for _, p in pieces) and \
                len({((sq // 8) + (sq % 8)) % 2 for sq, _ in pieces}) == 1:
            return ('1/2-1/2', 'same-colour bishops')
        return None


def perft(position: Position, depth: int) -> int:
    if depth == 0: return 1
    return sum(perft(position.make(m), depth - 1) for m in position.legal())
