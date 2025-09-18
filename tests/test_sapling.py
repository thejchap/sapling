from pydantic import BaseModel

from sapling import Database


class Hello(BaseModel):
    hello: str = "world"


def test_basic():
    db = Database()
    hello = Hello()
    with db.connection() as conn, conn.transaction() as txn:
        record = txn.create(hello)
        maybe_record = txn.get(Hello, record.model_id)
        assert maybe_record
        record = txn.fetch(Hello, record.model_id)
