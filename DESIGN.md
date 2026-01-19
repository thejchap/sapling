# design

## unstructured thoughts

- zero-setup persistence
- solid, battle-tested storage (sqlite)
- extend pydantic - does not require subclassing, etc. just annotate existing
  pydantic models
- easy integration with fastapi
- strongly typed
- primary keys - options
  - define field _on_ pydantic model
    - `@primary_key` decorator
    - `Annotated[str, PrimaryKey]`
    - requires a bit more upfront work for users (and requires framework to
      validate)
    - system fields/auto generated
      - if on pydantic model need to do some metaprogramming
      - conflicts with other model fields
    - requires more non-pydantic code on pydantic models
  - wrapper class gets returned from DB: `Document[MyModel]`
    - pydantic models can stay "pure"
    - this can have system-generated persistence-related fields on it, makes it
      easier to swap out for other storage
    - more closely mirrors the actual structure of data (you have a generic
      document with MyModel specialization, that has a `.model` field on it with
      the actual model)
    - in the db a document would be a unit of persistence, with the model
      contents being a json blob on it
- queries
  - allow sql queries directly
    - user would have to get the correct shape back for `Document[MyModel]`
  - query builder
    - large in scope, would have to think more about escape hatches
  - explicit indexes to query on other fields besides pk

## references

- <https://www.convex.dev/>
- <https://backchannel.org/blog/friendfeed-schemaless-mysql>
- <https://www.prisma.io/client>
- <https://docs.python.org/3/library/typing.html>
- <https://docs.pydantic.dev/2.12/>
- <https://fastapi.tiangolo.com/tutorial/>
- <https://docs.python.org/3/library/sqlite3.html>
- <https://docs.python.org/3/library/doctest.html>
