# sapling

[![ci](https://github.com/thejchap/sapling/actions/workflows/ci.yml/badge.svg)](https://github.com/thejchap/sapling/actions/workflows/ci.yml)
[![CodSpeed](https://img.shields.io/endpoint?url=https://codspeed.io/badge.json)](https://codspeed.io/gh/thejchap/sapling)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

simple, zero-setup, sqlite-backed persistence for pydantic models

```python
from pydantic import BaseModel
from sapling import Database


class User(BaseModel):
    name: str
    email: str


db = Database()

with db.transaction() as txn:
    user = User(name="alice", email="alice@example.com")
    doc = txn.put(User, "123", user)
    txn.fetch(User, "123")
```
