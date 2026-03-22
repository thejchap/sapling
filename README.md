# sapling

[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![PyPI](https://img.shields.io/pypi/v/sapling-db)](https://pypi.org/project/sapling-db/)
[![license](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![python](https://img.shields.io/badge/python-3.12%20%7C%203.13%20%7C%203.14-blue.svg)](https://python.org)
[![CI](https://github.com/thejchap/sapling/actions/workflows/ci.yml/badge.svg)](https://github.com/thejchap/sapling/actions/workflows/ci.yml)

## installation

```
pip install sapling-db
```

## overview

simple, zero-setup persistence for pydantic models

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

**features:**

- **fully typed** - complete type safety with ide autocomplete and type checking
- **zero setup** - works out of the box with no configuration
- **pydantic native** - designed specifically for pydantic models
- **fastapi ready** - seamless dependency injection for request-scoped transactions
- **sqlite backed** - solid, battle-tested storage
