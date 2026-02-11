# Basic Examples

Self-contained examples demonstrating core pytest-unmagic features.

## Files

| File                  | Demonstrates                               |
|-----------------------|--------------------------------------------|
| `fixtures.py`         | Shared fixture definitions                 |
| `test_simple.py`      | Basic fixture usage, `@use`, and shorthand |
| `test_scope.py`       | Module-scoped fixtures                     |
| `test_composition.py` | Building fixtures from other fixtures      |
| `test_classes.py`     | Class-based tests and `unittest.TestCase`  |

## Running

```bash
pip install pytest-unmagic
pytest examples/basic/ -v
```

## Expected Output

```
examples/basic/test_simple.py::test_greeting_value PASSED
examples/basic/test_simple.py::test_tracing PASSED
examples/basic/test_simple.py::test_shorthand PASSED
examples/basic/test_scope.py::test_first PASSED
examples/basic/test_scope.py::test_second PASSED
examples/basic/test_scope.py::test_setup_only_once PASSED
examples/basic/test_composition.py::test_admin_exists PASSED
examples/basic/test_composition.py::test_database_has_admin PASSED
examples/basic/test_classes.py::TestWithUse::test_add PASSED
examples/basic/test_classes.py::TestWithUse::test_empty PASSED
examples/basic/test_classes.py::TestWithTestCase::test_add PASSED
examples/basic/test_classes.py::TestWithTestCase::test_empty PASSED
```
