# Migration Examples

Side-by-side comparison of standard pytest fixtures and pytest-unmagic.

## Files

| File               | Description                               |
|--------------------|-------------------------------------------|
| `before_pytest.py` | Standard pytest patterns (for reference)  |
| `after_unmagic.py` | Equivalent pytest-unmagic code (runnable) |

## Running

Only the "after" file is runnable as a test:

```bash
pytest examples/migration/after_unmagic.py -v
```

## Key Differences

1. `@pytest.fixture` becomes `@fixture` (from `unmagic`)
2. Argument injection becomes explicit `@use` + `fixture()` call
3. `conftest.py` discovery becomes Python imports
4. `autouse=True` becomes `autouse=__file__` (module-scoped) or `True` (global)
5. Fixture composition uses `@use(dep)` instead of argument injection
