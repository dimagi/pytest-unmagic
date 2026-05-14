"""Integration tests for the pytest-django bridge.

Each test drives a sub-pytest via `pytester` with `pytest-django` loaded
and `DJANGO_SETTINGS_MODULE` pointing at `tests.django_app.settings`.
"""
from types import SimpleNamespace

from unmagic import _django


def test_bridge_is_inert_when_pytest_django_not_loaded():
    pm = SimpleNamespace(hasplugin=lambda _: False)
    config = SimpleNamespace(pluginmanager=pm)
    assert _django.is_pytest_django_loaded(config) is False
