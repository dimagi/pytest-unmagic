# Migration Guide

**Type:** Step-by-step tutorial for experienced pytest users
**Time:** ~20 minutes
**Prerequisites:** Familiarity with standard pytest fixtures
**Next:** [How-to Guides](howto/index.md) or [API Reference](api-reference.md)

This guide shows how to convert standard pytest fixtures to
pytest-unmagic, one pattern at a time.

## Quick Reference

| Standard pytest                       | pytest-unmagic                                           |
|---------------------------------------|----------------------------------------------------------|
| `@pytest.fixture`                     | `from unmagic import fixture; @fixture`                  |
| `def test(fix):` (argument injection) | `@use(fix)` + `fix()` inside test                        |
| `conftest.py` auto-discovery          | Explicit `import` from any module                        |
| `@pytest.fixture(autouse=True)`       | `@fixture(autouse=__file__)` or `autouse(fix, __file__)` |
| `request.getfixturevalue("name")`     | `get_request().getfixturevalue("name")`                  |
| `@pytest.fixture(scope="module")`     | `@fixture(scope="module")`                               |

## Migration Strategy

pytest-unmagic supports gradual migration. You don't need to convert
everything at once.

**Recommended approach:**

1. Install pytest-unmagic
2. Write new fixtures with `@fixture`
3. Convert existing fixtures file by file
4. Use the fence to track progress (optional)

## Example 1: Basic Fixture

**Before (standard pytest):**

```python
# conftest.py
import pytest

@pytest.fixture
def db():
    connection = create_connection()
    yield connection
    connection.close()

# test_app.py
def test_query(db):
    assert db.query("SELECT 1")
```

**After (pytest-unmagic):**

```python
# fixtures.py
from unmagic import fixture

@fixture
def db():
    connection = create_connection()
    yield connection
    connection.close()

# test_app.py
from fixtures import db

def test_query():
    database = db()
    assert database.query("SELECT 1")
```

**What changed:**

1. `@pytest.fixture` becomes `@fixture` (from `unmagic`)
2. Fixture moves from `conftest.py` to a regular module (e.g., `fixtures.py`)
3. Test imports the fixture explicitly
4. Test calls `db()` instead of receiving it as an argument

## Example 2: Fixture With Setup/Teardown Side Effects

When a fixture's value isn't used, apply it with `@use` instead of
calling it.

**Before:**

```python
@pytest.fixture(autouse=True)
def clean_cache():
    yield
    cache.clear()

def test_caching():
    cache.set("key", "value")
    assert cache.get("key") == "value"
```

**After:**

```python
from unmagic import fixture, use

@fixture
def clean_cache():
    yield
    cache.clear()

@use(clean_cache)
def test_caching():
    cache.set("key", "value")
    assert cache.get("key") == "value"
```

## Example 3: Fixture With Scope

**Before:**

```python
@pytest.fixture(scope="session")
def app():
    app = create_app()
    yield app
    app.shutdown()

def test_homepage(app):
    response = app.get("/")
    assert response.status == 200
```

**After:**

```python
from unmagic import fixture

@fixture(scope="session")
def app():
    application = create_app()
    yield application
    application.shutdown()

def test_homepage():
    application = app()
    response = application.get("/")
    assert response.status == 200
```

## Example 4: Autouse Fixtures

**Before:**

```python
# conftest.py
@pytest.fixture(autouse=True)
def reset_state():
    yield
    global_state.reset()
```

**After (module-level):**

```python
# fixtures.py
from unmagic import fixture

@fixture
def reset_state():
    yield
    global_state.reset()

# test_module.py
from unmagic import autouse
from fixtures import reset_state

autouse(reset_state, __file__)
```

**After (all tests):**

```python
# fixtures.py
from unmagic import fixture

@fixture(autouse=True)
def reset_state():
    yield
    global_state.reset()
```

## Example 5: Class-Based Tests

