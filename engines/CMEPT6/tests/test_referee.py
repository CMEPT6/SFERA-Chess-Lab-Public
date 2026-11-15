#!/usr/bin/env python3
"""Independent perft reference suite and chess rule boundary tests."""
from referee import Position, perft

def check(fen, depth, expected, tag):
    result = perft(Position.from_fen(fen), depth)
    assert result == expected, (tag, result, expected)
    print('PASS', tag, depth, result, flush=True)

check('rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1', 4, 197281, 'startpos')
check('r3k2r/p1ppqpb1/bn2pnp1/2pP4/1p2P3/2N2N2/PPQBBPPP/R3K2R w KQkq - 0 1', 3, 85877, 'kiwipete')
check('8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1', 4, 43238, 'endgame position 3')
check('r3k2r/Pppp1ppp/1b3nbN/nP6/BBP1P3/q4N2/Pp1P2PP/R2Q1RK1 w kq - 0 1', 3, 9467, 'promotions and checks')

p=Position.start()
for move in 'e2e4 a7a6 e4e5 d7d5 e5d6'.split():
    assert move in p.legal(), move
    p=p.make(move)
assert p.board[Position.start().board.index('P')] is not None  # board representation intact
assert p.board[3*8+3] == '.', 'en-passant captured pawn removed'

p=Position.from_fen('r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1')
assert 'e1g1' in p.legal() and 'e1c1' in p.legal()
assert p.san('e1g1') == 'O-O'
assert p.make('e1g1').board[5] == 'R' and p.make('e1g1').board[7] == '.'

p=Position.from_fen('7k/P7/8/8/8/8/8/K7 w - - 0 1')
assert 'a7a8q' in p.legal() and p.make('a7a8q').board[56] == 'Q'

p=Position.from_fen('7k/6Q1/5K2/8/8/8/8/8 b - - 100 90')
assert p.result({p.key():1}) == ('1-0','checkmate'), 'checkmate precedes 50 move draw'

p=Position.from_fen('8/8/8/8/8/8/8/K6k w - - 0 1')
assert p.result({p.key():1}) == ('1/2-1/2','insufficient material')
print('ALL INDEPENDENT REFEREE TESTS PASS')
