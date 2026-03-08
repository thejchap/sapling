import tempfile
from pathlib import Path

from pydantic import BaseModel
from tryke import expect, test

from sapling import Database, MemoryBackend, SaplingSettings, SQLiteBackend
from sapling.errors import NotFoundError


class Hello(BaseModel):
    hello: str = "world"


@test
def test_basic():
    db = Database()
    hello = Hello()
    with db.transaction() as txn:
        pk = "hello"
        record = txn.put(Hello, pk, hello)
        expect(record.model_id).to_equal(pk)
        maybe_record = txn.get(Hello, pk)
        expect(maybe_record).to_be_truthy()
        record = txn.fetch(Hello, pk)
        txn.delete(Hello, pk)
        expect(lambda: txn.fetch(Hello, pk)).to_raise(NotFoundError)


@test
def test_all_method():
    db = Database()
    with db.transaction() as txn:
        txn.put(Hello, "1", Hello(hello="one"))
        txn.put(Hello, "2", Hello(hello="two"))
        txn.put(Hello, "3", Hello(hello="three"))

        all_hellos = txn.all(Hello)
        expect(all_hellos).to_have_length(3)
        expect({h.model_id for h in all_hellos}).to_equal({"1", "2", "3"})
        expect({h.model.hello for h in all_hellos}).to_equal({"one", "two", "three"})


@test
def test_all_empty():
    db = Database()
    with db.transaction() as txn:
        all_hellos = txn.all(Hello)
        expect(all_hellos).to_equal([])


@test
def test_sqlite_backend_memory():
    backend = SQLiteBackend()
    db = Database(backend=backend)
    with db.transaction() as txn:
        txn.put(Hello, "test", Hello(hello="world"))
        doc = txn.fetch(Hello, "test")
        expect(doc.model.hello).to_equal("world")


@test
def test_sqlite_backend_file():
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = Path(tmp_dir) / "test.db"
        settings = SaplingSettings(sqlite_path=str(db_path))
        backend = SQLiteBackend(settings=settings)
        db = Database(backend=backend)

        with db.transaction() as txn:
            txn.put(Hello, "persistent", Hello(hello="saved"))

        settings2 = SaplingSettings(sqlite_path=str(db_path))
        db2 = Database(backend=SQLiteBackend(settings=settings2))
        with db2.transaction() as txn:
            doc = txn.fetch(Hello, "persistent")
            expect(doc.model.hello).to_equal("saved")


@test
def test_backend_all_method():
    backend = SQLiteBackend()
    db = Database(backend=backend)

    with db.transaction() as txn:
        txn.put(Hello, "a", Hello(hello="alpha"))
        txn.put(Hello, "b", Hello(hello="beta"))

        all_docs = txn.all(Hello)
        expect(all_docs).to_have_length(2)
        expect({d.model_id for d in all_docs}).to_equal({"a", "b"})


@test
def test_memory_backend():
    backend = MemoryBackend()
    db = Database(backend=backend)

    with db.transaction() as txn:
        txn.put(Hello, "test", Hello(hello="world"))
        doc = txn.fetch(Hello, "test")
        expect(doc.model.hello).to_equal("world")

        txn.put(Hello, "1", Hello(hello="one"))
        txn.put(Hello, "2", Hello(hello="two"))

        all_docs = txn.all(Hello)
        expect(all_docs).to_have_length(3)
        expect({d.model_id for d in all_docs}).to_equal({"test", "1", "2"})

        txn.delete(Hello, "test")
        expect(txn.get(Hello, "test")).to_be_none()

        expect(lambda: txn.fetch(Hello, "test")).to_raise(NotFoundError)


@test
def test_deferred_initialization():
    backend = SQLiteBackend()
    db = Database(backend=backend, initialize=False)

    db.initialize()

    with db.transaction() as txn:
        txn.put(Hello, "test", Hello(hello="world"))
        doc = txn.fetch(Hello, "test")
        expect(doc.model.hello).to_equal("world")


@test
def test_idempotent_initialization():
    backend = SQLiteBackend()
    db = Database(backend=backend, initialize=False)

    db.initialize()
    db.initialize()
    db.initialize()

    with db.transaction() as txn:
        txn.put(Hello, "test", Hello(hello="world"))


@test
def test_uninitialized_error():
    backend = SQLiteBackend()
    db = Database(backend=backend, initialize=False)

    def try_uninitialized() -> None:
        with db.transaction() as txn:
            txn.put(Hello, "test", Hello(hello="world"))

    expect(try_uninitialized).to_raise(ValueError, match="not initialized")
