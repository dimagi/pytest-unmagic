"""Simple unmagical fixture decorators

Unmagical fixtures make it obvious where a fixture comes from using
standard Python import semantics.
"""
import sys
from collections import defaultdict, namedtuple
from contextlib import ExitStack, contextmanager, nullcontext
from functools import wraps
from inspect import Parameter, ismethod, signature
from types import GeneratorType

import pytest
from _pytest.fixtures import get_scope_node, getfixturemarker
from _pytest.scope import Scope

__all__ = ["fixture", "use"]


def fixture(func=None, /, scope="function"):
    """Unmagic fixture decorator

    Applies ``contextlib.contextmanager`` to the decorated function.
    Decorated functions will not be run as tests, regardless of their
    name.
    """
    def fixture(func):
        func.is_unmagic_fixture = True
        func.scope = scope
        func.__test__ = False
        return contextmanager(validate_generator(func))
    return fixture if func is None else fixture(func)


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
                request = kw.pop("request") if discard else kw["request"]
                cache = Cache(request, get_scope_data(request))
                fixture_args = [cache.get(f) for f in fixtures]
                if args and ismethod(request.function):
                    # retain self as first argument
                    fixture_args.insert(0, args[0])
                    args = args[1:]
                if len(fixtures) > num_params:
                    fixture_args = fixture_args[:num_params]
            except Exception as exc:
                pytest.fail(f"fixture setup for {func.__name__!r} failed: "
                            f"{type(exc).__name__}: {exc}")
            return func(*fixture_args, *args, **kw)

        run_with_fixtures.has_unmagic_fixtures = True
        sig = signature(func)
        new_params = list(sig.parameters.values())[len(fixtures):]
        num_params = sum(_N_PARAMS(p.kind, 0) for p in sig.parameters.values())
        discard = not any(p.name == "request" for p in new_params)
        if discard:
            new_params.append(Parameter("request", Parameter.KEYWORD_ONLY))
        run_with_fixtures.__signature__ = sig.replace(parameters=new_params)
        return run_with_fixtures
    return apply_fixtures


_N_PARAMS = {
    Parameter.POSITIONAL_ONLY: 1,
    Parameter.POSITIONAL_OR_KEYWORD: 1,
}.get


class Cache:
    """Fixture value cache"""

    def __init__(self, request, scopes):
        self.request = request
        self.scopes = scopes

    def get(self, fixture):
        scope_key = self.get_scope_key(fixture)
        fixture_key = self.get_fixture_key(fixture)
        result = self.scopes[scope_key].get(fixture_key)
        if result is None:
            result = self.execute(fixture, fixture_key, scope_key)
            self.scopes[scope_key][fixture_key] = result
        if result.exc is not None:
            raise result.exc
        return result.value

    def execute(self, fixture, fixture_key, scope_key):
        values = self.scopes[scope_key]
        assert fixture_key not in values
        exit = values.get(_exit_key)
        if exit is None:
            on_exit_scope = self.get_scope_finalizer(scope_key)
            exit = values[_exit_key] = ExitStack()
            exit.callback(self.scopes.pop, scope_key)
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

    def get_scope_finalizer(self, scope_key):
        node = self.get_scope_node(scope_key)
        return node.addfinalizer

    def get_scope_node(self, scope):
        scope_enum = Scope.from_user(scope, "unmagic fixture cache")
        return get_scope_node(self.request.node, scope_enum)

    def make_context(self, fixture):
        if getattr(fixture, "has_unmagic_fixtures", False):
            return fixture(request=self.request)
        if getfixturemarker(fixture) is not None:
            return nullcontext(self.request.getfixturevalue(fixture.__name__))
        return fixture()


def get_scope_data(request):
    stash = request.config.stash
    value = stash.get(_stash_key, None)
    if value is None:
        value = stash[_stash_key] = defaultdict(dict)
    return value


_stash_key = pytest.StashKey()
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
