# pytest-unmagic

Pytest fixtures with conventional import semantics.

pytest's fixtures are powerful, but they rely on "magic": a test requests a
fixture by adding an argument whose name matches the fixture, and pytest
resolves it at runtime by searching `conftest.py` files and plugins. Where a
fixture comes from is not visible in the code, "go to definition" does not work,
and fixtures cannot be applied to `unittest.TestCase` tests.

pytest-unmagic applies the principle that explicit is better than implicit:
fixtures are imported, applied with a decorator, and called like ordinary Python
objects. Every dependency is visible and easy to navigate. Unmagic fixtures
coexist with standard pytest fixtures, so a project can adopt them gradually, one
fixture at a time.

## Installation

```sh
pip install pytest-unmagic
```

## Usage

Define fixtures with the `unmagic.fixture` decorator, and apply them to other
fixtures or test functions with `unmagic.use`.

```py
from unmagic import fixture, use

traces = []

@fixture
def tracer():
    assert not traces, f"unexpected traces before setup: {traces}"
    yield
    traces.clear()

@use(tracer)
def test_append():
    traces.append("hello")
    assert traces, "expected at least one trace"
```

A fixture must yield exactly once. The `@use` decorator causes the fixture to be
set up and registered for tear down, but does not pass the yielded value to the
decorated function. This is appropriate for fixtures that have side effects.

The location where a fixture is defined has no affect on where it can be used.
Any code that can import it can use it as long as it is executed in the context
of running tests and does not violate [scope](docs/reference.md#fixture-scope)
restrictions.

### @use shorthand

If a single fixture is being applied to another fixture or test it may be
applied directly as a decorator without `@use()`. The test in the example above
could have been written as

```py
@tracer
def test_append():
    traces.append("hello")
    assert traces, "expected at least one trace"
```

### Call a fixture to retrieve its value

The value of a fixture can be retrieved within a test function or other fixture
by calling the fixture. This is similar to `request.getfixturevalue()`.

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

## Learn more

The [reference guide](docs/reference.md) documents the rest of unmagic's
features in detail, including:

- Applying fixtures to test classes and `unittest.TestCase` tests
- Fixture scopes and teardown
- Autouse fixtures
- Accessing pytest's request object and reusing `@pytest.fixture` fixtures
- Chaining fixtures that depend on other fixtures
- Erecting a fence to flag remaining magic-fixture usage

See [CONTRIBUTING.md](CONTRIBUTING.md) for how to run the test suite and publish
a new release.
