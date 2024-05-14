import pytest
from pytest import fixture

from unmagic import fence


@fixture(scope="module")
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
    assert not fence.is_fenced(func)
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
