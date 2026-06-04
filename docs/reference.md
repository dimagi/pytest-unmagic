# Reference

This guide documents pytest-unmagic's features and public API in full. For
installation and a quick introduction, see the [README](../README.md).

## Defining fixtures

A fixture is a generator function decorated with `@fixture`. It must `yield`
exactly once. Code before the `yield` runs during setup, the yielded value
becomes the fixture's value when it is [called](#call-a-fixture-to-retrieve-its-value),
and code after the `yield` runs during teardown.

```py
from unmagic import fixture

@fixture
def db():
    conn = connect()      # setup
    yield conn            # value
    conn.close()          # teardown
```

A fixture can also be built from a context manager or from the name of an
existing `@pytest.fixture`. See [`fixture`](#fixture) in the API reference for
the full signature.

### Fixture scope

Fixtures may declare a `scope` of `'function'` (the default), `'class'`,
`'module'`, `'package'`, or `'session'`. A fixture will be torn down after all
tests in its scope have run if any in-scope tests used the fixture.

```py
@fixture(scope="class")
def tracer():
    traces = []
    yield traces
    assert traces, "expected at least one trace"
```

### Autouse fixtures

Fixtures may be applied to tests automatically with `@fixture(autouse=...)`. The
value of the `autouse` parameter may be one of

- A test module or package path (usually `__file__`) to apply the fixture to all
  tests within the module or package.
- `True`: apply the fixture to all tests in the session.

```py
# Apply to all tests in this module or package
@fixture(autouse=__file__)
def setup_env():
    yield

# Apply to all tests in the session
@fixture(autouse=True)
def global_setup():
    yield
```

A single fixture may be registered for autouse in multiple modules and packages
with `unmagic.autouse`.

```py
# tests/fixtures.py
from unmagic import fixture

@fixture
def a_fixture():
    ...


# tests/test_this.py
from unmagic import autouse
from .fixtures import a_fixture

autouse(a_fixture, __file__)

...


# tests/test_that.py
from unmagic import autouse
from .fixtures import a_fixture

autouse(a_fixture, __file__)

...
```

When `__file__` belongs to an `__init__.py`, the fixture applies to the entire
package. Calling `autouse()` after collection has finished emits a `UserWarning`,
since relevant tests may already have run.

## Applying fixtures

Apply fixtures to a test function, a test class, or another fixture with the
`@use` decorator. If a single fixture is being applied, it may be used directly
as a decorator without `@use()` (the [shorthand](../README.md#use-shorthand)).

### Applying fixtures to test classes

The `@use` decorator can be used on test classes, which applies the fixture(s)
to every test in the class.

```py
@use(tracer)
class TestClass:
    def test_galaxy(self):
        traces.append("Is anybody out there?")
```

#### Unmagic fixtures on `unittest.TestCase` tests

Unlike standard pytest fixtures, unmagic fixtures can be applied directly to
`unittest.TestCase` tests.

### Chaining fixtures

Fixtures that use other fixtures should be decorated with `@use`, so
that fixture dependencies are chained.

```python
@use("db")
def parent_fixture():
    daedalus = Person.objects.create(name='Daedalus')
    yield daedalus
    daedalus.delete()

@use(parent_fixture)
@fixture
def child_fixture():
    daedalus = parent_fixture()
    icarus = Person.objects.create(name='Icarus', father=daedalus)
    yield

@use(child_fixture)
def test_flight():
    flyers = Person.objects.all()
    ...
```

`@use` cannot wrap an autouse fixture. To combine the two, apply
`@fixture(autouse=...)` as the outermost decorator:

```py
@fixture(autouse=__file__)
@use(dependency)
def my_fixture():
    yield
```

### Using pytest fixtures

Fixtures defined with `@pytest.fixture` can be applied to a test or other
fixture by passing the fixture name to `@use`. None of the built-in fixtures
provided by pytest make sense to use this way, but it is a useful technique for
fixtures that have side effects, such as pytest-django's `db` fixture.

```py
from unmagic import use

@use("db")
def test_database():
    ...
```

## Retrieving fixture values

### Call a fixture to retrieve its value

The value of a fixture can be retrieved within a test function or other fixture
by calling the fixture. This is similar to `request.getfixturevalue()`. Calling
a fixture that has already been set up returns the value it yielded during setup
rather than running it again.

```py
@fixture
def tracer():
    assert not traces, f"unexpected traces before setup: {traces}"
    yield traces
    traces.clear()

def test_append():
    traces = tracer()
    traces.append("hello")
    assert traces, "expected at least one trace"
```

### Accessing the pytest request object

The `unmagic.get_request()` function provides access to the test request object.
Among other things, it can be used to retrieve fixtures defined with
`@pytest.fixture`.

```py
from unmagic import get_request

def test_output():
    capsys = get_request().getfixturevalue("capsys")
    print("hello")
    captured = capsys.readouterr()
    assert captured.out == "hello\n"
```

## The magic fixture fence

It is possible to erect a fence around tests in a particular module or package
to ensure that magic fixtures are not used in that namespace except with the
`@use(...)` decorator.

```py
from unmagic import fence

fence.install(['mypackage.tests'])
```

This will cause warnings to be emitted for magic fixture usages within
`mypackage.tests`. Tests still pass, so a fence is a useful aid during gradual
migration: the warnings show which tests and fixtures still rely on name-matching
magic, and they decrease as the fence's namespace is migrated.

Fences stack: each `fence.install()` adds to the set of fenced modules, and
inner fences are removed when their context exits while outer fences remain. Pass
`reset=True` to replace all existing fences instead of adding to them. Use
`fence.is_fenced(func)` to check whether a function's module is within a fenced
namespace.

## API reference

### `fixture`

```
fixture(func=None, /, scope="function", autouse=False)
```

Define an unmagic fixture.

| Parameter | Type              | Default      | Description                                                                                                                                      |
|-----------|-------------------|--------------|--------------------------------------------------------------------------------------------------------------------------------------------------|
| `func`    | callable or `str` | `None`       | A generator function, context manager, or pytest fixture name (string). When `None`, returns a decorator.                                        |
| `scope`   | `str`             | `"function"` | Fixture lifecycle scope. One of: `"function"`, `"class"`, `"module"`, `"package"`, `"session"`.                                                  |
| `autouse` | `bool` or `str`   | `False`      | Automatically apply the fixture. `True` applies to all tests. A file path (typically `__file__`) applies to tests within that module or package. |

**Returns:** an `UnmagicFixture` instance.

A fixture can be built from a context manager:

```py
from unittest.mock import patch

fixture(patch("mymodule.func", return_value=42), autouse=__file__)
```

or from the name of an existing `@pytest.fixture`:

```py
db = fixture("db")  # wraps pytest-django's db fixture
```

A generator fixture must yield exactly once. String arguments cannot be combined
with `autouse` or a non-default `scope`.

### `use`

```
use(*fixtures)
```

Apply one or more fixtures to a test function, test class, or another fixture.

| Parameter   | Type                                        | Description                                                                     |
|-------------|---------------------------------------------|---------------------------------------------------------------------------------|
| `*fixtures` | `UnmagicFixture`, context manager, or `str` | One or more fixtures to apply. Strings are interpreted as pytest fixture names. |

**Returns:** a decorator function.

**Raises:** `TypeError` if no fixtures are provided.

### `get_request`

```
get_request()
```

Get the active pytest request object.

**Returns:** a `pytest.FixtureRequest`.

**Raises:** `ValueError` if called outside of a test or fixture context (i.e.
there is no active request).

### `autouse`

```
autouse(fixture, where)
```

Register a fixture for automatic use within a scope. This is useful when the
fixture is defined in a shared module and you want to apply it to specific test
modules or packages without using `@fixture(autouse=...)`.

| Parameter | Type             | Description                                                                             |
|-----------|------------------|-----------------------------------------------------------------------------------------|
| `fixture` | `UnmagicFixture` | An unmagic fixture to register.                                                         |
| `where`   | `str` or `True`  | `__file__` to apply within the current module or package. `True` to apply to all tests. |

**Returns:** `None`.

Calling `autouse()` during test execution (after collection) emits a
`UserWarning`, since relevant tests may already have run.

### `fence.install`

```
fence.install(names=(), reset=False)
```

Install a fence that warns when magic fixtures are used within the named modules
or packages.

| Parameter | Type              | Default | Description                                                       |
|-----------|-------------------|---------|-------------------------------------------------------------------|
| `names`   | sequence of `str` | `()`    | Module or package names to fence.                                 |
| `reset`   | `bool`            | `False` | If `True`, replace all existing fences instead of adding to them. |

**Returns:** a context manager. The fence is removed when the context exits.

**Raises:** `ValueError` if `names` is a string instead of a sequence.

### `fence.is_fenced`

```
fence.is_fenced(func)
```

Check whether a function is within a fenced module.

| Parameter | Type     | Description                                                          |
|-----------|----------|----------------------------------------------------------------------|
| `func`    | callable | A function to check. Uses `func.__module__` to determine membership. |

**Returns:** `bool` — `True` if the function's module is within a fenced
namespace.

### Fixture calling convention

An `UnmagicFixture` instance is callable with two behaviors:

- **`my_fixture()`** (no arguments): retrieves the fixture's yielded value. The
  fixture is set up if it hasn't been already. Must be called within a test or
  fixture context.

- **`my_fixture(func)`** (one argument): applies the fixture to `func`, equivalent
  to `@use(fixture)`. This is the `@use` shorthand.

```py
@fixture
def my_fixture():
    yield create_database()

# Shorthand: apply as a decorator
@my_fixture
def test_something():
    database = my_fixture()  # retrieve the value
    ...
```
