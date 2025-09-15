from pydantic import BaseModel

from sapling import Database


class Hello(BaseModel):
    world: str = "world"


def test_basic():
    db = Database()
    hello = Hello()
    with db.connection() as conn, conn.transaction() as txn:
        record = txn.create(hello)
        record = txn.get(Hello, record.id_)
        assert record
        record = txn.fetch(Hello, record.id_)
        records = txn.query(Hello).where().all()
        assert len(records) == 1
