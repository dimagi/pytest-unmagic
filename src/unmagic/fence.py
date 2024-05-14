import dataclasses
from contextlib import contextmanager

from _pytest import fixtures as pytest_fixtures

from .fixtures import fixture

_fences = [set()]


def install(names=(), reset=False):
    """Install unmagic fixture fence

    Prevent pytest's standard magical fixtures from being defined and
    referenced with the named packages and modules.
    """
    if isinstance(names, str):
        raise ValueError("names should be a sequence of strings, not a string")

    if reset:
        _fences.append(set(names))
    else:
        _fences.append(_fences[-1].union(names))

    original = pytest_fixtures.FixtureFunctionMarker.__call__
    pytest_fixtures.FixtureFunctionMarker.__call__ = fenced_fixture
    if not hasattr(fenced_fixture, "_original"):
        fenced_fixture._original = original
    return _uninstall(_fences[-1])


@contextmanager
def _uninstall(fence):
    try:
        yield
    finally:
        assert fence is _fences[-1], (
            f"Cannot uninstall fence {fence} because it has either been "
            "uninstalled or other fences have subsequently been installed "
            f"but not uninstalled. Fence stack: {_fences}"
        )
        _fences.pop()


def fenced_fixture(self, function):
    scope = self.scope
    if not is_fenced(function) or scope != "function":
        autoself = dataclasses.replace(self, autouse=True, _ispytest=True)
        return fenced_fixture._original(autoself, function)
    if self.params:
        raise NotImplementedError("unsupported: fixture params")
    if self.autouse:
        raise NotImplementedError("unsupported: autouse")
    return fixture(function)


def is_fenced(func):
    fence = _fences[-1]
    mod = func.__module__
    while mod not in fence:
        if "." not in mod or not fence:
            return False
        mod, _ = mod.rsplit(".", 1)
    return True
