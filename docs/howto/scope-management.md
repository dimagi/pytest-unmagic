# How to: Manage Fixture Scopes

**Problem:** You want to control when fixtures are set up and torn down
to optimize test performance or share state across tests.

## Solution

Pass the `scope` parameter to `@fixture`:

```python
from unmagic import fixture

@fixture(scope="module")
def expensive_resource():
    resource = create_expensive_resource()
    yield resource
    resource.cleanup()
```

## Available Scopes

| Scope                  | Setup                        | Teardown                   |
|------------------------|------------------------------|----------------------------|
| `"function"` (default) | Before each test             | After each test            |
| `"class"`              | Before first test in class   | After last test in class   |
| `"module"`             | Before first test in module  | After last test in module  |
| `"package"`            | Before first test in package | After last test in package |
| `"session"`            | Once per session             | At end of session          |

## Examples

### Function scope (default)

Each test gets a fresh instance:

```python
@fixture
def items():
    yield []

def test_one():
    lst = items()
    lst.append(1)
    assert lst == [1]

def test_two():
    lst = items()
    assert lst == []  # fresh list
```

### Module scope

Shared across all tests in the file:

```python
@fixture(scope="module")
def db():
    conn = connect_to_database()
    yield conn
    conn.close()

def test_read():
    database = db()
    assert database.query("SELECT 1")

def test_write():
    database = db()  # same connection as test_read
    database.execute("INSERT ...")
```

### Session scope

Shared across the entire test run:

```python
@fixture(scope="session")
def app():
    application = create_app()
    yield application
    application.shutdown()
```

### Combining scopes

Higher-scoped fixtures can be used by lower-scoped ones:

```python
@fixture(scope="session")
def app():
    yield create_app()

@use(app)
@fixture(scope="function")
def client():
    application = app()
    yield application.test_client()
```

## When to Use Each Scope

- **function**: Default. Use when each test needs clean state.
- **class**: Use when tests within a class share setup but classes don't.
- **module**: Use for expensive setup shared across a file (e.g., database connection).
- **package**: Use for setup shared across a directory of test files.
- **session**: Use for one-time global setup (e.g., starting an application).

> [!warning]
> A fixture cannot depend on a fixture with a narrower scope. For
> example, a session-scoped fixture cannot use a function-scoped
> fixture.

## Related

- [API Reference: fixture()](../api-reference.md#fixturefuncnone--scopefunction-autousefalse): Full parameter details
- [Tutorial: Lesson 6](../tutorial.md#lesson-6-fixture-scopes): Scope basics
