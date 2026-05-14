"""pytest-django interop for unmagic fixtures.

This module is a no-op when pytest-django is not installed or not
loaded. It is imported unconditionally by `unmagic.fixtures`; all
behavior is gated on `is_pytest_django_loaded(config)`.
"""

# Name registered by pytest-django's pytest11 entry point
# (`pytest11 = django = pytest_django.plugin`).
_PYTEST_DJANGO_PLUGIN_NAME = "django"


def is_pytest_django_loaded(config):
    """Return True if pytest-django is registered with the pytest config."""
    return config.pluginmanager.hasplugin(_PYTEST_DJANGO_PLUGIN_NAME)
