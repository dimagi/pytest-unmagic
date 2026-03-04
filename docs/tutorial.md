# Tutorial

**Type:** Learning-oriented
**Time:** ~30 minutes
**Prerequisites:** Python basics, pytest installed
**Next:** [Migration Guide](migration-guide.md) or [How-to Guides](howto/index.md)

This tutorial teaches pytest-unmagic through hands-on practice. Each
lesson builds on the previous one.

## Setup

Install pytest-unmagic:

```bash
pip install pytest-unmagic
```

Create a working directory for the tutorial:

```bash
mkdir unmagic-tutorial && cd unmagic-tutorial
```

## Lesson 1: Your First Unmagic Fixture

Create `test_basics.py`:

```python
# test_basics.py
from unmagic import fixture

@fixture
def greeting():
    yield "hello"

def test_greeting():
    value = greeting()
    assert value == "hello"
```

Run it:

```bash
pytest test_basics.py -v
```

Expected output:

```
test_basics.py::test_greeting PASSED
```

**What happened:**

1. `@fixture` defines a fixture that yields a value (`"hello"`)
2. `greeting()` retrieves the fixture's value inside the test
3. pytest-unmagic manages setup and teardown automatically

Notice that calling `greeting()` inside a test does not re-execute the
fixture function. It returns the value that was already yielded when
the fixture was set up.

## Lesson 2: Fixture Setup and Teardown

Fixtures can run code before and after yielding. This is useful for
resource management.

Create `test_teardown.py`:

```python
# test_teardown.py
from unmagic import fixture

@fixture
def db_connection():
    # Setup: runs before the test
    print("connecting to database")
    connection = {"connected": True}
    yield connection
    # Teardown: runs after the test
    print("closing database connection")
    connection["connected"] = False

def test_database():
    conn = db_connection()
    assert conn["connected"] is True
```

Run it:

```bash
pytest test_teardown.py -v -s
```

Expected output:

```
test_teardown.py::test_database connecting to database
closing database connection
PASSED
```

> [!IMPORTANT]
> Code before `yield` is setup, code after `yield` is teardown. The
> fixture must yield exactly once.

## Lesson 3: Applying Fixtures with @use

When a fixture has side effects but you don't need its return value, use
the `@use` decorator to apply it.

Create `test_use.py`:

```python
# test_use.py
from unmagic import fixture, use

traces = []

@fixture
def tracer():
    traces.clear()
    yield
    print(f"traces: {traces}")

@use(tracer)
def test_one():
    traces.append("one")
    assert traces == ["one"]

@use(tracer)
def test_two():
    traces.append("two")
    assert traces == ["two"]
```

Run it:

```bash
pytest test_use.py -v -s
```

Expected output:

```
test_use.py::test_one traces: ['one']
PASSED
test_use.py::test_two traces: ['two']
PASSED
```

> [!IMPORTANT]
> `@use(tracer)` sets up and tears down `tracer` for each test, but
> doesn't pass a value. The test function takes no arguments.

## Lesson 4: @use Shorthand

When applying a single fixture, you can use the fixture itself as a
decorator instead of `@use()`.

Create `test_shorthand.py`:

```python
# test_shorthand.py
from unmagic import fixture

traces = []

@fixture
def tracer():
    traces.clear()
    yield

# These two are equivalent:

@tracer
def test_with_shorthand():
    traces.append("shorthand")
    assert traces == ["shorthand"]
```

Run it:

```bash
pytest test_shorthand.py -v
```

> [!IMPORTANT]
> `@tracer` is shorthand for `@use(tracer)` when applying a single
> fixture. This only works for applying the fixture as a decorator, not
> for retrieving its value.

## Lesson 5: Fixture Composition

Fixtures can use other fixtures. Decorate with `@use` to chain
dependencies.

Create `test_composition.py`:

```python
# test_composition.py
from unmagic import fixture, use

@fixture
def database():
    db = {"users": []}
    yield db
    db["users"].clear()

@use(database)
@fixture
def admin_user():
    db = database()
    db["users"].append({"name": "admin", "role": "admin"})
    yield db["users"][-1]

def test_admin_exists():
    user = admin_user()
    assert user["name"] == "admin"
    assert user["role"] == "admin"

def test_database_has_admin():
    admin = admin_user()
    db = database()
    assert admin in db["users"]
```

Run it:

