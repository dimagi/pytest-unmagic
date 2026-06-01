## Running the `unmagic` test suite

```sh
cd path/to/pytest-unmagic
pip install -e .
pytest
```


## Publishing a new verison to PyPI

Push a new tag to Github using the format vX.Y.Z where X.Y.Z matches the version
in [`__init__.py`](src/unmagic/__init__.py).

A new version is published to https://test.pypi.org/p/pytest-unmagic on every
push to the *main* branch.

Publishing is automated with [Github Actions](.github/workflows/pypi.yml).
