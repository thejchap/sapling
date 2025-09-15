# sapling

sapling is an embedded data storage solution for pydantic models, built on
sqlite

## development

validate changes by using the following steps:

- type checker: `uv run basedpyright`
- tests: `uv run pytest`

run the linter and formatter to ensure code quality:

- `uv run ruff check --fix`
- `uv run ruff format`

## references

- python typing docs: https://docs.python.org/3/library/typing.html
- pydantic docs: https://docs.pydantic.dev/2.4/
