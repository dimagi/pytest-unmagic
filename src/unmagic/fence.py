"""PYTEST_DONT_REWRITE"""
import warnings
from contextlib import contextmanager

from . import _api

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

    return _uninstall(_fences[-1])


def pytest_runtest_call(item):
    argnames = _api.get_arg_names(item)
    if _has_magic_fixtures(item.obj, argnames, item):
        names = ", ".join(argnames)
        warnings.warn(f"{item.nodeid} used magic fixture(s): {names}")


def pytest_fixture_setup(fixturedef):
    if is_fenced(fixturedef.func) and fixturedef.argnames:
        fixtureid = f"{fixturedef.baseid}::{fixturedef.argname}"
        names = ", ".join(fixturedef.argnames)
        warnings.warn(f"{fixtureid} used magic fixture(s): {names}")


def _has_magic_fixtures(obj, argnames, node):
    if not (is_fenced(obj) and argnames):
        return False
    args = set(argnames) - _api.get_direct_parametrize_args(node)
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


def is_fenced(func):
    fence = _fences[-1]
    mod = func.__module__
    while mod not in fence:
        if "." not in mod or not fence:
            return False
        mod, _ = mod.rsplit(".", 1)
    return True
