# quickstart

get up and running with sapling in minutes.

## basic example

```python
from pydantic import BaseModel
from sapling import Database


class User(BaseModel):
    name: str
    email: str


# create database (uses in-memory sqlite by default)
db = Database()

# use a transaction for multiple operations
with db.transaction() as txn:
    # create and store a user
    user = User(name="alice", email="alice@example.com")
    doc = txn.put(User, "user_1", user)
    print(f"stored user: {doc.model_id}")

    # retrieve the user
    retrieved = txn.fetch(User, "user_1")
    print(f"retrieved: {retrieved.model.name}")

    # get returns None if not found
    maybe_user = txn.get(User, "nonexistent")
    print(f"not found: {maybe_user}")

    # delete the user
    txn.delete(User, "user_1")
```

## what just happened?

let's break down what's happening:

1. **database creation**: `Database()` creates an in-memory sqlite database with no configuration needed
1. **transactions**: the `with db.transaction()` context manager ensures your operations are atomic
1. **document wrapper**: `txn.put()` wraps your pydantic model in a `Document` that includes metadata like `model_id`
1. **model_id as primary key**: you choose the unique identifier for each document
1. **get vs fetch**: `get()` returns `None` if not found, `fetch()` raises `NotFoundError`

## file-based storage

want persistence? just specify a file path:

```python
from sapling import Database, SQLiteBackend

# data persists to disk
db = Database(backend=SQLiteBackend("/path/to/db.sqlite"))

# use it the same way
with db.transaction() as txn:
    txn.put(User, "user_1", user)
```

## single operations

for single operations, sapling provides convenience methods with automatic transactions:

```python
from sapling import Database

db = Database()

# automatic transaction for single operation
user = User(name="bob", email="bob@example.com")
doc = db.put(User, "user_2", user)

# retrieve with automatic transaction
retrieved = db.fetch(User, "user_2")
```

## next steps

- [basic usage guide](../guide/basic-usage.md) - comprehensive crud operations
- [transactions](../guide/transactions.md) - transaction patterns and guarantees
- [fastapi integration](../guide/fastapi.md) - seamless fastapi integration
- [api reference](../api/database.md) - complete api documentation
