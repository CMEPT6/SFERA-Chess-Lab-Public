"""CMEPT6 1.1: UCI option, root volatility, and terminal status tests.

python3 tests/test_regression.py build/cmept6-engine
"""
import pathlib
import subprocess
import sys
import threading

ENGINE = str(pathlib.Path(sys.argv[1]).resolve()) if len(sys.argv) > 1 else str(pathlib.Path(__file__).resolve().parents[1] / 'build' / 'cmept6-engine')

def batch(command, timeout=10):
    return subprocess.run([ENGINE], input=command + '\nquit\n', text=True,
                          capture_output=True, timeout=timeout, check=True).stdout

out = batch('uci\nposition startpos\nverify\nstatus')
assert 'id name CMEPT6 Engine 1.1' in out
assert 'option name UncertaintySearch type check default false' in out
assert 'option name UncertaintyMargin type spin default 75 min 10 max 300' in out
assert 'verify ok' in out
assert 'status ongoing' in out
print('PASS: UCI options and board validation')

cases = [
    ('Checkmate', 'fen 7k/6Q1/5K2/8/8/8/8/8 b - - 0 1', 'checkmate'),
    ('Stalemate', 'fen 7k/5K2/6Q1/8/8/8/8/8 b - - 0 1', 'stalemate'),
    ('Dead position', 'fen 4k3/8/8/8/8/8/8/4K3 w - - 0 1', 'draw_dead_position'),
    ('50-move claim', 'fen 4k3/8/8/8/8/8/8/4K2R w - - 100 100', 'draw_50move_claimable'),
]
for title, fen, status in cases:
    out = batch(f'position {fen}\nstatus\nverify')
    assert f'status {status}' in out, f'{title}: {out}'
    assert 'verify ok' in out
    print(f'PASS: {title}')

out = batch('position startpos moves g1f3 g8f6 f3g1 f6g8 g1f3 g8f6 f3g1 f6g8\nstatus\nverify')
assert 'status draw_threefold_claimable' in out, out
assert 'verify ok' in out
print('PASS: threefold-repetition claim')


def search(on):
    p = subprocess.Popen([ENGINE], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, bufsize=1)
    timer = threading.Timer(25, lambda: p.kill() if p.poll() is None else None)
    timer.start()
    try:
        p.stdin.write(f'setoption name UncertaintySearch value {"true" if on else "false"}\n')
        p.stdin.write('position startpos\ngo depth 6\n')
        p.stdin.flush()
        result = []
        while True:
            line = p.stdout.readline()
            assert line, 'engine terminated unexpectedly'
            result.append(line.strip())
            if line.startswith('bestmove '):
                break
        p.stdin.write('quit\n'); p.stdin.flush(); p.wait(timeout=5)
        assert p.returncode == 0
        return result
    finally:
        timer.cancel()
        if p.poll() is None:
            p.kill()

base = search(False)
adaptive = search(True)
assert not any('CMEPT6 uncertainty depth' in s for s in base)
assert any('CMEPT6 uncertainty depth 6' in s for s in adaptive)
assert any('aspiration_researches' in s for s in adaptive)
assert base[-1] == adaptive[-1], (base[-1], adaptive[-1])
print('PASS: uncertainty toggle, completed depth-6 search and same start-position bestmove')
print('ALL REGRESSION TESTS PASSED')
