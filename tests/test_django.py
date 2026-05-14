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


@use(django_tester)
def test_inline_db_call_without_declaration_raises():
    """A fixture body that resolves the pytest-django `db` fixture
    inline (via `db()`) without it being declared anywhere up the
    chain must raise a clear error, not silently hit the dev DB.

    The stdout-based assertions below (and the negative
    `no_fnmatch_line` checks) are load-bearing: pytest surfaces
    setup-time failures differently across versions, so checking
    outcome counters is too brittle here. The assertions instead
    prove the error type, the fixture name, the message, and that
    neither the stealth fixture body nor the test body executed.
    """
    tester = django_tester()
    tester.makepyfile(textwrap.dedent("""
        from unmagic import fixture, use
        from unmagic.fixtures import UnmagicFixture
        from tests.django_app.models import Thing

        # Resolve the pytest-django 'db' fixture from inside the body.
        db = UnmagicFixture.create('db')

        @fixture
        def stealth_db():
            db()  # inline resolution; never declared via @use
            print("STEALTH_DB_RAN")  # must not appear in output
            yield

        @use(stealth_db)
        def test_inline():
            print("TEST_BODY_RAN")  # must not appear in output
            Thing.objects.create(name='x')
    """))
    result = tester.runpytest("-q")
    # Pytest surfaces setup-time failures differently across versions,
    # so assert on stdout rather than the outcome counters.
    assert result.ret != 0
    result.stdout.fnmatch_lines([
        "*RuntimeError*",
        "*pytest-django fixture 'db'*",
        "*pytest-django did not set up the test database*",
    ])
    result.stdout.no_fnmatch_line("*STEALTH_DB_RAN*")
    result.stdout.no_fnmatch_line("*TEST_BODY_RAN*")


@use(django_tester)
def test_declared_db_does_not_trip_runtime_guard():
    """When 'db' is declared via @use, the runtime guard must let
    the fixture resolve normally."""
    tester = django_tester()
    tester.makepyfile(textwrap.dedent("""
        from unmagic import use
        from tests.django_app.models import Thing

        @use('db')
        def test_ok():
            Thing.objects.create(name='ok')
            assert Thing.objects.count() == 1
    """))
    result = tester.runpytest("-q")
    result.assert_outcomes(passed=1)
