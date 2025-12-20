# fastapi integration

seamless integration between sapling and fastapi.

## why fastapi?

sapling is designed with fastapi in mind:

- **dependency injection**: transactions managed per request
- **automatic rollback**: errors trigger transaction rollback
- **type safety**: full type hints throughout
- **pydantic native**: works naturally with fastapi's pydantic integration

## basic setup

```python
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, status
from pydantic import BaseModel
from sapling import Database
from sapling.backends.base import Backend

class User(BaseModel):
    name: str
    email: str

# create database (deferred initialization for lifespan control)
db = Database(initialize=False)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # initialize on startup
    db.initialize()
    yield
    # cleanup on shutdown if needed

app = FastAPI(lifespan=lifespan)

@app.post("/users/{user_id}")
def create_user(
    user_id: str,
    user: User,
    txn: Annotated[Backend, Depends(db.transaction_dependency)],
):
    doc = txn.put(User, user_id, user)
    return {"id": doc.model_id, "user": doc.model.model_dump()}

@app.get("/users/{user_id}")
def get_user(
    user_id: str,
    txn: Annotated[Backend, Depends(db.transaction_dependency)],
):
    doc = txn.fetch(User, user_id)
    return doc.model.model_dump()
```

## transaction dependency

the `transaction_dependency()` method provides request-scoped transactions:

```python
txn: Annotated[Backend, Depends(db.transaction_dependency)]
```

**what it does:**
- opens a transaction at the start of the request
- yields the backend instance for crud operations
- commits the transaction on successful response
- rolls back the transaction if an exception occurs

## example routes

### create endpoint

```python
@app.post("/users/{user_id}", status_code=status.HTTP_201_CREATED)
def create_user(
    user_id: str,
    user: User,
    txn: Annotated[Backend, Depends(db.transaction_dependency)],
):
    doc = txn.put(User, user_id, user)
    return {"id": doc.model_id, "user": doc.model.model_dump()}
```

### read endpoint

```python
from sapling.errors import NotFoundError
from fastapi import HTTPException

@app.get("/users/{user_id}")
def get_user(
    user_id: str,
    txn: Annotated[Backend, Depends(db.transaction_dependency)],
):
    try:
        doc = txn.fetch(User, user_id)
        return doc.model.model_dump()
    except NotFoundError:
        raise HTTPException(status_code=404, detail="user not found")
```

### update endpoint

```python
@app.put("/users/{user_id}")
def update_user(
    user_id: str,
    user: User,
    txn: Annotated[Backend, Depends(db.transaction_dependency)],
):
    # put is an upsert - creates or updates
    doc = txn.put(User, user_id, user)
    return {"id": doc.model_id, "user": doc.model.model_dump()}
```

### delete endpoint

```python
@app.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: str,
    txn: Annotated[Backend, Depends(db.transaction_dependency)],
):
    txn.delete(User, user_id)
```

### list endpoint

```python
@app.get("/users")
def list_users(
    txn: Annotated[Backend, Depends(db.transaction_dependency)],
):
    docs = txn.all(User)
    return [{"id": doc.model_id, "user": doc.model.model_dump()} for doc in docs]
```

## error handling

sapling exceptions can be caught and converted to http responses:

```python
from fastapi import HTTPException
from sapling.errors import NotFoundError, SaplingError

@app.exception_handler(NotFoundError)
def handle_not_found(request, exc):
    raise HTTPException(status_code=404, detail="resource not found")

@app.exception_handler(SaplingError)
def handle_sapling_error(request, exc):
    raise HTTPException(status_code=500, detail=str(exc))
```

### automatic rollback

if a route raises an exception, the transaction automatically rolls back:

```python
@app.post("/users/{user_id}/risky")
def risky_operation(
    user_id: str,
    user: User,
    txn: Annotated[Backend, Depends(db.transaction_dependency)],
):
    # this gets saved
    txn.put(User, user_id, user)

    # this raises an exception
    if user.age < 18:
        raise ValueError("must be 18+")

    # if we get here, transaction commits
    # if exception raised, transaction rolls back
```

## application lifecycle

use fastapi's lifespan for initialization and cleanup:

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from sapling import Database, SQLiteBackend

db = Database(
    backend=SQLiteBackend("/app/data/db.sqlite"),
    initialize=False
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup: initialize database
    db.initialize()

    yield

    # shutdown: cleanup if needed
    # (sqlite connections are closed automatically)

app = FastAPI(lifespan=lifespan)
```

## multiple databases

use multiple database instances for different data domains:

```python
users_db = Database(
    backend=SQLiteBackend("/app/data/users.sqlite"),
    initialize=False
)

posts_db = Database(
    backend=SQLiteBackend("/app/data/posts.sqlite"),
    initialize=False
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    users_db.initialize()
    posts_db.initialize()
    yield

app = FastAPI(lifespan=lifespan)

@app.get("/users/{user_id}")
def get_user(
    user_id: str,
    txn: Annotated[Backend, Depends(users_db.transaction_dependency)],
):
    doc = txn.fetch(User, user_id)
    return doc.model.model_dump()

@app.get("/posts/{post_id}")
def get_post(
    post_id: str,
    txn: Annotated[Backend, Depends(posts_db.transaction_dependency)],
):
    doc = txn.fetch(Post, post_id)
    return doc.model.model_dump()
```

## complete example

```python
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, status
from pydantic import BaseModel
from sapling import Database
from sapling.backends.base import Backend
from sapling.errors import NotFoundError

class User(BaseModel):
    name: str
    email: str

db = Database(initialize=False)

@asynccontextmanager
async def lifespan(app: FastAPI):
    db.initialize()
    yield

app = FastAPI(lifespan=lifespan)

@app.post("/users/{user_id}", status_code=status.HTTP_201_CREATED)
def create_user(
    user_id: str,
    user: User,
    txn: Annotated[Backend, Depends(db.transaction_dependency)],
):
    doc = txn.put(User, user_id, user)
    return {"id": doc.model_id, "user": doc.model.model_dump()}

@app.get("/users/{user_id}")
def get_user(
    user_id: str,
    txn: Annotated[Backend, Depends(db.transaction_dependency)],
):
    try:
        doc = txn.fetch(User, user_id)
        return doc.model.model_dump()
    except NotFoundError:
        raise HTTPException(status_code=404, detail="user not found")

@app.put("/users/{user_id}")
def update_user(
    user_id: str,
    user: User,
    txn: Annotated[Backend, Depends(db.transaction_dependency)],
):
    doc = txn.put(User, user_id, user)
    return {"id": doc.model_id, "user": doc.model.model_dump()}

@app.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: str,
    txn: Annotated[Backend, Depends(db.transaction_dependency)],
):
    txn.delete(User, user_id)

@app.get("/users")
def list_users(
    txn: Annotated[Backend, Depends(db.transaction_dependency)],
):
    docs = txn.all(User)
    return [{"id": doc.model_id, "user": doc.model.model_dump()} for doc in docs]
```

## next steps

- [transactions](transactions.md) - transaction patterns and guarantees
- [backends](backends.md) - backend configuration options
- [api reference](../api/database.md) - complete api documentation
