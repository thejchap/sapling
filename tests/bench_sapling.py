"""Benchmarks for Sapling database operations."""

import pytest
from pydantic import BaseModel
from pytest_codspeed.plugin import BenchmarkFixture
from ulid import ULID

from sapling import Database


class BenchmarkModel(BaseModel):
    """Test model for benchmarking."""

    name: str = "test"
    value: int = 42
    data: str = "x" * 100


@pytest.fixture
def db() -> Database:
    """Create a database instance for benchmarks."""
    return Database()


def test_benchmark_put(benchmark: BenchmarkFixture, db: Database) -> None:
    """Benchmark the put operation."""

    def put_operation() -> None:
        model = BenchmarkModel()
        with db.connection() as conn, conn.transaction() as txn:
            pk = str(ULID())
            txn.put(BenchmarkModel, pk, model)

    benchmark(put_operation)


def test_benchmark_get(benchmark: BenchmarkFixture, db: Database) -> None:
    """Benchmark the get operation."""
    # Setup: insert a record first
    model = BenchmarkModel()
    pk = str(ULID())
    with db.connection() as conn, conn.transaction() as txn:
        txn.put(BenchmarkModel, pk, model)

        def get_operation() -> None:
            txn.get(BenchmarkModel, pk)

        benchmark(get_operation)


def test_benchmark_fetch(benchmark: BenchmarkFixture, db: Database) -> None:
    """Benchmark the fetch operation."""
    # Setup: insert a record first
    model = BenchmarkModel()
    pk = str(ULID())
    with db.connection() as conn, conn.transaction() as txn:
        txn.put(BenchmarkModel, pk, model)

        def fetch_operation() -> None:
            txn.fetch(BenchmarkModel, pk)

        benchmark(fetch_operation)


def test_benchmark_delete(benchmark: BenchmarkFixture, db: Database) -> None:
    """Benchmark the delete operation."""

    def delete_operation() -> None:
        model = BenchmarkModel()
        pk = str(ULID())
        with db.connection() as conn, conn.transaction() as txn:
            txn.put(BenchmarkModel, pk, model)
            txn.delete(BenchmarkModel, pk)

    benchmark(delete_operation)


def test_benchmark_put_get_cycle(benchmark: BenchmarkFixture, db: Database) -> None:
    """Benchmark a full put-get cycle."""

    def put_get_cycle() -> None:
        model = BenchmarkModel()
        pk = str(ULID())
        with db.connection() as conn, conn.transaction() as txn:
            txn.put(BenchmarkModel, pk, model)
            txn.get(BenchmarkModel, pk)

    benchmark(put_get_cycle)
