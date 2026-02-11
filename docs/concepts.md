# Concepts

**Type:** Understanding-oriented
**Audience:** Developers who want to understand why pytest-unmagic exists
**Next:** [Tutorial](tutorial.md) or [API Reference](api-reference.md)

## The Problem: pytest's "Magic"

pytest fixtures use argument-name matching to inject dependencies into
test functions. When you write `def test_query(db):`, pytest searches
its fixture registry for a fixture named `db` and passes its value as
an argument.

This is "magic" in the sense that the connection between the test and
the fixture is implicit:

```python
def test_query(db):
    assert db.query("SELECT 1")
```

Where does `db` come from? To answer that, you need to know:

1. Which `conftest.py` files are in scope
2. Which plugins are active
3. Whether any fixture with that name exists in the current file
4. The fixture discovery and shadowing rules

None of this is visible in the code itself.

## When Magic Breaks Down

### Discovery confusion

Fixtures can be defined in any `conftest.py` in the directory tree. In
large projects, it becomes difficult to know which fixture you're
actually using, especially when fixtures shadow each other across
directories.

### Name collisions

Two fixtures with the same name in different `conftest.py` files shadow
each other based on directory depth. This is a common source of subtle
bugs.

### IDE blindness

Standard tooling can't follow fixture resolution. "Go to definition"
doesn't work for `db` in `def test_query(db):` because the connection
is made at runtime by pytest, not by Python's import system.

### Implicit dependencies

There's no way to see what a test depends on without understanding
pytest's discovery mechanism. The test signature tells you the names,
but not where they come from.

### unittest.TestCase incompatibility

Standard pytest fixtures cannot be injected into `unittest.TestCase`
methods at all. This forces a choice between fixture reuse and the
TestCase base class.

## The Solution: Explicit is Better Than Implicit

pytest-unmagic applies the Python principle "Explicit is better than
implicit" (PEP 20) to fixtures:

```python
from fixtures import db  # explicit import

def test_query():
    database = db()      # explicit call
    assert database.query("SELECT 1")
```

Every fixture dependency is visible as an import at the top of the file.
Your IDE can navigate to it, refactoring tools can rename it, and new
developers can understand the test without knowing pytest internals.

## Design Principles

### Conventional Python semantics

Fixtures are Python objects. You import them, you call them, you pass
them around. No special discovery mechanism.

### Visible dependencies

Every fixture used by a test is either imported at the top of the file
or applied with a visible `@use` decorator. There are no hidden
dependencies.

### Gradual adoption

pytest-unmagic coexists with standard pytest fixtures. You can migrate
one file at a time, or use both styles in the same project
indefinitely.

### No worse than pytest

Anything you can do with standard pytest fixtures, you can do with
unmagic fixtures. Scopes, teardown, parametrize, and plugin fixtures
all work.

## How It Works

When you decorate a function with `@fixture`, pytest-unmagic creates an
`UnmagicFixture` object. This object:

1. **Registers** the fixture with pytest's fixture manager when a test
   that uses it is collected

2. **Sets up** the fixture (runs code before `yield`) when the test or a
   `@use` decorator triggers it

3. **Returns** the yielded value when the fixture is called

4. **Tears down** the fixture (runs code after `yield`) when the scope
   exits

The `@use` decorator marks a test or fixture as depending on one or more
unmagic fixtures, ensuring they're set up before the test runs.

Calling `fixture()` inside a test doesn't re-run the fixture -- it
retrieves the value that was yielded during setup.

## Comparison With Alternatives

### vs. Standard pytest fixtures

| Aspect           | Standard pytest        | pytest-unmagic          |
|------------------|------------------------|-------------------------|
| Discovery        | Name-matching magic    | Python imports          |
| IDE support      | Limited                | Full                    |
| TestCase support | No                     | Yes                     |
| Learning curve   | Higher (fixture rules) | Lower (standard Python) |
| Adoption         | All or nothing         | Gradual                 |

### vs. unittest

| Aspect          | unittest               | pytest-unmagic                            |
|-----------------|------------------------|-------------------------------------------|
| Setup/teardown  | setUp/tearDown methods | `@fixture` with yield                     |
| Shared fixtures | Class inheritance      | Import and compose                        |
| Scopes          | Class only             | function, class, module, package, session |
| Parametrize     | subTest                | `@pytest.mark.parametrize`                |

### vs. Dependency injection frameworks

pytest-unmagic is not a DI framework. It's a thin layer that makes
pytest fixtures work with Python's import system. There's no container,
no resolution graph, no configuration. Fixtures are just decorated
generator functions.

## Common Misconceptions

### "It's just more boilerplate"

The extra `@use(fixture)` decorator and `fixture()` call add two lines
per fixture per test. In exchange, you get explicit imports, IDE
navigation, and `TestCase` support. The trade-off is strongly in favor
of explicitness for projects with more than a handful of fixtures.

### "I'll lose pytest features"

No. Scopes, teardown, parametrize, and plugin fixtures all work. You can
also access any standard pytest fixture via
`get_request().getfixturevalue("name")` or `@use("name")`.

### "It's hard to adopt"

pytest-unmagic supports gradual adoption. You can convert one fixture at
a time and mix both styles in the same project. The
[migration guide](migration-guide.md) covers this in detail.

## When to Use pytest-unmagic

**Good fit:**

- Projects with many fixtures across multiple files
- Teams where developers are confused by fixture discovery
- Codebases that use `unittest.TestCase`
- Projects where IDE support is important

**Less ideal:**

- Very small projects with a few obvious fixtures
- Projects where everyone on the team is comfortable with pytest fixture
  magic

**Mixed approach:**

Use unmagic for your own fixtures and access third-party plugin
fixtures (like `db` from pytest-django) via `@use("name")` or
`get_request().getfixturevalue("name")`.

## The Fence

The fence feature supports gradual migration by warning about implicit
fixture usage:

```python
fence.install(["mypackage.tests"])
```

This doesn't break anything -- tests still pass. But you get warnings
showing which tests and fixtures still rely on name-matching magic. As
you migrate, the warnings decrease until you can remove the fence.

## See Also

- [Tutorial](tutorial.md): Learn through hands-on practice
- [Migration Guide](migration-guide.md): Convert from standard pytest
- [API Reference](api-reference.md): Complete API specification
- [FAQ](faq.md): Common questions
