# API Reference

Complete technical reference for all public APIs in pytest-unmagic.

## Module: `unmagic`

### `fixture(func=None, /, scope="function", autouse=False)`

Define an unmagic fixture.

**Parameters:**

| Parameter | Type              | Default      | Description                                                                                                                                      |
|-----------|-------------------|--------------|--------------------------------------------------------------------------------------------------------------------------------------------------|
| `func`    | callable or `str` | `None`       | A generator function, context manager, or pytest fixture name (string). When `None`, returns a decorator.                                        |
| `scope`   | `str`             | `"function"` | Fixture lifecycle scope. One of: `"function"`, `"class"`, `"module"`, `"package"`, `"session"`.                                                  |
| `autouse` | `bool` or `str`   | `False`      | Automatically apply the fixture. `True` applies to all tests. A file path (typically `__file__`) applies to tests within that module or package. |

**Returns:** `UnmagicFixture` instance.

**Usage as decorator:**

```python
from unmagic import fixture

@fixture
def my_fixture():
    # setup
    value = create_resource()
    yield value
    # teardown
    cleanup_resource(value)
```

**Usage with scope:**

```python
@fixture(scope="module")
def shared_resource():
    yield create_expensive_resource()
```

**Usage with autouse:**

```python
# Apply to all tests in this module
@fixture(autouse=__file__)
def setup_env():
    yield

# Apply to all tests in the session
@fixture(autouse=True)
def global_setup():
    yield
```

**Usage with a context manager:**

```python
from unittest.mock import patch

fixture(patch("mymodule.func", return_value=42), autouse=__file__)
```

**Usage with a string (pytest fixture name):**

```python
db = fixture("db")  # Wraps pytest-django's db fixture
```

**Requirements:**

- Generator functions must yield exactly once
- The yielded value becomes the fixture's return value when called
- Code after `yield` runs during teardown
- String arguments cannot use `autouse` or non-default `scope`

---

### `use(*fixtures)`

Apply one or more fixtures to a test function, test class, or another fixture.

**Parameters:**

| Parameter   | Type                                        | Description                                                                     |
|-------------|---------------------------------------------|---------------------------------------------------------------------------------|
| `*fixtures` | `UnmagicFixture`, context manager, or `str` | One or more fixtures to apply. Strings are interpreted as pytest fixture names. |

**Returns:** Decorator function.

**Raises:** `TypeError` if no fixtures are provided.

**Apply to a test function:**

```python
from unmagic import fixture, use

@fixture
def db():
    yield create_db()

@use(db)
def test_query():
    database = db()
    assert database.query("SELECT 1")
```

**Apply to a test class:**

```python
@use(db)
class TestDatabase:
    def test_insert(self):
        database = db()
        database.insert({"key": "value"})

    def test_query(self):
        database = db()
        assert database.query("SELECT 1")
```

**Apply multiple fixtures:**

```python
@use(db, cache, auth)
def test_full_stack():
    ...
```

**Apply a pytest fixture by name:**

```python
@use("db")
def test_django():
    ...
```

**Chain fixture dependencies:**

```python
@use(db)
@fixture
def populated_db():
    database = db()
    database.insert(seed_data)
    yield database
```

> [!NOTE]
> When applying `@use` to a fixture, place `@use` *above* `@fixture`:

```python
# Correct order:
@use(dependency)
@fixture
def my_fixture():
    yield

# Wrong: @use cannot wrap an autouse fixture:
@use(dependency)
@fixture(autouse=__file__)  # TypeError
def my_fixture():
    yield

# Correct: apply @use before @fixture(autouse=...):
@fixture(autouse=__file__)
@use(dependency)
def my_fixture():
    yield
```

---

### `get_request()`

Get the active pytest request object.

**Returns:** `pytest.FixtureRequest`

**Raises:** `ValueError` if called outside of a test or fixture context (i.e., there is no active request).

**Access pytest fixtures:**

```python
from unmagic import get_request

def test_output():
    capsys = get_request().getfixturevalue("capsys")
    print("hello")
    captured = capsys.readouterr()
    assert captured.out == "hello\n"
```

