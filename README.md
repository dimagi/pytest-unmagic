# pytest-unmagic

Pytest fixtures with conventional import semantics.

pytest-unmagic removes the "magic" from pytest fixtures. Instead of
relying on argument-name matching, fixtures are explicitly imported and
applied using standard Python conventions. This gives you IDE
navigation, clear dependency chains, and `unittest.TestCase` support.

## Quick Comparison

**Standard pytest** (implicit):

```python
# conftest.py
import pytest

@pytest.fixture
def db():
    return create_database()

# test_app.py -- where does `db` come from?
def test_query(db):
    assert db.query("SELECT 1")
```

**pytest-unmagic** (explicit):

```python
# fixtures.py
from unmagic import fixture

@fixture
def db():
    yield create_database()

# test_app.py -- clear import, visible dependency
from fixtures import db

def test_query():
    database = db()
    assert database.query("SELECT 1")
```

## Installation

```sh
pip install pytest-unmagic
```

## Quick Start

Define a fixture with `@fixture`, apply it with `@use` or call it to get
its value:

```python
from unmagic import fixture, use

@fixture
def greeting():
    yield "hello"

@use(greeting)
def test_greeting():
    value = greeting()
    assert value == "hello"
```

## Key Features

- **Explicit imports:** Fixtures are regular Python objects, imported
  where used

- **IDE support:** go-to-definition, find-usages, and refactoring work
  out of the box

- **`unittest.TestCase` support:** Apply fixtures to TestCase classes
  with `@use`

- **Gradual adoption:** Mix with standard pytest fixtures, migrate
  incrementally

- **Fixture scopes:** `function`, `class`, `module`, `package`, `session`

- **Magic fence:** Warn when magic fixtures are used in designated
  modules

## Core Concepts

### Define a fixture

```python
from unmagic import fixture

@fixture
def db():
    connection = create_connection()
    yield connection
    connection.close()
```

The fixture must yield exactly once. Code before `yield` is setup; code
after is teardown.

### Apply a fixture with `@use`

```python
from unmagic import use

@use(db)
def test_insert():
    database = db()
    database.insert({"key": "value"})
```

`@use` sets up the fixture and registers it for teardown. Call the fixture to retrieve its value.

### `@use` shorthand

A single fixture can be applied directly as a decorator:

```python
@db
def test_insert():
    database = db()
    ...
```

### Fixture scope

```python
@fixture(scope="module")
def shared_db():
    yield create_database()
```

### Apply fixtures to classes

```python
@use(db)
class TestQueries:
    def test_select(self):
        database = db()
        assert database.query("SELECT 1")
```

Works with `unittest.TestCase` too, unlike standard pytest fixtures.

### Autouse fixtures

```python
@fixture(autouse=__file__)
def setup_env():
    os.environ["MODE"] = "test"
    yield
    del os.environ["MODE"]
```

Or register autouse from another module:

```python
from unmagic import autouse
from .fixtures import setup_env

autouse(setup_env, __file__)
```

### Access pytest fixtures

```python
from unmagic import get_request

def test_output():
    capsys = get_request().getfixturevalue("capsys")
    print("hello")
    assert capsys.readouterr().out == "hello\n"
```

Or apply pytest fixtures by name:

```python
from unmagic import use

@use("db")  # pytest-django's db fixture
def test_models():
    ...
```

### Magic fixture fence

Warn when magic fixtures are used in specified modules:

```python
from unmagic import fence

fence.install(["mypackage.tests"])
```

## Documentation

| Document                                   | Description                           |
|--------------------------------------------|---------------------------------------|
| [Tutorial](docs/tutorial.md)               | Hands-on introduction (~30 min)       |
| [Migration Guide](docs/migration-guide.md) | Convert from standard pytest fixtures |
| [API Reference](docs/api-reference.md)     | Complete technical reference          |
| [How-to Guides](docs/howto/index.md)       | Task-focused solutions                |
| [Concepts](docs/concepts.md)               | Philosophy and design principles      |
| [FAQ](docs/faq.md)                         | Common questions and troubleshooting  |

## Compatibility

- **Python:** 3.9+
- **pytest:** 8.1+

## Running the Test Suite

```sh
cd path/to/pytest-unmagic
pip install -e .
pytest
```

## Publishing

Push a tag matching `vX.Y.Z` (where X.Y.Z matches the version in
[`__init__.py`](src/unmagic/__init__.py)) to publish to PyPI.

A test release is published to https://test.pypi.org/p/pytest-unmagic on every
push to the *main* branch.

Publishing is automated with [GitHub Actions](.github/workflows/pypi.yml).