```bash
pytest test_composition.py -v
```

> [!IMPORTANT]
> `@use(database)` on `admin_user` ensures `database` is set up before
> `admin_user`. Apply `@use` *before* `@fixture` (decorators apply
> bottom-up).

## Lesson 6: Fixture Scopes

By default, fixtures have `function` scope -- they are set up and torn
down for each test. You can change this with the `scope` parameter.

Create `test_scopes.py`:

```python
# test_scopes.py
from unmagic import fixture

setup_count = 0

@fixture(scope="module")
def shared_resource():
    global setup_count
    setup_count += 1
    print(f"\nsetup #{setup_count}")
    yield {"id": setup_count}
    print(f"teardown #{setup_count}")

def test_first():
    resource = shared_resource()
    assert resource["id"] == 1

def test_second():
    resource = shared_resource()
    # Same instance -- module-scoped fixture is set up once
    assert resource["id"] == 1

def test_setup_count():
    assert setup_count == 1
```

Run it:

```bash
pytest test_scopes.py -v -s
```

Expected output:

```
test_scopes.py::test_first
setup #1
PASSED
test_scopes.py::test_second PASSED
test_scopes.py::test_setup_count PASSED
teardown #1
```

Available scopes: `"function"` (default), `"class"`, `"module"`,
`"package"`, `"session"`.

## Lesson 7: Applying Fixtures to Classes

The `@use` decorator works on test classes, applying fixtures to every
test method in the class.

Create `test_classes.py`:

```python
# test_classes.py
from unmagic import fixture, use

@fixture
def items():
    yield []

@use(items)
class TestShoppingCart:
    def test_add_item(self):
        cart = items()
        cart.append("apple")
        assert "apple" in cart

    def test_empty_cart(self):
        cart = items()
        assert cart == []
```

Run it:

```bash
pytest test_classes.py -v
```

Expected output:

```
test_classes.py::TestShoppingCart::test_add_item PASSED
test_classes.py::TestShoppingCart::test_empty_cart PASSED
```

> [!IMPORTANT]
> `@use(items)` on the class applies the fixture to all test methods.
> Each test gets a fresh fixture instance (function scope by default).

This also works with `unittest.TestCase` -- unlike standard pytest
fixtures.

## Lesson 8: Accessing pytest Fixtures

You can access standard pytest fixtures (like `capsys`, `tmp_path`,
`monkeypatch`) using `get_request()`.

Create `test_pytest_interop.py`:

```python
# test_pytest_interop.py
from unmagic import get_request

def test_capture_output():
    capsys = get_request().getfixturevalue("capsys")
    print("hello")
    captured = capsys.readouterr()
    assert captured.out == "hello\n"
```

You can also apply pytest fixtures by name with `@use`:

```python
# test_use_pytest.py
from unmagic import use

@use("tmp_path")
def test_with_tmp_path():
    from unmagic import get_request
    tmp = get_request().getfixturevalue("tmp_path")
    p = tmp / "test.txt"
    p.write_text("hello")
    assert p.read_text() == "hello"
```

Run them:

```bash
pytest test_pytest_interop.py test_use_pytest.py -v
```

> [!IMPORTANT]
> `get_request()` gives access to the active pytest request, bridging
> unmagic and standard pytest fixtures.

## Lesson 9: The Fence Feature

The fence warns you when tests use magic pytest fixtures,
helping enforce explicit fixture usage.

Create `conftest.py`:

```python
# conftest.py
from unmagic import fence

fence.install(["test_fenced"])
```

Create `test_fenced.py`:

```python
# test_fenced.py
from pytest import fixture

@fixture
def magic_value():
    return 42

# This test uses a magic fixture -- fence will warn
def test_magic(magic_value):
    assert magic_value == 42
```

Run it:

```bash
pytest test_fenced.py -v
```

Expected output includes:

```
warnings summary
  ... UserWarning: test_fenced.py::test_magic used magic fixture(s): magic_value
```

The test still passes, but you get a warning. This helps with gradual
migration to explicit fixtures.

## Next Steps

You now know the core features of pytest-unmagic. Here's where to go
next:

- [Migration Guide](migration-guide.md): Convert existing pytest fixtures to unmagic
- [How-to Guides](howto/index.md): Solve specific problems
- [API Reference](api-reference.md): Complete API details
- [Concepts](concepts.md): Understand the design philosophy
