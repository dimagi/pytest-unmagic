from collections import defaultdict
from contextlib import contextmanager

from unmagic.fixtures import Cache, fixture


def test_execute_value():
    @fixture
    def fix():
        yield value

    value = object()
    cache = Cache(defaultdict(dict))
    fkey = cache.get_fixture_key(fix)
    skey = cache.get_scope_key(fix)

    result = cache.execute(fix, fkey, skey)
    assert result.value is value
    assert result.exc is None


def test_execute_error():
    @fixture
    def fix():
        raise Error

    cache = Cache(defaultdict(dict))
    fkey = cache.get_fixture_key(fix)
    skey = cache.get_scope_key(fix)

    result = cache.execute(fix, fkey, skey)
    assert isinstance(result.exc, Error), result.exc
    assert result.value is None


class TestScopeKeys:

    def test_unmagic_function_scope(self):
        @fixture
        def fix():
            yield
        cache = Cache(None)

        assert cache.get_scope_key(fix) == "function"

    def test_unmagic_default_scope(self):
        @contextmanager
        def fix():
            yield
        cache = Cache(None)

        assert cache.get_scope_key(fix) == "function"

    def test_unmagic_class_scope(self):
        @fixture(scope="class")
        def fix():
            yield
        cache = Cache(None)

        assert cache.get_scope_key(fix) == "class"


class Error(Exception):
    pass
