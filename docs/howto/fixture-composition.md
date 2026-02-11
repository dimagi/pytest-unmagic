# How to: Compose Fixtures

**Problem:** You want to build complex fixtures from simpler ones,
creating a dependency chain.

## Solution

Use `@use` to declare fixture dependencies, then call fixtures to get
their values:

```python
from unmagic import fixture, use

@fixture
def database():
    yield create_database()

@use(database)
@fixture
def user():
    db = database()
    user = db.create_user("test")
    yield user
```

## Decorator Order

When composing fixtures, `@use` must come *above* `@fixture`:

```python
# Correct: @use above @fixture
@use(database)
@fixture
def user():
    db = database()
    yield db.create_user("test")

# Wrong: @fixture above @use -- this will not work as expected
@fixture
@use(database)
def user():
    yield
```

## Multiple Dependencies

Chain multiple fixtures with a single `@use`:

```python
@fixture
def database():
    yield create_database()

@fixture
def cache():
    yield create_cache()

@use(database, cache)
@fixture
def service():
    db = database()
    c = cache()
    yield Service(db=db, cache=c)
```

## Deep Composition

Fixtures can depend on other composed fixtures. Dependencies are
resolved transitively:

```python
@fixture
def database():
    yield create_database()

@use(database)
@fixture
def user():
    db = database()
    yield db.create_user("test")

@use(user)
@fixture
def authenticated_client():
    u = user()
    yield create_client(user=u)

# When this test runs, database -> user -> authenticated_client
# are all set up in order
def test_dashboard():
    client = authenticated_client()
    response = client.get("/dashboard")
    assert response.status == 200
```

## Composing With pytest Fixtures

You can compose with standard pytest fixtures using their string names:

```python
@use("db")  # pytest-django's db fixture
@fixture
def user():
    from myapp.models import User
    yield User.objects.create(username="test")
```

## Related

- [Tutorial: Lesson 5](../tutorial.md#lesson-5-fixture-composition): Composition basics
- [How to: pytest Fixture Interop](pytest-fixture-interop.md): Mix with standard fixtures
- [API Reference: use()](../api-reference.md#usefixtures): Full parameter details
