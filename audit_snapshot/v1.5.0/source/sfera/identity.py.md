# Canonical source fragment

Original file: `sfera/identity.py`
Lines: 1-62
Archive SHA-256: `b354d664e739928369b89ff334dce87a0b2e0c111355477998c2cb0d0f723892`

```python
from __future__ import annotations
import hashlib
from .chesslite import FILES


def _ep_is_actionable(board_field: str, side: str, ep: str) -> bool:
    """For identity/deduplication, an EP square matters only if side-to-move can
    actually capture onto it with a pawn. This follows repetition/transposition
    semantics more closely than blindly hashing the raw FEN EP field.
    """
    if ep == '-' or len(ep) != 2 or ep[0] not in FILES or ep[1] not in '36':
        return False
    files = FILES
    ef = files.index(ep[0])
    er = int(ep[1])
    sqs = {}
    rank = 8
    for row in board_field.split('/'):
        file_i = 0
        for ch in row:
            if ch.isdigit():
                file_i += int(ch)
            else:
                sqs[(file_i, rank)] = ch
                file_i += 1
        rank -= 1
    pawn = 'P' if side == 'w' else 'p'
    from_rank = er - 1 if side == 'w' else er + 1
    for df in (-1, 1):
        ff = ef + df
        if 0 <= ff < 8 and sqs.get((ff, from_rank)) == pawn:
            return True
    return False


def canonical_fen_core(fen: str) -> str:
    """Canonical state identity: board, side, castling, actionable en-passant.
    Halfmove/fullmove counters are deliberately excluded.
    """
    parts = fen.strip().split()
    if len(parts) < 4:
        raise ValueError(f'Invalid FEN: {fen!r}')
    board, side, castling, ep = parts[:4]
    castling = ''.join(c for c in 'KQkq' if c in castling) or '-'
    if not _ep_is_actionable(board, side, ep):
        ep = '-'
    return f'{board} {side} {castling} {ep}'


def position_hash128(fen: str) -> str:
    return hashlib.blake2b(canonical_fen_core(fen).encode('utf-8'), digest_size=16).hexdigest()


def source_fingerprint(path: str, sample: bytes | None = None, size: int | None = None, mtime_ns: int | None = None) -> str:
    h = hashlib.blake2b(digest_size=16)
    h.update(path.encode('utf-8', 'replace'))
    if size is not None: h.update(str(size).encode())
    if mtime_ns is not None: h.update(str(mtime_ns).encode())
    if sample: h.update(sample)
    return h.hexdigest()
```
