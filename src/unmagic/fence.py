import dataclasses
import warnings
from contextlib import contextmanager

from _pytest import fixtures as pytest_fixtures

from .fixtures import fixture

_fences = [set()]


def install(names=(), reset=False):
    """Install unmagic fixture fence

    Warn if pytest magic fixtures are used within the named
    modules/packages.
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


def pytest_runtest_call(item):
    if _has_magic_fixtures(item.obj, item._fixtureinfo.argnames, item):
        names = ", ".join(item._fixtureinfo.argnames)
        warnings.warn(f"{item._nodeid} used magic fixture(s): {names}")


def pytest_fixture_setup(fixturedef):
    if is_fenced(fixturedef.func) and fixturedef.argnames:
        fixtureid = f"{fixturedef.baseid}::{fixturedef.argname}"
        names = ", ".join(fixturedef.argnames)
        warnings.warn(f"{fixtureid} used magic fixture(s): {names}")


def _has_magic_fixtures(obj, argnames, node):
    if not (is_fenced(obj) and argnames):
        return False
    args = set(argnames) - pytest_fixtures._get_direct_parametrize_args(node)
    if getattr(obj, "discard_magic_request", False):
        args.discard("request")
    return args


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
