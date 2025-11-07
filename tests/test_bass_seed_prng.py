from __future__ import annotations

from techno_engine.bass_seed import PCG32, canonicalize_json, audit_hash, master_seed


def test_prng_repeatability_same_seed():
    a = PCG32(seed=123456, seq=789)
    b = PCG32(seed=123456, seq=789)
    seq_a = [a.next_uint32() for _ in range(10)]
    seq_b = [b.next_uint32() for _ in range(10)]
    assert seq_a == seq_b
    # random() should also match elementwise
    a2 = PCG32(seed=42, seq=1)
    b2 = PCG32(seed=42, seq=1)
    floats_a = [a2.random() for _ in range(5)]
    floats_b = [b2.random() for _ in range(5)]
    assert floats_a == floats_b


def test_canonicalization_order_independent():
    x1 = {"b": 2, "a": 1, "c": [3, {"z": 9, "y": 8}]}
    x2 = {"c": [3, {"y": 8, "z": 9}], "a": 1, "b": 2}
    s1 = canonicalize_json(x1)
    s2 = canonicalize_json(x2)
    assert s1 == s2
    h1 = audit_hash(x1)
    h2 = audit_hash(x2)
    assert h1 == h2


def test_master_seed_stability_and_order_independence():
    payload1 = {"alpha": 1, "beta": [1, 2, 3], "params": {"x": 10, "y": 20}}
    payload2 = {"params": {"y": 20, "x": 10}, "beta": [1, 2, 3], "alpha": 1}
    s1 = master_seed(1234, payload1, salt="unit_test_salt")
    s2 = master_seed(1234, payload2, salt="unit_test_salt")
    assert s1 == s2
    # Changing base_seed or salt must change the result (very high probability)
    s3 = master_seed(1235, payload1, salt="unit_test_salt")
    s4 = master_seed(1234, payload1, salt="different_salt")
    assert s3 != s1
    assert s4 != s1