**Before:**

```python
@pytest.fixture
def items():
    return []

class TestCart:
    def test_add(self, items):
        items.append("apple")
        assert items == ["apple"]
```

**After:**

```python
from unmagic import fixture, use

@fixture
def items():
    yield []

@use(items)
class TestCart:
    def test_add(self):
        cart = items()
        cart.append("apple")
        assert cart == ["apple"]
```

## Example 6: unittest.TestCase (New Capability)

Standard pytest fixtures don't work with `unittest.TestCase`.
pytest-unmagic does.

```python
import unittest
from unmagic import fixture, use

@fixture
def db():
    yield create_database()

@use(db)
class TestDatabase(unittest.TestCase):
    def test_query(self):
        database = db()
        self.assertTrue(database.query("SELECT 1"))
```

## Example 7: Using Standard pytest Fixtures

You can still use standard pytest fixtures from unmagic code:

**Access by name with `@use`:**

```python
from unmagic import use

@use("db")  # pytest-django's db fixture
def test_models():
    from myapp.models import User
    User.objects.create(username="test")
```

**Access via `get_request()`:**

```python
from unmagic import get_request

def test_output():
    capsys = get_request().getfixturevalue("capsys")
    print("hello")
    assert capsys.readouterr().out == "hello\n"
```

## Example 8: Parametrize

`pytest.mark.parametrize` works the same way:

```python
import pytest
from unmagic import fixture

@fixture
def db():
    yield create_database()

@pytest.mark.parametrize("table", ["users", "orders"])
def test_table_exists(table):
    database = db()
    assert database.has_table(table)
```

## Migration Patterns

### File-by-file migration

1. Pick a test file
2. Convert its fixtures to unmagic
3. Move fixtures to a shared module (e.g., `fixtures.py`)
4. Update imports in the test file
5. Run tests to verify

### Hybrid approach

Keep both styles during migration. Standard pytest fixtures and unmagic
fixtures can coexist.

### Using the fence for tracking

Install a fence to get warnings about remaining magic fixtures:

```python
# conftest.py
from unmagic import fence

fence.install(["tests"])
```

Then run tests and look for warnings:

```
UserWarning: tests/test_app.py::test_query used magic fixture(s): db
```

These warnings show which tests still use implicit fixtures.

## Common Pitfalls

### Forgetting to call the fixture

```python
# Wrong -- fixture is not called, `db` is the fixture object itself
def test_query():
    assert db.query("SELECT 1")  # AttributeError

# Correct -- call the fixture to get its value
def test_query():
    database = db()
    assert database.query("SELECT 1")
```

### Wrong decorator order

```python
# Wrong -- @use must come before @fixture
@fixture
@use(dependency)
def my_fixture():
    yield

# Correct
@use(dependency)
@fixture
def my_fixture():
    yield
```

### Forgetting to apply the fixture

```python
# Wrong -- fixture is never set up
from fixtures import db

def test_query():
    database = db()  # Error: fixture not set up

# Correct -- apply with @use (or use shorthand)
@use(db)
def test_query():
    database = db()
```

If you call a fixture without applying it first (via `@use` or
shorthand), it will still work for fixtures that are first used in the
same test. But applying fixtures explicitly with `@use` ensures proper
ordering when fixtures depend on each other.

## Checklist

After migrating a file:

- [ ] All fixtures use `@fixture` from `unmagic`
- [ ] All fixture dependencies use `@use` or shorthand
- [ ] Fixtures are imported explicitly (no conftest.py magic)
- [ ] Tests pass with `pytest -v`
- [ ] No fence warnings (if fence is installed)

## See Also

- [Tutorial](tutorial.md): Learn from scratch
- [API Reference](api-reference.md): Complete API details
- [How-to: pytest Fixture Interop](howto/pytest-fixture-interop.md): Mix
  with standard fixtures
- [Concepts](concepts.md) -- Understand the design philosophy
