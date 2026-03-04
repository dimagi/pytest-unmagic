# pytest-unmagic Documentation

**Version:** 1.0.1
**Type:** Documentation hub
**Source:** [GitHub](https://github.com/dimagi/pytest-unmagic)
**Package:** [PyPI](https://pypi.org/project/pytest-unmagic/)

pytest-unmagic replaces pytest's magic fixture injection with
conventional Python imports. Fixtures are explicitly imported, applied
with decorators, and called to retrieve values -- no name-matching
magic.

## I want to...

| Goal                              | Document                              |
|-----------------------------------|---------------------------------------|
| Learn pytest-unmagic from scratch | [Tutorial](tutorial.md)               |
| Migrate existing pytest fixtures  | [Migration Guide](migration-guide.md) |
| Solve a specific problem          | [How-to Guides](howto/index.md)       |
| Look up API details               | [API Reference](api-reference.md)     |
| Understand the philosophy         | [Concepts](concepts.md)               |
| Fix an error or common issue      | [FAQ](faq.md)                         |

## Quick Start

```bash
pip install pytest-unmagic
```

```python
# fixtures.py
from unmagic import fixture

@fixture
def greeting():
    yield "hello"

# test_example.py
from unmagic import use
from fixtures import greeting

@use(greeting)
def test_greeting():
    value = greeting()
    assert value == "hello"
```

```bash
pytest test_example.py -v
```

## Documentation Overview

This documentation follows the [Diataxis](https://diataxis.fr/) framework:

- [Tutorial](tutorial.md): Learning-oriented, hands-on lessons (~30 minutes)

- [How-to Guides](howto/index.md): Problem-oriented, task-focused solutions

- [API Reference](api-reference.md): Information-oriented, complete
  technical specification

- [Concepts](concepts.md): Understanding-oriented, philosophy and design

Additional resources:

- [Migration Guide](migration-guide.md): Convert from standard pytest
  fixtures step by step

- [FAQ](faq.md): Common questions, error messages, and troubleshooting

- [CHANGELOG](https://github.com/dimagi/pytest-unmagic/blob/main/CHANGELOG.md):
  Release history

## Compatibility

- **Python:** 3.9, 3.10, 3.11, 3.12, 3.13
- **pytest:** 8.1, 8.2, 8.3, 8.4
