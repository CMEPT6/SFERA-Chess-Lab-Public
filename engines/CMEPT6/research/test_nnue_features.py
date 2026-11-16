"""Run: python engines/CMEPT6/research/test_nnue_features.py"""
from pathlib import Path
import random
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tests'))
from referee import Position
from nnue_features import Accumulator, FEATURE_COUNT, context, features


class FeatureContractTests(unittest.TestCase):
    def check_transition(self, position, move):
        self.assertIn(move, position.legal())
        after = position.make(move)
        for white in (True, False):
            acc = Accumulator.refresh(position.board, white)
            before = acc.values.copy()
            acc.update(after.board)
            self.assertEqual(acc.values, Accumulator.refresh(after.board, white).values)
            acc.update(position.board)
            self.assertEqual(acc.values, before, 'undo must restore integer accumulator')
        return after

    def test_color_and_horizontal_symmetry(self):
        p = Position.start().make('e2e4').make('c7c5')
        rotated = ['.'] * 64
        mirrored = ['.'] * 64
        for square, piece in enumerate(p.board):
            rotated[square ^ 56] = piece.swapcase()
            mirrored[square ^ 7] = piece
        for white in (True, False):
            self.assertEqual(features(p.board, white), features(rotated, not white))
            self.assertEqual(features(p.board, white), features(mirrored, white))

    def test_special_moves_and_undo(self):
        cases = [
            ('r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1', 'e1g1'),
            ('r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1', 'e1c1'),
            ('4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 1', 'e5d6'),
            ('7k/8/8/8/8/8/3p4/4K3 w - - 0 1', 'e1d2'),
        ]
        for fen, move in cases:
            self.check_transition(Position.from_fen(fen), move)
        for promotion in 'qrbn':
            self.check_transition(Position.from_fen('1r5k/P7/8/8/8/8/8/4K3 w - - 0 1'), 'a7b8' + promotion)

    def test_mirror_boundary_refresh(self):
        p = Position.from_fen('7k/8/8/8/8/8/8/3K4 w - - 0 1')
        after = p.make('d1e1')
        self.assertEqual(context(p.board, True)[0], context(after.board, True)[0])
        acc = Accumulator.refresh(p.board, True)
        self.assertTrue(acc.update(after.board), 'mirror changes even when bucket does not')
        self.assertEqual(acc.values, Accumulator.refresh(after.board, True).values)

    def test_seeded_legal_walk(self):
        rng = random.Random(20261116)
        p = Position.start()
        accumulators = [Accumulator.refresh(p.board, white) for white in (True, False)]
        for _ in range(256):
            moves = p.legal()
            if not moves:
                p = Position.start()
                accumulators = [Accumulator.refresh(p.board, white) for white in (True, False)]
            else:
                p = p.make(rng.choice(moves))
            for acc in accumulators:
                acc.update(p.board)
                self.assertEqual(acc.values, Accumulator.refresh(p.board, acc.white).values)
                self.assertTrue(all(0 <= f < FEATURE_COUNT for f in acc.active))
                self.assertEqual(len(acc.active), sum(c != '.' for c in p.board))
                self.assertTrue(all(-32768 <= x <= 32767 for x in acc.values))


if __name__ == '__main__':
    unittest.main(verbosity=2)
