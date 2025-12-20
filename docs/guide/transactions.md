# transactions

managing multi-operation transactions with sapling.

## automatic transactions

single-operation methods use automatic transactions:

```python
from sapling import Database

db = Database()

# each operation is automatically wrapped in a transaction
db.put(User, "user_1", user)       # commits immediately
maybe_user = db.get(User, "user_1") # commits immediately
db.delete(User, "user_1")           # commits immediately
```

## explicit transactions

for multiple operations, use explicit transactions:

### context manager pattern

```python
with db.transaction() as txn:
    # all operations in this block are part of one transaction
    txn.put(User, "user_1", user1)
    txn.put(User, "user_2", user2)
    txn.put(User, "user_3", user3)
    # automatic commit on successful exit
```

### automatic commit

when the context manager exits normally, the transaction commits:

```python
with db.transaction() as txn:
    txn.put(User, "user_1", user)
    txn.put(Post, "post_1", post)
# commit happens here
```

### automatic rollback

if an exception occurs, the transaction rolls back:

```python
with db.transaction() as txn:
    txn.put(User, "user_1", user)
    raise ValueError("something went wrong")
    txn.put(Post, "post_1", post)  # this never executes
# rollback happens here, user_1 is not saved
```

## transaction guarantees

sqlite provides acid guarantees:

- **atomicity**: all operations succeed or all fail
- **consistency**: database moves from one valid state to another
- **isolation**: transactions don't interfere with each other
- **durability**: committed data persists (for file-based sqlite)

### isolation levels

sqlite uses serializable isolation by default, which provides the strongest isolation guarantee.

## transaction patterns

### batch operations

insert multiple documents efficiently:

```python
users = [
    User(name="alice", email="alice@example.com"),
    User(name="bob", email="bob@example.com"),
    User(name="charlie", email="charlie@example.com"),
]

with db.transaction() as txn:
    for i, user in enumerate(users):
        txn.put(User, f"user_{i}", user)
```

### read-modify-write

safely update documents:

```python
with db.transaction() as txn:
    # read
    doc = txn.fetch(User, "user_1")

    # modify
    updated_user = doc.model.model_copy(update={"age": doc.model.age + 1})

    # write
    txn.put(User, "user_1", updated_user)
```

### conditional updates

only update if certain conditions are met:

```python
with db.transaction() as txn:
    doc = txn.fetch(User, "user_1")

    if doc.model.age < 18:
        updated_user = doc.model.model_copy(update={"age": 18})
        txn.put(User, "user_1", updated_user)
```

### error handling

handle errors gracefully with rollback:

```python
from sapling.errors import NotFoundError

try:
    with db.transaction() as txn:
        # this might raise NotFoundError
        user_doc = txn.fetch(User, "user_1")

        # this might raise ValueError
        if user_doc.model.age < 0:
            raise ValueError("invalid age")

        txn.delete(User, "user_1")
except NotFoundError:
    print("user not found, no changes made")
except ValueError as e:
    print(f"validation error: {e}, no changes made")
```

### verifying rollback

```python
with db.transaction() as txn:
    txn.put(User, "user_1", user)

try:
    with db.transaction() as txn:
        txn.put(User, "user_2", user2)
        raise Exception("oops")
except Exception:
    pass

# user_1 was committed (first transaction)
# user_2 was rolled back (second transaction)
with db.transaction() as txn:
    assert txn.get(User, "user_1") is not None
    assert txn.get(User, "user_2") is None
```

## fastapi integration

for fastapi, use the `transaction_dependency` method:

```python
from fastapi import Depends, FastAPI
from typing import Annotated
from sapling import Database
from sapling.backends.base import Backend

app = FastAPI()
db = Database()

@app.post("/users/{user_id}")
def create_user(
    user_id: str,
    user: User,
    txn: Annotated[Backend, Depends(db.transaction_dependency)],
):
    # transaction is automatically managed per request
    doc = txn.put(User, user_id, user)
    return {"id": doc.model_id, "user": doc.model.model_dump()}
```

see the [fastapi integration guide](fastapi.md) for more details.

## next steps

- [backends](backends.md) - backend configuration options
- [fastapi integration](fastapi.md) - request-scoped transactions
- [api reference](../api/database.md) - complete api documentation
