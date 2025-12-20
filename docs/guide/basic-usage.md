# basic usage

comprehensive guide to crud operations with sapling.

## defining models

sapling works with standard pydantic models - no special decorators or subclassing needed:

```python
from pydantic import BaseModel


class User(BaseModel):
    name: str
    email: str
    age: int | None = None


class Post(BaseModel):
    title: str
    content: str
    author_id: str
```

## creating a database

### default (in-memory sqlite)

```python
from sapling import Database

db = Database()
```

### file-based sqlite

```python
from sapling import Database, SQLiteBackend

db = Database(backend=SQLiteBackend("/path/to/db.sqlite"))
```

### memory backend

```python
from sapling import Database, MemoryBackend

db = Database(backend=MemoryBackend())
```

### deferred initialization

for fastapi lifespan or other lifecycle management:

```python
from sapling import Database

db = Database(initialize=False)

# later, when ready
db.initialize()
```

## documents

sapling wraps your pydantic models in a `Document` to preserve model purity:

```python
from sapling import Document

# Document attributes
doc.model  # your pydantic model instance
doc.model_id  # the unique identifier
doc.model_class  # fully qualified class name
```

this means your pydantic models don't need database-specific fields like `id` or `created_at`.

## type safety and ide support

sapling uses python's generic type system to preserve exact types through all operations. your ide and type checker understand what you're working with at every step.

```python
from sapling import Database


class User(BaseModel):
    name: str
    email: str


db = Database()

# get() returns Document[User] | None
doc = db.get(User, "user_1")

# type checker knows doc.model is User
if doc:
    # ide autocomplete works on doc.model
    print(doc.model.name)  # ✓ autocomplete shows: name, email
    print(doc.model.invalid_field)  # ✗ type error!

# fetch() returns Document[User] (no None)
user_doc = db.fetch(User, "user_1")
print(user_doc.model.email)  # type checker knows this exists

# all() returns list[Document[User]]
users = db.all(User)
for user_doc in users:
    # type checker knows user_doc.model is User
    print(user_doc.model.name)
```

the type parameter flows through:

- database methods preserve the model type
- transactions preserve the model type
- document wrappers are generic over the model type
- your ide suggests the correct fields on `doc.model`

this works with all python type checkers: pyright, mypy, and ty.

## crud operations

### inserting documents

use `put()` to insert or update documents:

```python
user = User(name="alice", email="alice@example.com", age=30)

with db.transaction() as txn:
    doc = txn.put(User, "user_1", user)
    print(f"stored: {doc.model_id}")
```

`put()` is an upsert - it inserts if the document doesn't exist, updates if it does.

### choosing model_id values

you control the unique identifier for each document:

```python
# simple string ids
txn.put(User, "alice", user)

# ulids for sortable, unique ids
from ulid import ULID

txn.put(User, str(ULID()), user)

# uuids
import uuid

txn.put(User, str(uuid.uuid4()), user)

# composite keys as strings
txn.put(Post, f"user_{user_id}_post_{post_id}", post)
```

### retrieving documents

`get()` returns `None` if not found:

```python
with db.transaction() as txn:
    maybe_user = txn.get(User, "user_1")
    if maybe_user:
        print(f"found: {maybe_user.model.name}")
    else:
        print("not found")
```

`fetch()` raises `NotFoundError` if not found:

```python
from sapling.errors import NotFoundError

with db.transaction() as txn:
    try:
        doc = txn.fetch(User, "user_1")
        print(f"found: {doc.model.name}")
    except NotFoundError:
        print("user not found")
```

### updating documents

use `put()` with the same `model_id` to update:

```python
with db.transaction() as txn:
    # get existing user
    doc = txn.fetch(User, "user_1")

    # modify the model
    updated_user = doc.model.model_copy(update={"age": 31})

    # save the update
    txn.put(User, "user_1", updated_user)
```

### deleting documents

```python
with db.transaction() as txn:
    txn.delete(User, "user_1")
```

`delete()` is idempotent - no error if the document doesn't exist.

### querying all documents

retrieve all documents of a given model class:

```python
with db.transaction() as txn:
    all_users = txn.all(User)
    for doc in all_users:
        print(f"{doc.model_id}: {doc.model.name}")
```

## working with multiple model types

sapling automatically isolates different model classes:

```python
with db.transaction() as txn:
    # store users
    txn.put(User, "user_1", User(name="alice", email="alice@example.com"))
    txn.put(User, "user_2", User(name="bob", email="bob@example.com"))

    # store posts
    txn.put(Post, "post_1", Post(title="hello", content="world", author_id="user_1"))
    txn.put(Post, "post_2", Post(title="goodbye", content="world", author_id="user_1"))

    # query by model class
    users = txn.all(User)  # returns 2 users
    posts = txn.all(Post)  # returns 2 posts
```

model classes are isolated by their class name, so `User` and `Post` documents are stored separately even with the same `model_id`.

## single-operation convenience methods

for single operations outside transactions, use the database methods directly:

```python
# these all create automatic transactions
doc = db.put(User, "user_1", user)
maybe_doc = db.get(User, "user_1")
doc = db.fetch(User, "user_1")
db.delete(User, "user_1")
docs = db.all(User)
```

## next steps

- [transactions](transactions.md) - transaction patterns and guarantees
- [backends](backends.md) - backend configuration and custom backends
- [fastapi integration](fastapi.md) - seamless fastapi integration
