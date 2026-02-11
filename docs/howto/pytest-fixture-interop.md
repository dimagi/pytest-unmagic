# How to: Interop With Standard pytest Fixtures

**Problem:** You need to use standard pytest fixtures (built-in or from
plugins) alongside unmagic fixtures.

## Solution

There are two ways to access standard pytest fixtures:

### Method 1: `@use("fixture_name")`

Apply a pytest fixture by name:

```python
from unmagic import use

@use("db")  # pytest-django's db fixture
def test_models():
    from myapp.models import User
    User.objects.create(username="test")
    assert User.objects.count() == 1
```

This is useful for fixtures with side effects (like `db`, which enables
database access) where you don't need the fixture's return value.

### Method 2: `get_request().getfixturevalue("name")`

Retrieve a fixture's value by name:

```python
from unmagic import get_request

def test_capture():
    capsys = get_request().getfixturevalue("capsys")
    print("hello")
    captured = capsys.readouterr()
    assert captured.out == "hello\n"
```

## Common pytest Fixtures

### `capsys` -- Capture output

```python
from unmagic import get_request

def test_output():
    capsys = get_request().getfixturevalue("capsys")
    print("hello")
    assert capsys.readouterr().out == "hello\n"
```

### `tmp_path` -- Temporary directory

```python
from unmagic import get_request

def test_files():
    tmp = get_request().getfixturevalue("tmp_path")
    f = tmp / "data.txt"
    f.write_text("hello")
    assert f.read_text() == "hello"
```

### `monkeypatch` -- Patching

```python
from unmagic import get_request

def test_env():
    mp = get_request().getfixturevalue("monkeypatch")
    mp.setenv("MODE", "test")
    import os
    assert os.environ["MODE"] == "test"
```

### Plugin fixtures (e.g., pytest-django `db`)

```python
from unmagic import use

@use("db")
def test_database():
    from myapp.models import User
    User.objects.create(username="test")
```

## Wrapping a pytest Fixture as Unmagic

Use `fixture("name")` to create a reusable unmagic wrapper:

```python
from unmagic import fixture

db = fixture("db")

# Now use like any unmagic fixture
@use(db)
def test_models():
    ...
```

## Using pytest Fixtures in Unmagic Fixture Dependencies

```python
from unmagic import fixture, use

@use("db")
@fixture
def test_user():
    from myapp.models import User
    yield User.objects.create(username="test")
    User.objects.filter(username="test").delete()

def test_user_exists():
    user = test_user()
    from myapp.models import User
    assert User.objects.filter(pk=user.pk).exists()
```

## Related

- [API Reference: use()](../api-reference.md#usefixtures): Accepts fixture names as strings
- [API Reference: get_request()](../api-reference.md#get_request): Access the pytest request
- [Migration Guide: Example 7](../migration-guide.md#example-7-using-standard-pytest-fixtures): Interop examples
