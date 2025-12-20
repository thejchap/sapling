import pytest
from pydantic import BaseModel
from pytest_codspeed.plugin import BenchmarkFixture

from sapling import Database


class BenchmarkModel(BaseModel):
    name: str = "test"
    value: int = 42
    data: str = "x" * 100


@pytest.fixture
def db() -> Database:
    return Database()


@pytest.mark.benchmark(group="sqlite3_memory")
def test_benchmark_put(benchmark: BenchmarkFixture, db: Database) -> None:
    def put_operation() -> None:
        model = BenchmarkModel()
        with db.transaction() as txn:
            txn.put(BenchmarkModel, "hello", model)

    benchmark(put_operation)


@pytest.mark.benchmark(group="sqlite3_memory")
def test_benchmark_get(benchmark: BenchmarkFixture, db: Database) -> None:
    model = BenchmarkModel()
    with db.transaction() as txn:
        txn.put(BenchmarkModel, "hello", model)

        def get_operation() -> None:
            txn.get(BenchmarkModel, "hello")

        benchmark(get_operation)


@pytest.mark.benchmark(group="sqlite3_memory")
def test_benchmark_fetch(benchmark: BenchmarkFixture, db: Database) -> None:
    model = BenchmarkModel()
    with db.transaction() as txn:
        txn.put(BenchmarkModel, "hello", model)

        def fetch_operation() -> None:
            txn.fetch(BenchmarkModel, "hello")

        benchmark(fetch_operation)


@pytest.mark.benchmark(group="sqlite3_memory")
def test_benchmark_delete(benchmark: BenchmarkFixture, db: Database) -> None:
    def delete_operation() -> None:
        model = BenchmarkModel()
        with db.transaction() as txn:
            txn.put(BenchmarkModel, "hello", model)
            txn.delete(BenchmarkModel, "hello")

    benchmark(delete_operation)


@pytest.mark.benchmark(group="sqlite3_memory")
def test_benchmark_put_get_cycle(benchmark: BenchmarkFixture, db: Database) -> None:
    def put_get_cycle() -> None:
        model = BenchmarkModel()
        with db.transaction() as txn:
            txn.put(BenchmarkModel, "hello", model)
            txn.get(BenchmarkModel, "hello")

    benchmark(put_get_cycle)
