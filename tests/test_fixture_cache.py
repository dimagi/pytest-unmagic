from collections import defaultdict
from contextlib import contextmanager, closing

from unmagic.fixtures import Cache, fixture, use


@fixture
def make_cache():
    request = FakeRequest()
    with closing(request):
        yield Cache(request, defaultdict(dict))


@use(make_cache)
def test_execute_value(cache):
    @fixture
    def fix():
        yield value

    value = object()
    fkey = cache.get_fixture_key(fix)
    skey = cache.get_scope_key(fix)

    result = cache.execute(fix, fkey, skey)
    assert result.value is value
    assert result.exc is None


@use(make_cache)
def test_execute_error(cache):
    @fixture
    def fix():
        raise Error

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
        cache = Cache(None, None)

        assert cache.get_scope_key(fix) == "function"

    def test_unmagic_default_scope(self):
        @contextmanager
        def fix():
            yield
        cache = Cache(None, None)

        assert cache.get_scope_key(fix) == "function"

    def test_unmagic_class_scope(self):
        @fixture(scope="class")
        def fix():
            yield
        cache = Cache(None, None)

        assert cache.get_scope_key(fix) == "class"


class FakeRequest:
    def addfinalizer(self, fin):
        assert not hasattr(self, "close")
        self.close = fin


class Error(Exception):
    pass
