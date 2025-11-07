from __future__ import annotations

"""
Seed discipline and hashing utilities for bassline module (Step 1 roadmap).

Provides:
- PCG32 PRNG (deterministic 32-bit generator)
- canonicalize_json(obj) -> str (sorted keys, compact)
- audit_hash(obj) -> str (sha256 of canonicalized JSON)
- master_seed(base_seed, payload, salt) -> int (stable 32-bit seed)

No external dependencies.
"""

import hashlib
import json
from typing import Any


class PCG32:
    """Minimal PCG32 implementation (XSH RR), deterministic across platforms.

    Based on reference algorithm: 64-bit state, 64-bit increment (odd),
    outputs 32-bit unsigned ints.
    """

    __slots__ = ("_state", "_inc")

    def __init__(self, seed: int, seq: int = 54_321) -> None:
        # state and increment are 64-bit; increment must be odd
        self._state = 0
        self._inc = ((seq << 1) | 1) & 0xFFFFFFFFFFFFFFFF
        self._step()
        self._state = (self._state + (seed & 0xFFFFFFFFFFFFFFFF)) & 0xFFFFFFFFFFFFFFFF
        self._step()

    def _step(self) -> None:
        mul = 6364136223846793005
        self._state = (self._state * mul + self._inc) & 0xFFFFFFFFFFFFFFFF

    def next_uint32(self) -> int:
        oldstate = self._state
        self._step()
        # XSH RR output transformation
        xorshifted = (((oldstate >> 18) ^ oldstate) >> 27) & 0xFFFFFFFF
        rot = (oldstate >> 59) & 0x1F
        # rotate right 32-bit
        return ((xorshifted >> rot) | (xorshifted << ((-rot) & 31))) & 0xFFFFFFFF

    def random(self) -> float:
        # Uniform [0,1) using 32-bit integer / 2**32
        return self.next_uint32() / 4294967296.0


def canonicalize_json(obj: Any) -> str:
    """Return a canonical JSON string with sorted keys and compact separators.

    Ensures stable ordering independent of input dict ordering.
    """
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def audit_hash(obj: Any) -> str:
    """SHA-256 hex digest of the canonicalized JSON representation of obj."""
    data = canonicalize_json(obj).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def master_seed(base_seed: int, payload: Any, salt: str = "ai_bass_v1") -> int:
    """Derive a stable 32-bit seed from a base seed and arbitrary payload.

    - Canonicalizes payload to ensure order independence.
    - Mixes base_seed, salt, and payload hash via SHA-256.
    - Returns a 32-bit integer suitable for PCG32.
    """
    base = int(base_seed) & 0xFFFFFFFF
    canon = canonicalize_json(payload)
    h = hashlib.sha256()
    h.update(salt.encode("utf-8"))
    h.update(base.to_bytes(4, "little"))
    h.update(canon.encode("utf-8"))
    digest = h.digest()
    # take first 4 bytes as unsigned 32-bit seed
    return int.from_bytes(digest[:4], "little")

