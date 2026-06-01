# pytest-unmagic

Pytest fixtures with conventional import semantics.

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
of running tests and does not violate scope restrictions.

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
