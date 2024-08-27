import pytest
from pytest import fixture

from unmagic import fence

from .util import get_source


@fixture(scope="module", autouse=True)
def unfenced():
    with fence.install(reset=True):
        yield


def test_fence():
    with fence.install([__name__]):
        @fixture
        def fix():
            yield

        assert fence.is_fenced(fix)


def test_fence_is_removed_on_exit_context():
    assert not fence.is_fenced(func), fence._fences
    with fence.install([__name__]):
        assert fence.is_fenced(func)
    assert not fence.is_fenced(func)


def test_new_fence_does_not_remove_previously_installed_fence():
    with fence.install([__name__]):
        with fence.install([__name__]):
            assert fence.is_fenced(func)
        assert fence.is_fenced(func)
    assert not fence.is_fenced(func)


def func():
    ...


def test_fence_with_str():
    with pytest.raises(ValueError, match="not a str"):
        fence.install(__name__)


def test_warning_on_magic_fixture_usage(pytester):

    @get_source
    def test_py():
        from pytest import fixture
        from unmagic import fence

        @fixture(scope="module", autouse=True)
        def module_fence():
            with fence.install(['test_warning_on_magic_fixture_usage']):
                yield

        @fixture
        def magic_fix():
            yield "magic"

        @fixture
        def fixfix(magic_fix):
            assert magic_fix == "magic"
            return "fixfix"

        def test(fixfix):
            assert fixfix == "fixfix"

    fn = test_warning_on_magic_fixture_usage.__name__
    pytester.makepyfile(test_py)
    result = pytester.runpytest()
    result.stdout.fnmatch_lines([
        f"* UserWarning: {fn}.py::fixfix used magic fixture(s): magic_fix",
        f"* UserWarning: {fn}.py::test used magic fixture(s): fixfix",
    ])
    result.assert_outcomes(passed=1, warnings=2)
