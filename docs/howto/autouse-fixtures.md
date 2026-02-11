# How to: Use Autouse Fixtures

**Problem:** You want a fixture to run automatically for tests without
explicitly applying `@use` to each test.

## Solution

### Option 1: `@fixture(autouse=__file__)`

Apply to all tests in the current module:

```python
# test_module.py
from unmagic import fixture

@fixture(autouse=__file__)
def setup_env():
    os.environ["MODE"] = "test"
    yield
    del os.environ["MODE"]

def test_something():
    assert os.environ["MODE"] == "test"  # fixture was applied automatically
```

### Option 2: `autouse()` from another module

Register a shared fixture for autouse in specific modules:

```python
# fixtures.py
from unmagic import fixture

@fixture
def setup_env():
    os.environ["MODE"] = "test"
    yield
    del os.environ["MODE"]

# test_module.py
from unmagic import autouse
from .fixtures import setup_env

autouse(setup_env, __file__)

def test_something():
    assert os.environ["MODE"] == "test"
```

### Option 3: `@fixture(autouse=True)`

Apply to all tests in the entire session:

```python
@fixture(autouse=True)
def global_setup():
    yield
```

## Package-Level Autouse

To apply a fixture to all tests in a package, use `autouse` in the
package's `__init__.py`:

```python
# tests/__init__.py
from unmagic import autouse
from .fixtures import setup_env

autouse(setup_env, __file__)
```

When `__file__` resolves to an `__init__.py`, the fixture applies to the
entire package.

## Autouse With Scopes

Autouse fixtures respect their scope:

```python
# Set up once per module, applied automatically
@fixture(scope="module", autouse=__file__)
def module_setup():
    yield create_module_resource()
```

## Context Managers as Autouse Fixtures

You can register a context manager as an autouse fixture:

```python
from contextlib import contextmanager
from unmagic import fixture

@contextmanager
def managed_resource():
    resource = acquire()
    yield resource
    release(resource)

fixture(managed_resource, scope="module", autouse=__file__)
```

## Autouse With Dependencies

When an autouse fixture depends on another fixture, apply
`@use` *inside* `@fixture(autouse=...)`:

```python
@fixture(autouse=__file__)
@use(database)
def seed_data():
    db = database()
    db.insert({"key": "value"})
    yield
```

> [!note]
> `@fixture(autouse=...)` must be the outermost decorator.

## Warning About Late Registration

If you call `autouse()` during test execution (after collection), a warning is emitted because relevant tests may have already run. Register autouse fixtures at module import time.

## Related

- [API Reference: fixture()](../api-reference.md#fixturefuncnone--scopefunction-autousefalse): `autouse` parameter details
- [API Reference: autouse()](../api-reference.md#autousefixture-where): Full documentation
- [Tutorial: Lesson 4](../tutorial.md#lesson-4-use-shorthand): Basics
