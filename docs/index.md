# sapling

simple persistence for pydantic models

## overview

sapling provides zero-setup data persistence for pydantic models built on sqlite. it strives to be very simple.

## key features

- **fully typed**: complete type safety with ide autocomplete and type checking
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

## type safety

sapling is built with full type safety. generic type parameters preserve your model types through all operations, giving you autocomplete and type checking in your ide.

```python
from pydantic import BaseModel
from sapling import Database


class User(BaseModel):
    name: str
    email: str


db = Database()

# type checker knows this returns Document[User] | None
doc = db.get(User, "user_1")

# ide autocomplete works on doc.model
if doc:
    reveal_type(doc.model)  # User
    print(doc.model.name)  # autocomplete suggests: name, email
    print(doc.model.invalid)  # type error caught before runtime!
```

types flow end-to-end from your pydantic models through database operations to your application code. your ide and type checker (pyright, mypy, ty) understand the exact types at every step.

## installation

```bash
pip install sapling
```

## next steps

- [quickstart guide](getting-started/quickstart.md)
- [fastapi integration](guide/fastapi.md)
- [api reference](api/database.md)
