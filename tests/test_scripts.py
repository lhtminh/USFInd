"""Smoke tests: each CLI script imports cleanly (catches refactor breakage)."""

from __future__ import annotations


def test_seed_data_imports():
    from scripts import seed_data

    assert callable(seed_data.main)


def test_benchmark_imports():
    from scripts import benchmark

    assert callable(benchmark.main)


def test_backfill_embeddings_imports():
    from scripts import backfill_embeddings

    assert callable(backfill_embeddings.main)


def test_benchmark_percentiles_helper():
    from scripts.benchmark import _percentiles

    out = _percentiles([10.0, 20.0, 30.0, 40.0, 50.0])
    assert out[0.50] in {20.0, 30.0}  # boundary-dependent
    assert out[0.95] == 50.0
