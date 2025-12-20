# sapling

simple persistence for pydantic models

## overview

sapling provides zero-setup data persistence for pydantic models built on sqlite. it strives to be very simple.

## key features

- **zero setup**: works out of the box with no configuration
- **pydantic native**: designed specifically for pydantic models
- **sqlite backed**: solid, battle-tested storage
- **transaction support**: acid guarantees with context managers
- **fastapi ready**: seamless dependency injection
- **pluggable backends**: sqlite, memory, or custom

## quick example

```python
from pydantic import BaseModel
from sapling import Database

class User(BaseModel):
    name: str
    email: str

db = Database()

with db.transaction() as txn:
    user = User(name="alice", email="alice@example.com")
    doc = txn.put(User, "user_1", user)
    print(f"stored: {doc.model_id}")

    retrieved = txn.fetch(User, "user_1")
    print(f"retrieved: {retrieved.model.name}")
```

## installation

```bash
pip install sapling
```

## next steps

- [quickstart guide](getting-started/quickstart.md)
- [fastapi integration](guide/fastapi.md)
- [api reference](api/database.md)
