from pydantic import BaseModel

from sapling.database import Database


class Hello(BaseModel):
    world: str = "world"


def test_hello_world():
    db = Database()
    hello = Hello()

    with db.connection() as conn, conn.transaction() as txn:
        txn.insert(hello)
