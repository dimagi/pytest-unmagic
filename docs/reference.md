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

### `@use` pytest fixtures

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
