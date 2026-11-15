"""Independent perft regression positions plus UCI smoke tests.
Use: python tests/run_tests.py [path/to/sfera-engine]
"""
import pathlib
import subprocess
import sys
import threading

ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT = ROOT / 'build' / 'cmept6-engine'
ENGINE = str(pathlib.Path(sys.argv[1]).resolve()) if len(sys.argv) > 1 else str(DEFAULT)

CASES = [
    ('Initial', 'startpos', {1: 20, 2: 400, 3: 8902, 4: 197281}),
    ('Kiwipete', 'fen r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1', {1:48,2:2039,3:97862,4:4085603}),
    ('Position 3', 'fen 8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1', {1:14,2:191,3:2812,4:43238}),
    ('Position 4', 'fen r3k2r/Pppp1ppp/1b3nbN/nP6/BBP1P3/q4N2/Pp1P2PP/R2Q1RK1 w kq - 0 1', {1:6,2:264,3:9467,4:422333}),
    ('Position 5', 'fen rnbq1k1r/pp1Pbppp/2p5/8/2B5/8/PPP1NnPP/RNBQK2R w KQ - 1 8', {1:44,2:1486,3:62379,4:2103487}),
    ('Position 6', 'fen r4rk1/1pp1qppp/p1np1n2/2b1p1B1/2B1P1b1/P1NP1N2/1PP1QPPP/R4RK1 w - - 0 10', {1:46,2:2079,3:89890,4:3894594}),
]

for name, fen, depth_map in CASES:
    commands = f'position {fen}\n' + ''.join(f'perft {d}\n' for d in depth_map) + 'quit\n'
    result = subprocess.run([ENGINE], input=commands, text=True, capture_output=True, timeout=30, check=True)
    for depth, expected in depth_map.items():
        actual_line = f'perft {depth} {expected}'
        assert actual_line in result.stdout.splitlines(), f'{name} depth={depth}: expected {expected}; got:\n{result.stdout}'
    print(f'PASS: {name}, depth 1..{max(depth_map)}')

p = subprocess.Popen([ENGINE], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, bufsize=1)
timer = threading.Timer(10, lambda: p.kill() if p.poll() is None else None)
timer.start()
try:
    p.stdin.write('uci\nisready\nposition startpos moves e2e4 e7e5 g1f3\ngo depth 4\n')
    p.stdin.flush()
    output = []
    while True:
        line = p.stdout.readline()
        assert line, 'engine closed stream unexpectedly'
        output.append(line)
        if line.startswith('bestmove '):
            break
    assert any(line == 'uciok\n' for line in output)
    assert any(line == 'readyok\n' for line in output)
    assert any(line.startswith('info depth 4 ') for line in output)
    assert output[-1].split()[1] != '0000'
    p.stdin.write('quit\n'); p.stdin.flush()
    p.wait(timeout=3)
    assert p.returncode == 0
    print('PASS: UCI handshake and completed depth-4 search')
finally:
    timer.cancel()
    if p.poll() is None: p.kill()
# One-ply mate and additional depth-five starting-position perft regression.
mate = subprocess.Popen([ENGINE], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, bufsize=1)
try:
    mate.stdin.write('position fen 7k/8/5KQ1/8/8/8/8/8 w - - 0 1\ngo depth 4\n'); mate.stdin.flush()
    lines = []
    for line in mate.stdout:
        lines.append(line.strip())
        if line.startswith('bestmove '): break
    assert 'bestmove g6g7' in lines, f'Expected Qg7#: {lines}'
finally:
    mate.stdin.write('quit\n');mate.stdin.flush(); mate.wait(timeout=5)
print('PASS: one-move checkmate Qg7#')
print('ALL TESTS PASSED')