**Access test metadata:**

```python
def test_node_info():
    request = get_request()
    print(request.node.name)      # test name
    print(request.node.nodeid)    # full test ID
```

---

### `autouse(fixture, where)`

Register a fixture for automatic use within a scope.

This is useful when the fixture is defined in a shared module and you want to apply it to specific test modules or packages without using `@fixture(autouse=...)`.

**Parameters:**

| Parameter | Type             | Description                                                                             |
|-----------|------------------|-----------------------------------------------------------------------------------------|
| `fixture` | `UnmagicFixture` | An unmagic fixture to register.                                                         |
| `where`   | `str` or `True`  | `__file__` to apply within the current module or package. `True` to apply to all tests. |

**Returns:** None.

**Apply to a specific module:**

```python
# tests/fixtures.py
from unmagic import fixture

@fixture
def setup_env():
    yield

# tests/test_this.py
from unmagic import autouse
from .fixtures import setup_env

autouse(setup_env, __file__)
```

**Apply to a package (in `__init__.py`):**

```python
# tests/__init__.py
from unmagic import autouse
from .fixtures import setup_env

autouse(setup_env, __file__)
```

When `__file__` is in an `__init__.py`, the fixture applies to the entire package.

**Apply globally:**

```python
autouse(setup_env, True)
```

> [!WARNING]
> Calling `autouse()` during test execution (after collection) will emit
> a `UserWarning` since relevant tests may have already run.

---

## Module: `unmagic.fence`

### `fence.install(names=(), reset=False)`

Install a fence that warns when magic fixtures are used within the named
modules or packages.

**Parameters:**

| Parameter | Type              | Default | Description                                                       |
|-----------|-------------------|---------|-------------------------------------------------------------------|
| `names`   | sequence of `str` | `()`    | Module or package names to fence.                                 |
| `reset`   | `bool`            | `False` | If `True`, replace all existing fences instead of adding to them. |

**Returns:** Context manager. The fence is removed when the context exits.

**Raises:** `ValueError` if `names` is a string instead of a sequence.

**Install globally (e.g., in `conftest.py`):**

```python
# conftest.py
from unmagic import fence

fence.install(["mypackage.tests"])
```

**Install as a context manager:**

```python
from unmagic import fence

with fence.install(["mypackage.tests"]):
    # fence is active
    ...
# fence is removed
```

**Install for a pytest session with a fixture:**

```python
from pytest import fixture
from unmagic import fence

@fixture(scope="session", autouse=True)
def enforce_unmagic():
    with fence.install(["tests"]):
        yield
```

**Nested fences:**

Fences stack. Each `fence.install()` adds to the set of fenced modules.
Inner fences are removed when their context exits, but outer fences
remain.

---

### `fence.is_fenced(func)`

Check whether a function is within a fenced module.

**Parameters:**

| Parameter | Type     | Description                                                          |
|-----------|----------|----------------------------------------------------------------------|
| `func`    | callable | A function to check. Uses `func.__module__` to determine membership. |

**Returns:** `bool` -- `True` if the function's module is within a fenced namespace.

```python
from unmagic import fence

with fence.install(["mypackage.tests"]):
    from mypackage.tests.test_example import some_func
    assert fence.is_fenced(some_func)
```

---

## Fixture Calling Convention

An `UnmagicFixture` instance is callable with two behaviors:

- **`fixture()`** (no arguments): Retrieves the fixture's yielded value.
  The fixture is set up if it hasn't been already. Must be called
  within a test or fixture context.

- **`fixture(func)`** (one argument): Applies the fixture to `func`,
  equivalent to `@use(fixture)`. This is the `@use` shorthand.

```python
@fixture
def db():
    yield create_database()

# Shorthand: apply as decorator
@db
def test_something():
    database = db()  # retrieve value
    ...
```

---

## Compatibility

|                       | Supported                   |
|-----------------------|-----------------------------|
| **Python**            | 3.9, 3.10, 3.11, 3.12, 3.13 |
| **pytest**            | 8.1, 8.2, 8.3, 8.4          |
| **unittest.TestCase** | Yes (via `@use` on class)   |
