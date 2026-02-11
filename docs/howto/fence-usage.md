# How to: Use the Magic Fixture Fence

**Problem:** You want to enforce explicit fixture usage and get warnings
when tests use implicit (magic) pytest fixtures.

## Solution

Install a fence for your test namespace:

```python
# conftest.py
from unmagic import fence

fence.install(["mypackage.tests"])
```

Any test or fixture within `mypackage.tests` that uses magic fixtures
will produce a warning:

```
UserWarning: mypackage/tests/test_app.py::test_query used magic fixture(s): db
```

## How It Works

The fence monitors fixture resolution. When a test function or fixture
within a fenced namespace receives fixtures via argument injection
(the standard pytest way), a `UserWarning` is emitted.

The fence does not break tests -- they still pass. It only warns, making
it safe to install during migration.

## Using the Fence as a Context Manager

Install the fence with a scope using a pytest fixture:

```python
# conftest.py
from pytest import fixture
from unmagic import fence

@fixture(scope="session", autouse=True)
def enforce_explicit_fixtures():
    with fence.install(["tests"]):
        yield
```

The fence is active during the session and removed afterward.

## Checking if a Function Is Fenced

```python
from unmagic import fence

with fence.install(["mypackage.tests"]):
    from mypackage.tests.test_app import test_query
    assert fence.is_fenced(test_query)
```

## Nested Fences

Fences stack. Each `install()` adds to the set of fenced modules:

```python
with fence.install(["package_a"]):
    # package_a is fenced
    with fence.install(["package_b"]):
        # both package_a and package_b are fenced
    # only package_a is fenced
```

## What the Fence Catches

The fence warns about:

- Test functions that receive fixtures via argument injection
- Fixtures that depend on other fixtures via argument injection

The fence does **not** warn about:

- `@pytest.mark.parametrize` parameters (these are not fixtures)
- The `request` parameter (this is a pytest built-in)
- Fixtures applied with `@use` or called explicitly

## Migration Workflow

1. Install the fence for your test namespace
2. Run tests and collect warnings
3. Migrate warned tests/fixtures to use `@use` and explicit calls
4. Repeat until no warnings remain
5. Keep the fence as a safety net, or remove it

## Related

- [API Reference: fence.install()](../api-reference.md#fenceinstallnames-resetfalse): Full parameter details
- [Migration Guide](../migration-guide.md): Step-by-step migration
- [Concepts: The Fence](../concepts.md#the-fence): Design rationale
