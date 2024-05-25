"""Simple unmagical fixture decorators

Unmagical fixtures make it obvious where a fixture comes from using
standard Python import semantics.
"""
from collections import namedtuple
from contextlib import ExitStack, contextmanager, nullcontext
from functools import wraps
from inspect import Parameter, ismethod, signature
from types import GeneratorType

import pytest
from _pytest.fixtures import getfixturemarker

from .scope import get_active, get_addfinalizer, get_scope_data

__all__ = ["fixture", "use"]


def fixture(func=None, /, scope="function"):
    """Unmagic fixture decorator

    Applies ``contextlib.contextmanager`` to the decorated function.
    Decorated functions will not be run as tests, regardless of their
    name.

    Fixtures can be assigned a scope. Scoped fixtures are setup
    immediately before the first test that uses them. Teardown occurs
    after all tests in the scope have been run.

    To have a fixture automatically applied to all tests in a scope,
    `@use` decorators may be applied to the corresponding setup
    function. For example, a module-scoped fixture can be applied to all
    tests in a given module by applying it to a function named
    `setup_module` in the module. As another example, a function-scoped
    fixture may be applied to every function in a module by applying it
    to `setup_function` in the module.
    """
    def fixture(func):
        func.is_unmagic_fixture = True
        func.scope = scope
        func.__test__ = False
        return contextmanager(validate_generator(func))
    return fixture if func is None else fixture(func)


def get_fixture_value(name):
    """Get magic fixture value

    The fixture will be set up if necessary, and will be torn down
    at the end of its scope.

    The 'unmagic' plugin must be active for this to work.
    """
    if not isinstance(name, str):
        raise ValueError("magic fixture name must be a string")
    requests = get_active().requests
    if not requests:
        raise ValueError("There is no active pytest request")
    if name == "request":
        return requests[-1]
    return requests[-1].getfixturevalue(name)


def use(*fixtures):
    """Apply fixture(s) to a function

    Fixtures are passed to the function as positional arguments in the
    same order as they were passed to this decorator factory. Additional
    arguments passed to decorated functions are applied after fixtures.

    Any context manager may be used as a fixture.
    """
    if not fixtures:
        raise TypeError("At least one fixture is required")

    def apply_fixtures(func):
        @wraps(func)
        def run_with_fixtures(*args, **kw):
            try:
                request = get_fixture_value("request")
                cache = Cache(get_scope_data())
                fixture_args = [cache.get(f) for f in fixtures]
                if args and ismethod(request.function):
                    # retain self as first argument
                    fixture_args.insert(0, args[0])
                    args = args[1:]
                if len(fixture_args) > num_params:
                    fixture_args = fixture_args[:num_params]
            except Exception as exc:
                pytest.fail(f"fixture setup for {func.__name__!r} failed: "
                            f"{type(exc).__name__}: {exc}")
            return func(*fixture_args, *args, **kw)

        run_with_fixtures.has_unmagic_fixtures = True
        sig = signature(func)
        new_params = list(sig.parameters.values())[len(fixtures):]
        num_params = sum(_N_PARAMS(p.kind, 0) for p in sig.parameters.values())
        run_with_fixtures.__signature__ = sig.replace(parameters=new_params)
        return run_with_fixtures
    return apply_fixtures


_N_PARAMS = {
    Parameter.POSITIONAL_ONLY: 1,
    Parameter.POSITIONAL_OR_KEYWORD: 1,
}.get


class Cache:
    """Fixture value cache"""

    def __init__(self, scope_data):
        self.scope_data = scope_data

    def get(self, fixture):
        scope_key = self.get_scope_key(fixture)
        fixture_key = self.get_fixture_key(fixture)
        result = self.scope_data[scope_key].get(fixture_key)
        if result is None:
            result = self.execute(fixture, fixture_key, scope_key)
            self.scope_data[scope_key][fixture_key] = result
        if result.exc is not None:
            raise result.exc
        return result.value

    def execute(self, fixture, fixture_key, scope_key):
        values = self.scope_data[scope_key]
        assert fixture_key not in values
        exit = values.get(_exit_key)
        if exit is None:
            on_exit_scope = get_addfinalizer(scope_key)
            exit = values[_exit_key] = ExitStack()
            exit.callback(self.scope_data.pop, scope_key)
            on_exit_scope(exit.close)
        try:
            value = exit.enter_context(self.make_context(fixture))
            exc = None
        except BaseException as exc_value:
            value = None
            exc = exc_value
        return Result(value, exc)

    def get_scope_key(self, fixture):
        return getattr(fixture, "scope", "function")

    @staticmethod
    def get_fixture_key(fixture):
        return fixture

    def make_context(self, fixture):
        if getfixturemarker(fixture) is not None:
            return nullcontext(get_fixture_value(fixture.__name__))
        return fixture()


_exit_key = object()
Result = namedtuple("Result", ["value", "exc"])


def validate_generator(func):
    @wraps(func)
    def validate(*args, **kw):
        gen = func(*args, **kw)
        if not isinstance(gen, GeneratorType):
            raise TypeError(f"fixture {func.__name__!r} does not yield")
        return gen
    return validate
