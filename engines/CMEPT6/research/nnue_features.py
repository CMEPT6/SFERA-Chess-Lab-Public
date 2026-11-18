"""Original CMEPT6 feature/accumulator research contract; NOT a trained evaluator.

MIT, same license as the containing engine. Squares a1=0..h8=63.
Only geometry and integer update parity are implemented. Synthetic weights
must never be used as a chess evaluation or reported as a strength result.
"""
from dataclasses import dataclass

PIECES = 'PNBRQK'
FEATURE_COUNT = 16 * 12 * 64


def context(board, white):
    king = board.index('K' if white else 'k')
    oriented = king if white else king ^ 56
    mirror = oriented % 8 >= 4
    canonical = oriented ^ (7 if mirror else 0)
    # Four file columns and four rank pairs, 16 buckets.
    return (canonical // 16) * 4 + canonical % 8, mirror


def features(board, white):
    bucket, mirror = context(board, white)
    result = set()
    for square, piece in enumerate(board):
        if piece == '.':
            continue
        oriented = square ^ (0 if white else 56) ^ (7 if mirror else 0)
        relative_piece = PIECES.index(piece.upper()) + (0 if piece.isupper() == white else 6)
        result.add((bucket * 12 + relative_piece) * 64 + oriented)
    return frozenset(result)


def synthetic_row(feature, width):
    """Deterministic small integer fixture, not trained network parameters."""
    return tuple(((feature + 1) * 31 + i * 17 + (feature >> (i % 8))) % 255 - 127
                 for i in range(width))


@dataclass
class Accumulator:
    white: bool
    width: int
    ctx: tuple
    active: frozenset
    values: list

    @classmethod
    def refresh(cls, board, white, width=128):
        active = features(board, white)
        values = [0] * width
        for feature in active:
            for i, weight in enumerate(synthetic_row(feature, width)):
                values[i] += weight
        return cls(white, width, context(board, white), active, values)

    def update(self, board):
        """Reference delta via sets; production will consume dirty-piece events.

        Returns True if a context change required refresh. A production king
        move must check BOTH bucket and mirror flag, including boundary moves.
        """
        ctx = context(board, self.white)
        active = features(board, self.white)
        if ctx != self.ctx:
            fresh = self.refresh(board, self.white, self.width)
            self.ctx, self.active, self.values = fresh.ctx, fresh.active, fresh.values
            return True
        for feature in self.active - active:
            for i, weight in enumerate(synthetic_row(feature, self.width)):
                self.values[i] -= weight
        for feature in active - self.active:
            for i, weight in enumerate(synthetic_row(feature, self.width)):
                self.values[i] += weight
        self.active = active
        return False
