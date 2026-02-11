# How to: Use Fixtures With unittest.TestCase

**Problem:** You want to use pytest-unmagic fixtures with
`unittest.TestCase` tests, which don't support standard pytest
fixtures.

## Solution

Apply fixtures to the TestCase class with `@use`:

```python
import unittest
from unmagic import fixture, use

@fixture
def db():
    connection = create_database()
    yield connection
    connection.close()

@use(db)
class TestQueries(unittest.TestCase):
    def test_insert(self):
        database = db()
        database.insert({"key": "value"})
        self.assertEqual(database.get("key"), "value")

    def test_query(self):
        database = db()
        self.assertTrue(database.query("SELECT 1"))
```

## How It Works

When `@use` is applied to a class, it wraps each test method so that the
fixtures are set up before the method runs and torn down afterward.
This works with any class, including `unittest.TestCase`.

## Multiple Fixtures

Apply multiple fixtures at once:

```python
@use(db, cache, auth)
class TestApp(unittest.TestCase):
    def test_with_all_fixtures(self):
        database = db()
        cache_client = cache()
        ...
```

## Scoped Fixtures

Fixture scopes work as expected. A class-scoped fixture is shared across
all methods in the TestCase:

```python
@fixture(scope="class")
def shared_db():
    yield create_database()

@use(shared_db)
class TestDatabase(unittest.TestCase):
    def test_one(self):
        db = shared_db()  # same instance
        db.insert({"a": 1})

    def test_two(self):
        db = shared_db()  # same instance as test_one
        self.assertIn("a", db.keys())
```

## Why This Matters

Standard pytest fixtures cannot be injected into `unittest.TestCase`
methods. This is a long-standing limitation of pytest. pytest-unmagic
works around this because fixtures are applied via decorators and
called explicitly, not injected via argument names.

## Related

- [Tutorial: Lesson 7](../tutorial.md#lesson-7-applying-fixtures-to-classes): Class-based test basics
- [Migration Guide: Example 6](../migration-guide.md#example-6-unittesttestcase-new-capability): TestCase migration
- [API Reference: use()](../api-reference.md#usefixtures): Full parameter details
