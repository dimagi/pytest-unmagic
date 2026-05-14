"""Integration tests for the pytest-django bridge.

Each test drives a sub-pytest via `pytester` with `pytest-django` loaded
and `DJANGO_SETTINGS_MODULE` pointing at `tests.django_app.settings`.
"""
import textwrap
from types import SimpleNamespace
from unittest.mock import patch

import _pytest.pytester as _pytester

from unmagic import _django, fixture, use
from unmagic.scope import get_request

from .util import unmagic_inactive


@fixture
def django_tester():
    with patch.object(_pytester, "main", unmagic_inactive()(_pytester.main)):
        pytester = get_request().getfixturevalue("pytester")
        pytester.makeini(textwrap.dedent("""
            [pytest]
            DJANGO_SETTINGS_MODULE = tests.django_app.settings
        """))
        yield pytester


def test_bridge_is_inert_when_pytest_django_not_loaded():
    pm = SimpleNamespace(hasplugin=lambda _: False)
    config = SimpleNamespace(pluginmanager=pm)
    assert _django.is_pytest_django_loaded(config) is False


@use(django_tester)
def test_use_db_triggers_pytest_django_setup():
    tester = django_tester()
    tester.makepyfile(textwrap.dedent("""
        from unmagic import use
        from tests.django_app.models import Thing

        @use('db')
        def test_creates_row():
            Thing.objects.create(name='x')
            assert Thing.objects.count() == 1
    """))
    result = tester.runpytest("-q")
    result.assert_outcomes(passed=1)


@use(django_tester)
def test_use_db_via_nested_unmagic_fixture():
    """A user-defined unmagic fixture that declares @use('db') in its
    own decorator chain should still trigger DB setup when applied to
    a test that does not itself declare 'db'."""
    tester = django_tester()
    tester.makepyfile(textwrap.dedent("""
        from unmagic import fixture, use
        from tests.django_app.models import Thing

        @use('db')
        @fixture
        def seeded():
            Thing.objects.create(name='seed')
            yield

        @use(seeded)
        def test_reads_seed():
            assert Thing.objects.filter(name='seed').exists()
    """))
    result = tester.runpytest("-q")
    result.assert_outcomes(passed=1)
