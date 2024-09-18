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

@fixture
def tracer():
    traces = []
    yield traces
    assert traces, "expected at least one trace"

@use(tracer)
def test_world(traces):
    traces.append("hello")
```

A fixture must yield exactly once. The `@use` decorator will apply yielded
fixture values to the decorated function as positional arguments, which means
the fixture value may have whatever name is appropriate within the function to
which it is applied. If there is no positional argument available to receive the
value then it will not be passed.

The location where a fixture is defined has no affect on where it can be used.
Any code that can import it can use it.

### @use shorthand

If a single fixture is being applied to another fixture or test it may be
applied directly as a decorator without `@use()`. The test in the example above
could have been written as

```py
@tracer
def test_world(traces):
    traces.append("hello")
```

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

A single fixture may be registered for autouse in multiple modules and packages
with ``unmagic.autouse``.

```py
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

### Magic fixture fence

It is possible to errect a fence around tests in a particular module or package
to ensure that magic fixtures are not used in that namespace except with the
`@use(...)` decorator.

```py
from unmagic import fence

fence.install(['mypackage.tests'])
```

This will cause warnings to be emitted for magic fixture usages within
`mypackage.tests`.


## Running the `unmagic` test suite

```sh
cd path/to/pytest-unmagic
pip install -e .
pytest
```
