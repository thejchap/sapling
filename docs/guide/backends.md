# backends

storage backend configuration for sapling.

## available backends

sapling provides two built-in backends: sqlite and memory.

### sqlite backend

the default backend, provides persistent storage using sqlite.

#### in-memory mode

```python
from sapling import Database, SQLiteBackend

# explicitly create in-memory sqlite (also the default)
db = Database(backend=SQLiteBackend(":memory:"))

# or just use the default
db = Database()
```

**characteristics:**
- data stored in memory
- fast performance
- data lost when process ends
- great for development and testing

#### file-based mode

```python
from sapling import Database, SQLiteBackend

# store data in a file
db = Database(backend=SQLiteBackend("/path/to/database.sqlite"))
```

**characteristics:**
- data persists to disk
- survives process restarts
- acid guarantees
- suitable for production

#### persistence example

```python
from pathlib import Path
from sapling import Database, SQLiteBackend

# first process: write data
db_path = Path("./data/app.sqlite")
db_path.parent.mkdir(exist_ok=True)

db = Database(backend=SQLiteBackend(str(db_path)))
with db.transaction() as txn:
    txn.put(User, "user_1", User(name="alice", email="alice@example.com"))

# later, different process: read data
db2 = Database(backend=SQLiteBackend(str(db_path)))
with db2.transaction() as txn:
    doc = txn.fetch(User, "user_1")
    print(f"found: {doc.model.name}")  # prints: found: alice
```

#### thread safety

sqlite connections are thread-safe when used with `check_same_thread=False`, which sapling enables automatically. transactions provide serializable isolation, ensuring thread-safe operations.

### memory backend

pure python in-memory storage using a dict.

```python
from sapling import Database, MemoryBackend

db = Database(backend=MemoryBackend())
```

**characteristics:**
- no persistence (data lost on exit)
- pure python (no sqlite dependency)
- fast for small datasets
- perfect for testing

**use cases:**
- unit tests
- temporary caching
- development without file i/o
- environments without sqlite

#### example

```python
from sapling import Database, MemoryBackend

# create memory backend
backend = MemoryBackend()
db = Database(backend=backend)

# use like any other backend
with db.transaction() as txn:
    txn.put(User, "user_1", user)
    doc = txn.fetch(User, "user_1")

# data exists only while process runs
```

## choosing a backend

use this decision matrix:

| scenario | recommended backend |
|----------|---------------------|
| production app | `SQLiteBackend("/path/to/db.sqlite")` |
| development | `SQLiteBackend()` (in-memory) or `MemoryBackend()` |
| testing | `MemoryBackend()` for speed, `SQLiteBackend()` for realism |
| temporary cache | `MemoryBackend()` |
| persistence required | `SQLiteBackend("/path/to/db.sqlite")` |
| no sqlite available | `MemoryBackend()` |

## backend initialization

by default, backends initialize automatically when the database is created. for explicit control (e.g., fastapi lifespan):

### deferred initialization

```python
from sapling import Database

# defer initialization
db = Database(initialize=False)

# later, when ready
db.initialize()
```

### idempotent initialization

`initialize()` is safe to call multiple times:

```python
db = Database(initialize=False)

db.initialize()  # initializes
db.initialize()  # no-op
db.initialize()  # no-op
```

### fastapi lifespan example

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from sapling import Database

db = Database(initialize=False)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # initialize on startup
    db.initialize()
    yield
    # cleanup on shutdown (if needed)

app = FastAPI(lifespan=lifespan)
```

## custom backends

to create a custom backend, implement the `Backend` abstract base class:

```python
from sapling.backends.base import Backend
from sapling import Document

class CustomBackend(Backend):
    def initialize(self) -> None:
        # setup connection, schema, etc.
        pass

    def transaction(self):
        # return context manager
        pass

    def get(self, model_class, model_id):
        # return Document or None
        pass

    def put(self, model_class, model_id, model):
        # return Document
        pass

    def fetch(self, model_class, model_id):
        # return Document or raise NotFoundError
        pass

    def delete(self, model_class, model_id):
        # delete document
        pass

    def all(self, model_class):
        # return list of Documents
        pass
```

see the [api reference](../api/backends.md) for complete backend interface documentation.

### custom backend example ideas

- **redis backend**: cache documents in redis
- **http backend**: store documents via rest api
- **s3 backend**: persist to object storage
- **postgres backend**: use postgres instead of sqlite

## next steps

- [api reference - backends](../api/backends.md) - complete backend api
- [fastapi integration](fastapi.md) - lifecycle management
- [basic usage](basic-usage.md) - crud operations
