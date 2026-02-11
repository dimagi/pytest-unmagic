# FAQ

**Type:** Troubleshooting and common questions

## Getting Started

### Should I use pytest-unmagic?

Use pytest-unmagic if you want:

- Explicit fixture dependencies via standard Python imports
- IDE navigation (go-to-definition, find-usages) for fixtures
- Fixtures that work with `unittest.TestCase`
- To eliminate name-collision issues with pytest's fixture discovery

If you're happy with standard pytest fixtures and don't experience these
pain points, you don't need to switch.

### Can I mix unmagic and standard pytest fixtures?

Yes. pytest-unmagic is designed for gradual adoption. You can use both
in the same project, and even in the same test file. Use
`get_request().getfixturevalue("name")` or `@use("name")` to access
standard pytest fixtures from unmagic code.

### Do I need to migrate all at once?

No. You can migrate one file or one fixture at a time. The
[Migration Guide](migration-guide.md) covers gradual adoption strategies.

## Common Errors

### "There is no active request"

**Error:**

```
ValueError: There is no active request
```

**Cause:** `get_request()` or a fixture call was made outside of a test
or fixture context.

**Solution:** Ensure you only call `get_request()` or call fixtures
inside a test function or another fixture:

```python
# Wrong: called at module level
value = my_fixture()  # ValueError

# Correct: called inside a test
def test_something():
    value = my_fixture()
```

### "There is no active pytest session"

**Error:**

```
ValueError: There is no active pytest session
```

**Cause:** Attempted to access the active session before pytest has
started or after it has finished.

**Solution:** This typically happens in plugin code that runs too early.
Ensure your code runs during or after `pytest_sessionstart`.

### "fixture setup failed"

**Error:**

```
FAILED - fixture setup for 'test_name' failed: ExceptionType: message
```

**Cause:** An exception occurred during fixture setup (before `yield`).

**Solution:** Check the fixture's setup code. The error message includes
the exception type and message. Common causes:

- Missing resource (database, file, service)
- Incorrect fixture ordering (dependency not set up yet)
- Code error in the fixture

### "Cannot apply @use to autouse fixture"

**Error:**

```
TypeError: Cannot apply @use to autouse fixture ...
```

**Cause:** Applied `@use` on top of `@fixture(autouse=...)`.

**Solution:** Reverse the decorator order:

```python
# Wrong:
@use(dependency)
@fixture(autouse=__file__)
def my_fixture():
    yield

# Correct:
@fixture(autouse=__file__)
@use(dependency)
def my_fixture():
    yield
```

### "is not a fixture"

**Error:**

```
TypeError: <object> is not a fixture. Hint: expected generator function, context manager, or pytest.fixture name.
```

**Cause:** Passed something to `@use()` or `fixture()` that isn't a
valid fixture type.

**Solution:** Ensure you pass one of:

- A generator function decorated with `@fixture`
- A context manager
- A string naming a pytest fixture

```python
# Wrong:
@use(42)
def test_something():
    ...

# Correct:
@use(my_fixture)
def test_something():
    ...
```

### "names should be a sequence of strings, not a string"

**Error:**

```
ValueError: names should be a sequence of strings, not a string
```

**Cause:** Passed a string instead of a list to `fence.install()`.

**Solution:**

```python
# Wrong:
fence.install("mypackage.tests")

# Correct:
fence.install(["mypackage.tests"])
```

## Usage Questions

### How do I get the value from a fixture?

Call the fixture inside your test:

```python
@fixture
def db():
    yield create_database()

def test_query():
    database = db()  # returns the yielded value
    assert database.query("SELECT 1")
```

### How do I apply a fixture without needing its value?

Use `@use()` or the shorthand decorator:

```python
@use(setup_env)
def test_something():
    ...

# or shorthand with single fixture:
@setup_env
def test_something():
    ...
```

### How do I use fixtures from other files?

Import them like any Python object:

```python
# tests/fixtures.py
from unmagic import fixture

@fixture
def db():
    yield create_database()

# tests/test_queries.py
from .fixtures import db

def test_query():
    database = db()
    ...
```

### How do I parametrize tests that use unmagic fixtures?

`pytest.mark.parametrize` works normally:

```python
import pytest
from unmagic import fixture

@fixture
def db():
    yield create_database()

@pytest.mark.parametrize("query", ["SELECT 1", "SELECT 2"])
def test_query(query):
    database = db()
    result = database.execute(query)
    assert result is not None
```

### How do I use pytest-django's `db` fixture?

Use `@use("db")` to apply it by name:

```python
from unmagic import use

@use("db")
def test_database():
    from myapp.models import User
    User.objects.create(username="test")
    assert User.objects.count() == 1
```

## Debugging

### How do I see fixture setup/teardown output?

Use `pytest -s` to disable output capture:

```bash
pytest test_file.py -v -s
```

### How do I see which fixtures are active?

Use `get_request()` to inspect:

```python
from unmagic import get_request

def test_debug():
    request = get_request()
    print(request.fixturenames)  # list of active fixture names
```

## Best Practices

### Where should I define fixtures?

Define fixtures in a shared module (e.g., `tests/fixtures.py`) and
import them where needed. This makes dependencies visible at the top of
each test file.

```python
# tests/fixtures.py -- shared fixtures
from unmagic import fixture

@fixture
def db():
    yield create_database()

@fixture(scope="session")
def app():
    yield create_app()
```

### Should I use the fence?

The fence is useful when migrating a large codebase. It warns about
magic fixture usage in specific modules, helping you track migration
progress. Once migration is complete, you can keep it as a safety net or
remove it.

### How many fixtures should a test use?

Keep it minimal. If a test requires more than 3-4 fixtures, consider
composing them into a higher-level fixture that encapsulates the setup.

## See Also

- [Tutorial](tutorial.md):  Learn the basics
- [API Reference](api-reference.md):  Complete API details
- [Migration Guide](migration-guide.md):  Convert from standard pytest
- [How-to Guides](howto/index.md):  Task-focused solutions
