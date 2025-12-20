# installation

## requirements

- python 3.13+
- pydantic 2.12+

## install from pypi

```bash
pip install sapling
```

## optional dependencies

### fastapi integration

```bash
pip install sapling fastapi
```

## verify installation

```python
from sapling import Database

db = Database()
print("sapling ready!")
```
